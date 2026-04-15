#!/usr/bin/env bash
#
# log-surgeon - Structured Log Parser & Analyzer
# 作者: Chen Su
# 许可证: MIT
# 描述: 将原始日志转换为结构化格式，支持多格式解析、字段提取、过滤与统计
#

set -euo pipefail

# ============ 颜色定义 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ============ 默认配置 ============
FORMAT="${FORMAT:-nginx}"           # 日志格式: nginx, apache, syslog, json, csv, custom
INPUT_FILE=""                         # 输入文件 (空则读取 stdin)
OUTPUT_FORMAT="${OUTPUT_FORMAT:-json}" # 输出格式: json, csv, table, raw
CONFIG_FILE="${CONFIG_FILE:-}"         # 自定义格式配置文件
TAIL_MODE="false"                     # 实时 tail 模式
FILTER_FIELD=""                       # 过滤字段
FILTER_VALUE=""                       # 过滤值 (支持正则)
STATS_MODE="false"                    # 统计模式
STATS_FIELD=""                        # 统计字段
STATS_LIMIT="10"                      # 统计TopN
HEAD_COUNT="0"                        # 仅输出前N行 (0=全部)
TAIL_COUNT="0"                        # 仅输出后N行 (0=全部)
QUIET="false"                         # 静默模式
NO_COLOR="false"                      # 禁用颜色

# ============ 格式定义 ============
# 每个格式是一个关联数组，下标是字段名，值是正则表达式
declare -A FORMAT_REGEX

# Nginx 访问日志格式
FORMAT_REGEX[nginx]='^([^ ]+) - ([^ ]+) \[([^]]+)\] "([^"]+)" ([0-9]+) ([0-9]+) "([^"]*)" "([^"]*)"'

# Apache Combined 日志格式
FORMAT_REGEX[apache]='^([^ ]+) ([^ ]+) ([^ ]+) \[([^]]+)\] "([^"]+)" ([0-9]+) ([0-9]+) "([^"]*)" "([^"]*)"'

# Syslog 格式 (RFC 3164)
FORMAT_REGEX[syslog]='^([A-Z][a-z]{2} [ 0-9]{2} [0-9:]+) ([^ ]+) ([^:]+): (.*)$'

# Syslog 格式 (RFC 5424 with ISO timestamp)
FORMAT_REGEX[syslog5424]='^<([0-9]+)>([0-9]+) ([0-9TZ:.-]+) ([^ ]+) ([^ ]+) ([^ ]+) ([^ ]+) (.*)$'

# JSON 日志 (每行一个JSON对象)
FORMAT_REGEX[json]='^\{.*\}$'

# 自定义格式 (从配置文件加载)
FORMAT_REGEX[custom]=""

# ============ 格式字段列表 ============
declare -a NGINX_FIELDS=("remote_addr" "remote_user" "time_local" "request" "status" "body_bytes_sent" "http_referer" "http_user_agent")
declare -a APACHE_FIELDS=("remote_addr" "remote_ident" "remote_user" "time_local" "request" "status" "body_bytes_sent" "http_referer" "http_user_agent")
declare -a SYSLOG_FIELDS=("timestamp" "hostname" "program" "message")
declare -a SYSLOG5424_FIELDS=("pri" "version" "timestamp" "hostname" "appname" "proc_id" "msg_id" "message")

# ============ 帮助信息 ============
show_help() {
    cat << EOF
${BOLD}log-surgeon${NC} - Structured Log Parser & Analyzer

${BOLD}描述:${NC}
  将原始日志文件转换为结构化格式，支持字段提取、过滤、统计

${BOLD}用法:${NC}
  $(basename "$0") [选项]

${BOLD}选项:${NC}
  输入相关:
    -f, --file FILE       输入日志文件 (默认: 读取 stdin)
    -c, --config FILE     自定义格式配置文件

  格式相关:
    -F, --format FMT      输入日志格式: nginx, apache, syslog, syslog5424, json, csv, custom
                           (默认: nginx)
    -O, --output FMT      输出格式: json, csv, table, raw (默认: json)

  过滤相关:
    --filter-field FIELD  按字段名过滤
    --filter-value REGEX  过滤值 (支持正则表达式)
    -s, --status CODE     仅显示指定状态的请求 (如: 404, 500)

  统计相关:
    --stats FIELD         启用统计模式，按字段分组计数
    --stats-limit N       统计TopN (默认: 10)

  限制相关:
    -n, --head N          仅显示前 N 行
    -t, --tail N          仅显示后 N 行 (支持 --tail-mode)
    --tail-mode           实时 tail -f 模式

  输出相关:
    -q, --quiet            静默模式，不输出元信息
    --no-color             禁用颜色输出

  其他:
    -h, --help             显示帮助信息
    -v, --version          显示版本信息

${BOLD}示例:${NC}
  # 解析 Nginx 日志，输出 JSON
  $(basename "$0") -f access.log -F nginx

  # 解析 JSON 日志，按 status=500 过滤
  $(basename "$0") -f app.log -F json --filter-field status --filter-value "500"

  # 实时监控 Nginx 日志
  tail -f access.log | $(basename "$0") -F nginx --tail-mode

  # Apache 日志统计，Top 10 请求路径
  $(basename "$0") -f access.log -F apache --stats request --stats-limit 10

  # 输出为 CSV 格式
  $(basename "$0") -f access.log -F nginx -O csv

  # 从配置文件加载自定义格式
  $(basename "$0") -f app.log -c config/myformat.conf

${BOLD}环境变量:${NC}
  FORMAT         设置默认日志格式
  OUTPUT_FORMAT  设置默认输出格式
  CONFIG_FILE    设置自定义格式配置文件

EOF
}

# 显示版本
show_version() {
    echo "log-surgeon v1.0.0"
    echo "Structured Log Parser & Analyzer"
    echo "作者: Chen Su"
}

# ============ 工具函数 ============

# 过滤敏感信息
mask_sensitive() {
    local value="$1"
    # 过滤 IP 地址后半段、邮箱、token 等
    echo "$value" | sed -E 's/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/*.*.*/g' \
              | sed -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/***@***/g' \
              | sed -E 's/(token|key|pass|secret)=[^& ]*/\1=***/gi'
}

# 颜色输出
color_output() {
    local level="$1"
    shift
    local msg="$*"
    case "$level" in
        red)    [[ "$NO_COLOR" != "true" ]] && echo -e "${RED}${msg}${NC}" || echo "$msg" ;;
        green)  [[ "$NO_COLOR" != "true" ]] && echo -e "${GREEN}${msg}${NC}" || echo "$msg" ;;
        yellow) [[ "$NO_COLOR" != "true" ]] && echo -e "${YELLOW}${msg}${NC}" || echo "$msg" ;;
        blue)   [[ "$NO_COLOR" != "true" ]] && echo -e "${BLUE}${msg}${NC}" || echo "$msg" ;;
        cyan)   [[ "$NO_COLOR" != "true" ]] && echo -e "${CYAN}${msg}${NC}" || echo "$msg" ;;
        bold)   [[ "$NO_COLOR" != "true" ]] && echo -e "${BOLD}${msg}${NC}" || echo "$msg" ;;
        *)      echo "$msg" ;;
    esac
}

# 转义 JSON 字符串
json_escape() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    str="${str//$'\n'/\\n}"
    str="${str//$'\r'/\\r}"
    str="${str//$'\t'/\\t}"
    echo "$str"
}

# 从 syslog 时间戳提取可排序的时间
normalize_time() {
    local ts="$1"
    # 将 Jan 15 10:30:00 转换为 2026-01-15 10:30:00 (假设当前年份)
    local year
    year=$(date '+%Y')
    # 尝试解析并转换
    date -j -f "%b %d %H:%M:%S" "${ts}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null \
        || date -d "$ts" "+%Y-%m-%d %H:%M:%S" 2>/dev/null \
        || echo "$ts"
}

# ============ 格式解析函数 ============

# 解析 Nginx/Apache 日志行
parse_combined_log() {
    local line="$1"
    local regex="$2"
    local -a fields=("${!3}")
    
    if [[ "$line" =~ $regex ]]; then
        local result="{"
        local first=true
        local i=1
        for field in "${fields[@]}"; do
            local value="${BASH_REMATCH[$i]}"
            # 跳过 "-" 空值
            [[ "$value" == "-" ]] && value=""
            # URL decode
            value=$(printf '%b' "${value//%/\\x}")
            # JSON 转义
            value=$(json_escape "$value")
            if [[ "$first" == "true" ]]; then
                first=false
            else
                result+=", "
            fi
            result+="\"$field\": \"$value\""
            ((i++)) || true
        done
        result+="}"
        echo "$result"
        return 0
    fi
    return 1
}

# 解析 Syslog 行
parse_syslog() {
    local line="$1"
    local regex="$2"
    local -a fields=("${!3}")
    
    if [[ "$line" =~ $regex ]]; then
        local result="{"
        local first=true
        local i=1
        for field in "${fields[@]}"; do
            local value="${BASH_REMATCH[$i]}"
            value=$(json_escape "$value")
            if [[ "$first" == "true" ]]; then
                first=false
            else
                result+=", "
            fi
            result+="\"$field\": \"$value\""
            ((i++)) || true
        done
        result+="}"
        echo "$result"
        return 0
    fi
    return 1
}

# 解析 JSON 日志行
parse_json_log() {
    local line="$1"
    
    # 验证是否是有效 JSON
    if echo "$line" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "$line"
        return 0
    fi
    return 1
}

# ============ 加载自定义格式 ============
load_custom_format() {
    local config="$1"
    if [[ ! -f "$config" ]]; then
        echo "错误: 自定义格式配置文件不存在: $config" >&2
        exit 1
    fi
    
    local name=""
    local regex=""
    local fields=()
    
    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        
        if [[ "$line" =~ ^name:[[:space:]]*(.+)$ ]]; then
            name="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^regex:[[:space:]]*(.+)$ ]]; then
            regex="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^field:[[:space:]]*(.+)$ ]]; then
            fields+=("${BASH_REMATCH[1]}")
        fi
    done < "$config"
    
    if [[ -z "$name" ]] || [[ -z "$regex" ]] || [[ ${#fields[@]} -eq 0 ]]; then
        echo "错误: 自定义格式配置文件格式错误" >&2
        exit 1
    fi
    
    FORMAT_REGEX[custom]="$regex"
    
    # 设置全局变量供调用方使用
    CUSTOM_FIELDS=("${fields[@]}")
    CUSTOM_REGEX="$regex"
}

# ============ 输出函数 ============

# 输出 JSON 行
output_json() {
    local json="$1"
    echo "$json"
}

# 输出 CSV 行 (需要字段名)
output_csv() {
    local json="$1"
    # 简单CSV转换
    echo "$json" | python3 -c "
import sys, json, csv
data = json.loads(sys.stdin.read())
# 提取所有键值对
writer = csv.writer(sys.stdout)
writer.writerow(list(data.keys()))
writer.writerow(list(data.values()))
" 2>/dev/null || echo "$json"
}

# 输出表格
output_table() {
    local json="$1"
    local max_field_len=20
    local max_value_len=50
    
    echo "$json" | python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    max_f = max(len(str(k)) for k in data.keys()) if data else 10
    max_v = max(len(str(v)) for v in data.values()) if data else 10
    max_f = min(max_f, 20)
    max_v = min(max_v, 50)
    for k, v in data.items():
        print(f'{str(k):<{max_f}} : {str(v)[:max_v]}')
except: pass
" 2>/dev/null
    echo "---"
}

# 输出原始行
output_raw() {
    local json="$1"
    echo "$json" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(' '.join(str(v) for v in data.values()))
" 2>/dev/null || echo "$json"
}

# ============ 统计函数 ============

# 统计计数器
declare -A STATS_COUNTER

# 统计一组字段值
update_stats() {
    local field="$1"
    local json="$2"
    
    # 从 JSON 中提取指定字段的值
    local value
    value=$(echo "$json" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('$field', 'N/A'))
" 2>/dev/null) || value="N/A"
    
    : ${STATS_COUNTER["$value"]:=0}
    STATS_COUNTER["$value"]=$((STATS_COUNTER["$value"] + 1))
}

# 输出统计结果
print_stats() {
    local total=0
    local count=0
    
    echo ""
    color_output "bold" "========== 统计结果 (Top $STATS_LIMIT) =========="
    echo ""
    
    # 按计数排序
    for key in "${!STATS_COUNTER[@]}"; do
        ((total += STATS_COUNTER["$key"])) || true
        ((count++)) || true
    done
    
    printf "  %-50s %10s %10s\n" "值" "次数" "占比"
    echo "  --------------------------------------------------------------------------------"
    
    # 排序输出
    while IFS= read -r line; do
        local val count_pct
        val=$(echo "$line" | cut -d: -f1)
        count_pct=$(echo "$line" | cut -d: -f2)
        local pct
        pct=$(echo "scale=2; $count_pct * 100 / $total" | bc 2>/dev/null || echo "N/A")
        printf "  %-50s %10s %8s%%\n" "${val:0:50}" "$count_pct" "$pct"
    done < <(
        for key in "${!STATS_COUNTER[@]}"; do
            echo "${key}:${STATS_COUNTER[$key]}"
        done | sort -t: -k2 -rn | head -n "$STATS_LIMIT"
    )
    
    echo ""
    color_output "cyan" "  总计: $count 种不同值, $total 条记录"
    echo ""
}

# ============ 过滤函数 ============

# 检查行是否匹配过滤条件
should_include() {
    local json="$1"
    
    # 按状态码过滤 (特殊处理)
    if [[ -n "$STATUS_FILTER" ]]; then
        local status
        status=$(echo "$json" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('status', ''))
" 2>/dev/null) || status=""
        if [[ "$status" != "$STATUS_FILTER" ]]; then
            return 1
        fi
    fi
    
    # 按字段+正则过滤
    if [[ -n "$FILTER_FIELD" ]] && [[ -n "$FILTER_VALUE" ]]; then
        local field_value
        field_value=$(echo "$json" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('$FILTER_FIELD', ''))
" 2>/dev/null) || field_value=""
        
        if ! [[ "$field_value" =~ $FILTER_VALUE ]]; then
            return 1
        fi
    fi
    
    return 0
}

# ============ 主解析函数 ============
STATUS_FILTER=""

parse_line() {
    local line="$1"
    local parsed=""
    
    case "$FORMAT" in
        nginx)
            parsed=$(parse_combined_log "$line" "${FORMAT_REGEX[nginx]}" NGINX_FIELDS[@])
            ;;
        apache)
            parsed=$(parse_combined_log "$line" "${FORMAT_REGEX[apache]}" APACHE_FIELDS[@])
            ;;
        syslog)
            parsed=$(parse_syslog "$line" "${FORMAT_REGEX[syslog]}" SYSLOG_FIELDS[@])
            ;;
        syslog5424)
            parsed=$(parse_syslog "$line" "${FORMAT_REGEX[syslog5424]}" SYSLOG5424_FIELDS[@])
            ;;
        json)
            parsed=$(parse_json_log "$line")
            ;;
        csv)
            # CSV 简单处理: 按逗号分隔，字段名为 col1, col2...
            local i=1
            local result="{"
            local first=true
            IFS=',' read -ra fields <<< "$line"
            for field in "${fields[@]}"; do
                field=$(json_escape "$field")
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    result+=", "
                fi
                result+="\"col${i}\": \"$field\""
                ((i++)) || true
            done
            result+="}"
            echo "$result"
            return 0
            ;;
        custom)
            if [[ -n "$CUSTOM_REGEX" ]] && [[ ${#CUSTOM_FIELDS[@]} -gt 0 ]]; then
                parsed=$(parse_combined_log "$line" "$CUSTOM_REGEX" CUSTOM_FIELDS[@])
            fi
            ;;
        *)
            echo "不支持的格式: $FORMAT" >&2
            return 1
            ;;
    esac
    
    if [[ -n "$parsed" ]]; then
        echo "$parsed"
        return 0
    else
        return 1
    fi
}

# ============ 主函数 ============
main() {
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--file)
                INPUT_FILE="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                load_custom_format "$CONFIG_FILE"
                FORMAT="custom"
                shift 2
                ;;
            -F|--format)
                FORMAT="$2"
                shift 2
                ;;
            -O|--output)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --filter-field)
                FILTER_FIELD="$2"
                shift 2
                ;;
            --filter-value)
                FILTER_VALUE="$2"
                shift 2
                ;;
            -s|--status)
                STATUS_FILTER="$2"
                shift 2
                ;;
            --stats)
                STATS_MODE="true"
                STATS_FIELD="$2"
                shift 2
                ;;
            --stats-limit)
                STATS_LIMIT="$2"
                shift 2
                ;;
            -n|--head)
                HEAD_COUNT="$2"
                shift 2
                ;;
            -t|--tail)
                TAIL_COUNT="$2"
                shift 2
                ;;
            --tail-mode)
                TAIL_MODE="true"
                shift
                ;;
            -q|--quiet)
                QUIET="true"
                shift
                ;;
            --no-color)
                NO_COLOR="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                show_version
                exit 0
                ;;
            *)
                echo "未知选项: $1" >&2
                show_help
                exit 1
                ;;
        esac
    done
    
    # 验证格式
    if [[ "$FORMAT" != "nginx" && "$FORMAT" != "apache" && "$FORMAT" != "syslog" && \
          "$FORMAT" != "syslog5424" && "$FORMAT" != "json" && "$FORMAT" != "csv" && \
          "$FORMAT" != "custom" ]]; then
        echo "不支持的格式: $FORMAT" >&2
        echo "支持的格式: nginx, apache, syslog, syslog5424, json, csv, custom" >&2
        exit 1
    fi
    
    # 验证统计模式参数
    if [[ "$STATS_MODE" == "true" ]] && [[ -z "$STATS_FIELD" ]]; then
        echo "错误: --stats 需要指定 --stats FIELD" >&2
        exit 1
    fi
    
    # 头部信息
    if [[ "$QUIET" != "true" ]]; then
        color_output "bold" "========== log-surgeon =========="
        color_output "cyan" "  格式: $FORMAT  →  输出: $OUTPUT_FORMAT"
        [[ -n "$INPUT_FILE" ]] && color_output "yellow" "  文件: $INPUT_FILE"
        [[ "$TAIL_MODE" == "true" ]] && color_output "green" "  模式: 实时监控中 (Ctrl+C 退出)"
        echo ""
    fi
    
    # 行计数器
    local line_count=0
    local parsed_count=0
    local skipped_count=0
    
    # 输入处理
    local input_fd
    if [[ -n "$INPUT_FILE" ]]; then
        if [[ ! -f "$INPUT_FILE" ]]; then
            echo "错误: 文件不存在: $INPUT_FILE" >&2
            exit 1
        fi
        input_fd="$INPUT_FILE"
    else
        input_fd="/dev/stdin"
    fi
    
    # tail -n 处理
    local tail_cmd="cat"
    if [[ "$TAIL_COUNT" -gt 0 ]]; then
        tail_cmd="tail -n $TAIL_COUNT"
    fi
    
    # head -n 处理
    local head_cmd="cat"
    if [[ "$HEAD_COUNT" -gt 0 ]]; then
        head_cmd="head -n $HEAD_COUNT"
    fi
    
    # 主处理循环
    if [[ "$TAIL_MODE" == "true" ]]; then
        # 实时 tail 模式
        tail -f "$INPUT_FILE" 2>/dev/null | while IFS= read -r line; do
            local parsed
            parsed=$(parse_line "$line") || continue
            
            if ! should_include "$parsed"; then
                continue
            fi
            
            ((parsed_count++)) || true
            
            if [[ "$STATS_MODE" == "true" ]]; then
                update_stats "$STATS_FIELD" "$parsed"
            else
                case "$OUTPUT_FORMAT" in
                    json)  output_json "$parsed" ;;
                    csv)   output_csv "$parsed" ;;
                    table) output_table "$parsed" ;;
                    raw)   output_raw "$parsed" ;;
                esac
            fi
        done
        
        if [[ "$STATS_MODE" == "true" ]]; then
            print_stats
        fi
    else
        # 批量处理模式
        local _input_fd
        if [[ -n "$INPUT_FILE" ]]; then
            if [[ ! -f "$INPUT_FILE" ]]; then
                echo "错误: 文件不存在: $INPUT_FILE" >&2
                exit 1
            fi
            _input_fd="$INPUT_FILE"
        else
            _input_fd="/dev/stdin"
        fi
        
        # 使用文件描述符重定向，确保计数器在主shell中持久化
        if [[ "$TAIL_COUNT" -gt 0 ]]; then
            exec 3< <(tail -n "$TAIL_COUNT" "$_input_fd" 2>/dev/null)
        elif [[ "$HEAD_COUNT" -gt 0 ]]; then
            exec 3< <(head -n "$HEAD_COUNT" "$_input_fd" 2>/dev/null)
        else
            exec 3< "$_input_fd"
        fi
        
        # 主处理循环（文件描述符3）
        while IFS= read -r line <&3; do
            ((line_count++)) || true
            
            local parsed
            parsed=$(parse_line "$line")
            
            if [[ -z "$parsed" ]]; then
                ((skipped_count++)) || true
                continue
            fi
            
            if ! should_include "$parsed"; then
                ((skipped_count++)) || true
                continue
            fi
            
            ((parsed_count++)) || true
            
            if [[ "$STATS_MODE" == "true" ]]; then
                update_stats "$STATS_FIELD" "$parsed"
            else
                case "$OUTPUT_FORMAT" in
                    json)  output_json "$parsed" ;;
                    csv)   output_csv "$parsed" ;;
                    table) output_table "$parsed" ;;
                    raw)   output_raw "$parsed" ;;
                esac
            fi
        done
        exec 3<&-
        
        # 输出统计信息
        if [[ "$STATS_MODE" == "true" ]]; then
            print_stats
        fi
        
        # 元信息
        if [[ "$QUIET" != "true" && "$STATS_MODE" != "true" ]]; then
            echo ""
            color_output "cyan" "  已解析: $parsed_count 行, 跳过: $skipped_count 行, 总计: $line_count 行"
        fi
    fi
}

# 启动
main "$@"
