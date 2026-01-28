#!/bin/bash

# Claude Code Environment Setup Script
# Author: Claude Assistant
# Purpose: Automatically configure environment variables for Claude Code on macOS and Linux

set -e  # Exit on error

# Colors for output
RED='\033[1;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to display current environment variables
display_current_env() {
    print_info "当前环境变量状态："
    echo -e "${BLUE}----------------------------------------${NC}"
    
    # Get current shell type for proper variable display
    CURRENT_SHELL=$(basename "$SHELL")
    
    if [[ "$CURRENT_SHELL" == "fish" ]]; then
        # Fish shell syntax
        echo "ANTHROPIC_BASE_URL=$(set -q ANTHROPIC_BASE_URL && echo $ANTHROPIC_BASE_URL || echo '(未设置)')"
        echo "ANTHROPIC_API_KEY=$(set -q ANTHROPIC_API_KEY && echo '****'${ANTHROPIC_API_KEY: -4} || echo '(未设置)')"
        echo "ANTHROPIC_AUTH_TOKEN=$(set -q ANTHROPIC_AUTH_TOKEN && echo $ANTHROPIC_AUTH_TOKEN || echo '(未设置)')"
    else
        # Bash/Zsh syntax
        if [ -n "$ANTHROPIC_BASE_URL" ]; then
            echo "ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
        else
            echo "ANTHROPIC_BASE_URL=(未设置)"
        fi
        
        if [ -n "$ANTHROPIC_API_KEY" ]; then
            echo "ANTHROPIC_API_KEY=****${ANTHROPIC_API_KEY: -4}"
        else
            echo "ANTHROPIC_API_KEY=(未设置)"
        fi
        
        if [ -n "$ANTHROPIC_AUTH_TOKEN" ]; then
            echo "ANTHROPIC_AUTH_TOKEN=$ANTHROPIC_AUTH_TOKEN"
        else
            echo "ANTHROPIC_AUTH_TOKEN=(未设置)"
        fi
    fi
    
    echo -e "${BLUE}----------------------------------------${NC}"
}

# Header
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Claude Code Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Display current environment variables before any changes
display_current_env
echo

# Check if API key is provided as argument
if [ $# -eq 0 ]; then
    print_error "请提供API密钥作为参数"
    echo "使用方法: $0 <your-api-key>"
    exit 1
fi

ANTHROPIC_API_KEY="$1"
ANTHROPIC_BASE_URL="http://10.250.1.173:12654/claude-proxy"

# Detect OS and shell
detect_os_and_shell() {
    print_info "检测操作系统和Shell环境..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    # Detect Shell
    CURRENT_SHELL=$(basename "$SHELL")
    
    # Determine config file based on shell
    case "$CURRENT_SHELL" in
        bash)
            if [[ "$OS" == "macOS" ]]; then
                CONFIG_FILE="$HOME/.bash_profile"
            else
                CONFIG_FILE="$HOME/.bashrc"
            fi
            ;;
        zsh)
            CONFIG_FILE="$HOME/.zshrc"
            ;;
        fish)
            CONFIG_FILE="$HOME/.config/fish/config.fish"
            ;;
        *)
            print_error "不支持的Shell: $CURRENT_SHELL"
            exit 1
            ;;
    esac
    
    print_success "检测完成 - 系统: $OS, Shell: $CURRENT_SHELL"
    print_info "配置文件: $CONFIG_FILE"
}

# Function to add environment variables to config file
add_env_vars() {
    print_info "开始配置环境变量..."
    
    # Create backup
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "已备份原配置文件"
    fi
    
    # Check if variables already exist
    if grep -q "ANTHROPIC_BASE_URL" "$CONFIG_FILE" 2>/dev/null || grep -q "ANTHROPIC_API_KEY" "$CONFIG_FILE" 2>/dev/null; then
        print_warning "检测到已存在的Claude Code环境变量配置"
        print_info "正在清理所有现有配置..."
        
        # Remove ALL existing ANTHROPIC environment variable configurations
        # For bash/zsh: export VARIABLE=...
        # For fish: set -x VARIABLE ...
        if [[ "$CURRENT_SHELL" == "fish" ]]; then
            # Fish shell: remove 'set -x VARIABLE ...' patterns
            # Using -E for extended regex on macOS/BSD sed
            sed -i.tmp -E '/^[[:space:]]*set[[:space:]]+-x[[:space:]]+ANTHROPIC_BASE_URL/d' "$CONFIG_FILE" 2>/dev/null || true
            sed -i.tmp -E '/^[[:space:]]*set[[:space:]]+-x[[:space:]]+ANTHROPIC_API_KEY/d' "$CONFIG_FILE" 2>/dev/null || true
            sed -i.tmp -E '/^[[:space:]]*set[[:space:]]+-x[[:space:]]+ANTHROPIC_AUTH_TOKEN/d' "$CONFIG_FILE" 2>/dev/null || true
        else
            # Bash/Zsh: remove 'export VARIABLE=...' patterns
            # Using -E for extended regex on macOS/BSD sed
            sed -i.tmp -E '/^[[:space:]]*export[[:space:]]+ANTHROPIC_BASE_URL=/d' "$CONFIG_FILE" 2>/dev/null || true
            sed -i.tmp -E '/^[[:space:]]*export[[:space:]]+ANTHROPIC_API_KEY=/d' "$CONFIG_FILE" 2>/dev/null || true
            sed -i.tmp -E '/^[[:space:]]*export[[:space:]]+ANTHROPIC_AUTH_TOKEN=/d' "$CONFIG_FILE" 2>/dev/null || true
        fi
        
        # Also remove the marked sections for backward compatibility
        sed -i.tmp '/# Claude Code Environment Variables/,/# End Claude Code Environment Variables/d' "$CONFIG_FILE" 2>/dev/null || true
        
        # Clean up temporary files
        rm -f "$CONFIG_FILE.tmp" 
        
        print_success "已彻底清理所有旧配置，准备写入新配置"
    fi
    
    # Add environment variables based on shell type
    if [[ "$CURRENT_SHELL" == "fish" ]]; then
        cat >> "$CONFIG_FILE" << EOF

# Claude Code Environment Variables
set -x ANTHROPIC_BASE_URL "$ANTHROPIC_BASE_URL"
set -x ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
set -x ANTHROPIC_AUTH_TOKEN ""
# End Claude Code Environment Variables
EOF
    else
        cat >> "$CONFIG_FILE" << EOF

# Claude Code Environment Variables
export ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL"
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export ANTHROPIC_AUTH_TOKEN=""
# End Claude Code Environment Variables
EOF
    fi
    
    print_success "环境变量已写入配置文件"
}

# Function to update .claude.json
update_claude_json() {
    print_info "更新 ~/.claude.json 配置..."
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_error "需要安装 jq 工具"
        if [[ "$OS" == "macOS" ]]; then
            print_info "请运行: brew install jq"
        else
            print_info "请运行: sudo apt-get install jq (Ubuntu/Debian) 或 sudo yum install jq (CentOS/RHEL)"
        fi
        return 1
    fi
    
    # Execute the jq command
    print_info "添加API密钥到Claude配置..."
    
    # Get the last 20 characters of the API key
    KEY_SUFFIX="${ANTHROPIC_API_KEY: -20}"
    
    # Create .claude.json if it doesn't exist
    if [ ! -f "$HOME/.claude.json" ]; then
        echo '{}' > "$HOME/.claude.json"
        print_info "创建新的 ~/.claude.json 文件"
    fi
    
    # Update the JSON file
    if (cat ~/.claude.json 2>/dev/null || echo 'null') | jq --arg key "$KEY_SUFFIX" '(. // {}) | .customApiKeyResponses.approved |= ([.[]?, $key] | unique)' > ~/.claude.json.tmp; then
        mv ~/.claude.json.tmp ~/.claude.json
        print_success "Claude配置已更新"
        
        # Display the updated customApiKeyResponses
        print_info "更新后的 customApiKeyResponses 内容:"
        echo -e "${BLUE}----------------------------------------${NC}"
        jq '.customApiKeyResponses' ~/.claude.json 2>/dev/null || echo "{}"
        echo -e "${BLUE}----------------------------------------${NC}"
    else
        print_error "更新Claude配置失败"
        rm -f ~/.claude.json.tmp
        return 1
    fi
}

# Function to source the config file
activate_config() {
    print_info "激活配置..."
    
    # Export variables for current session
    export ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL"
    export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
    export ANTHROPIC_AUTH_TOKEN=""
    
    print_success "环境变量已在当前会话中激活"
    print_info "要在新的终端会话中使用，请运行以下命令："
    
    if [[ "$CURRENT_SHELL" == "fish" ]]; then
        echo -e "${GREEN}source $CONFIG_FILE${NC}"
    else
        echo -e "${GREEN}source $CONFIG_FILE${NC}"
    fi
    
    print_info "或者重新打开终端窗口"
}

# Function to verify configuration
verify_config() {
    print_info "验证配置..."
    
    # Check if variables are set
    if [ -n "$ANTHROPIC_BASE_URL" ] && [ -n "$ANTHROPIC_API_KEY" ]; then
        print_success "环境变量验证成功"
        echo "ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
        echo "ANTHROPIC_API_KEY: ****${ANTHROPIC_API_KEY: -4}"
        echo "ANTHROPIC_AUTH_TOKEN: ${ANTHROPIC_AUTH_TOKEN:-\"\"}"
    else
        print_error "环境变量验证失败"
        return 1
    fi
    
    # Check .claude.json
    if [ -f "$HOME/.claude.json" ]; then
        if jq -e '.customApiKeyResponses.approved' "$HOME/.claude.json" &>/dev/null; then
            print_success "Claude配置文件验证成功"
        else
            print_warning "Claude配置文件存在但可能不完整"
        fi
    else
        print_error "Claude配置文件不存在"
    fi
}

# Main execution
main() {
    # Step 1: Detect OS and Shell
    detect_os_and_shell
    echo
    
    # Step 2: Add environment variables
    add_env_vars
    echo
    
    # Step 3: Update .claude.json
    update_claude_json
    echo
    
    # Step 4: Activate configuration
    activate_config
    echo
    
    # Step 5: Verify configuration
    verify_config
    echo
    
    print_success "Claude Code环境配置完成！"
    echo -e "${BLUE}========================================${NC}"
    
    # Important reminder in red
    echo
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                          ║${NC}"
    echo -e "${RED}║    请关闭终端后重新打开，开始 claude code 使用～        ║${NC}"
    echo -e "${RED}║                                                          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Run main function
main

# Exit successfully
exit 0