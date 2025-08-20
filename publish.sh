#!/usr/bin/bash

# 发布脚本 - 自动化版本发布流程
# 用法: ./publish.sh <version> [comment]
# 示例: ./publish.sh 1.0.0 "添加新功能"

set -e  # 遇到错误立即退出

VERSION=$1
COMMENT=$2

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}用法:${NC}"
    echo -e "  $0 <version> [comment]"
    echo -e ""
    echo -e "${BLUE}参数:${NC}"
    echo -e "  version    版本号 (必需, 支持多种格式)"
    echo -e "  comment    提交备注 (可选, 默认: 'Released v<version>')"
    echo -e ""
    echo -e "${BLUE}示例:${NC}"
    echo -e "  $0 v20250818.1"
    echo -e "  $0 20250818.2 '修复重要bug'"
    echo -e "  $0 v20250819.1 '新增功能'"
    echo -e "  $0 1.0.0 '传统版本号格式'"
}

# 验证版本号格式（支持多种格式）
validate_version() {
    # 移除前缀 v（如果有的话）
    local clean_version="${1#v}"
    
    # 支持多种版本号格式，只要不为空即可
    if [[ -z "$clean_version" ]]; then
        echo -e "${RED}错误: 版本号不能为空${NC}"
        return 1
    fi
    
    # 简单检查：确保版本号只包含数字、字母、点号、连字符
    if [[ ! $clean_version =~ ^[a-zA-Z0-9.-]+$ ]]; then
        echo -e "${RED}错误: 版本号只能包含字母、数字、点号和连字符${NC}"
        return 1
    fi
}

# 检查参数
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

if [ -z "$VERSION" ]; then
    echo -e "${RED}错误: 请提供版本号${NC}"
    show_help
    exit 1
fi

# 验证版本号格式
if ! validate_version "$VERSION"; then
    exit 1
fi

# 规范化版本号：确保以 v 开头
if [[ ! $VERSION =~ ^v ]]; then
    NORMALIZED_VERSION="v$VERSION"
else
    NORMALIZED_VERSION="$VERSION"
fi

# 设置默认提交信息
if [ -z "$COMMENT" ]; then
    COMMIT_MSG="Released $NORMALIZED_VERSION"
else
    COMMIT_MSG="Released $NORMALIZED_VERSION: $COMMENT"
fi

echo -e "${BLUE}开始发布流程...${NC}"
echo -e "${YELLOW}输入版本号:${NC} $VERSION"
echo -e "${YELLOW}规范化版本号:${NC} $NORMALIZED_VERSION"
echo -e "${YELLOW}提交信息:${NC} $COMMIT_MSG"
echo ""

# 检查是否有未提交的更改
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}检测到未提交的更改，正在添加到暂存区...${NC}"
    git add .
else
    echo -e "${GREEN}工作目录干净，无需添加文件${NC}"
fi

# 检查标签是否已存在
if git tag -l | grep -q "^$NORMALIZED_VERSION$"; then
    echo -e "${RED}错误: 标签 $NORMALIZED_VERSION 已存在${NC}"
    echo -e "${YELLOW}现有标签:${NC}"
    git tag -l | grep "^v" | sort -V | tail -5
    exit 1
fi

# 更新 pyproject.toml 中的版本号
if [ -f "pyproject.toml" ]; then
    echo -e "${YELLOW}更新 pyproject.toml 中的版本号...${NC}"
    if command -v sed >/dev/null 2>&1; then
        # 使用 sed 更新版本号（去掉 v 前缀用于 pyproject.toml）
        CLEAN_VERSION="${NORMALIZED_VERSION#v}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^version = \".*\"/version = \"$CLEAN_VERSION\"/" pyproject.toml
        else
            # Linux
            sed -i "s/^version = \".*\"/version = \"$CLEAN_VERSION\"/" pyproject.toml
        fi
        git add pyproject.toml
        echo -e "${GREEN}版本号已更新为 $CLEAN_VERSION${NC}"
    else
        echo -e "${YELLOW}警告: 未找到 sed 命令，请手动更新 pyproject.toml 中的版本号${NC}"
    fi
fi

# 提交更改
echo -e "${YELLOW}提交更改...${NC}"
git commit -m "$COMMIT_MSG"

# 创建标签
echo -e "${YELLOW}创建标签 $NORMALIZED_VERSION...${NC}"
git tag -a "$NORMALIZED_VERSION" -m "$NORMALIZED_VERSION"

# 推送到远程仓库
echo -e "${YELLOW}推送标签到远程仓库...${NC}"
git push --tag

echo -e "${YELLOW}推送代码到远程仓库...${NC}"
git push

echo ""
echo -e "${GREEN}✅ 发布完成!${NC}"
echo -e "${GREEN}版本 $NORMALIZED_VERSION 已成功发布${NC}"
echo -e "${BLUE}GitHub Actions 将自动构建并发布到 PyPI${NC}"
echo ""
echo -e "${YELLOW}可以通过以下链接查看发布状态:${NC}"
echo -e "- GitHub Releases: https://github.com/your-username/pytbox/releases"
echo -e "- GitHub Actions: https://github.com/your-username/pytbox/actions"
echo -e "- PyPI: https://pypi.org/project/pytbox/"