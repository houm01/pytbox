#!/usr/bin/env bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

YES_MODE=0
MANUAL_TAG=""
TARGET_TAG=""
MODE=""

show_help() {
    echo -e "${BLUE}用法:${NC}"
    echo -e "  $0 [vX.Y.Z-YYYYMMDD] [--yes]"
    echo -e ""
    echo -e "${BLUE}说明:${NC}"
    echo -e "  - 不传 tag 时自动计算下一版本并使用当天日期"
    echo -e "  - 传 tag 时必须是完整格式 vX.Y.Z-YYYYMMDD，且日期必须为当天"
    echo -e "  - 默认会先预览并要求确认，--yes 可跳过确认"
    echo -e ""
    echo -e "${BLUE}示例:${NC}"
    echo -e "  $0"
    echo -e "  $0 --yes"
    echo -e "  $0 v0.1.1-20260212"
}

current_date() {
    if [[ -n "${PUBLISH_DATE_OVERRIDE:-}" ]]; then
        echo "${PUBLISH_DATE_OVERRIDE}"
        return 0
    fi
    date '+%Y%m%d'
}

fetch_tags() {
    if git remote get-url origin >/dev/null 2>&1; then
        if ! git fetch origin --tags --quiet; then
            echo -e "${YELLOW}警告: 拉取远端 tags 失败，继续使用本地 tags 计算版本${NC}"
        fi
    fi
}

compute_next_version() {
    local best_major=-1
    local best_minor=-1
    local best_patch=-1
    local major=0
    local minor=0
    local patch=1
    local tag
    local matched=0

    while IFS= read -r tag; do
        if [[ "$tag" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)-([0-9]{8})$ ]]; then
            local m_major="${BASH_REMATCH[1]}"
            local m_minor="${BASH_REMATCH[2]}"
            local m_patch="${BASH_REMATCH[3]}"
            matched=1
            if (( m_major > best_major )) \
                || (( m_major == best_major && m_minor > best_minor )) \
                || (( m_major == best_major && m_minor == best_minor && m_patch > best_patch )); then
                best_major="$m_major"
                best_minor="$m_minor"
                best_patch="$m_patch"
            fi
        fi
    done < <(git tag -l)

    if (( matched == 1 )); then
        major="$best_major"
        minor="$best_minor"
        patch="$best_patch"

        if (( patch < 9 )); then
            patch=$((patch + 1))
        else
            patch=1
            if (( minor < 9 )); then
                minor=$((minor + 1))
            else
                minor=1
                major=$((major + 1))
            fi
        fi
    fi

    echo "${major}.${minor}.${patch}"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --yes)
            YES_MODE=1
            ;;
        *)
            if [[ -n "${MANUAL_TAG}" ]]; then
                echo -e "${RED}错误: 仅支持传入一个手动 tag 参数${NC}"
                show_help
                exit 1
            fi
            MANUAL_TAG="$1"
            ;;
        esac
        shift
    done
}

validate_manual_tag() {
    local manual_tag="$1"
    local today="$2"

    if [[ ! "${manual_tag}" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)-([0-9]{8})$ ]]; then
        echo -e "${RED}错误: 手动 tag 格式必须为 vX.Y.Z-YYYYMMDD${NC}"
        exit 1
    fi

    local tag_date="${BASH_REMATCH[4]}"
    if [[ "${tag_date}" != "${today}" ]]; then
        echo -e "${RED}错误: 手动 tag 日期必须是当天 ${today}${NC}"
        exit 1
    fi
}

ensure_tag_not_exists() {
    local tag="$1"
    if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
        echo -e "${RED}错误: 标签 ${tag} 已存在${NC}"
        exit 1
    fi
}

confirm_if_needed() {
    if (( YES_MODE == 1 )); then
        echo -e "${YELLOW}已启用 --yes，跳过确认${NC}"
        return 0
    fi

    local answer=""
    read -r -p "确认创建并推送标签？[y/N] " answer
    if [[ ! "${answer}" =~ ^[yY]$ ]]; then
        echo -e "${YELLOW}已取消，未创建任何标签${NC}"
        exit 0
    fi
}

main() {
    parse_args "$@"

    local today
    today="$(current_date)"

    fetch_tags

    if [[ -n "${MANUAL_TAG}" ]]; then
        MODE="manual"
        validate_manual_tag "${MANUAL_TAG}" "${today}"
        TARGET_TAG="${MANUAL_TAG}"
    else
        MODE="auto"
        local version
        version="$(compute_next_version)"
        TARGET_TAG="v${version}-${today}"
    fi

    echo -e "${BLUE}发布预览:${NC}"
    echo -e "${YELLOW}模式:${NC} ${MODE}"
    echo -e "${YELLOW}目标标签:${NC} ${TARGET_TAG}"
    echo -e "${YELLOW}将执行:${NC} 创建并推送 tag"
    echo ""

    confirm_if_needed
    ensure_tag_not_exists "${TARGET_TAG}"

    echo -e "${YELLOW}创建标签 ${TARGET_TAG}...${NC}"
    git tag -a "${TARGET_TAG}" -m "${TARGET_TAG}"

    echo -e "${YELLOW}推送标签到远端 origin...${NC}"
    git push origin "${TARGET_TAG}"

    echo ""
    echo -e "${GREEN}✅ 发布完成${NC}"
    echo -e "${GREEN}标签 ${TARGET_TAG} 已创建并推送${NC}"
}

main "$@"
