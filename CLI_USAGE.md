# Pytbox CLI 使用指南

## 简介

Pytbox CLI 是一个功能强大的命令行工具，支持 Categraf 配置管理和模板处理。它集成了 rich 库来提供美观的输出格式和日志显示。

## 安装

### 开发环境使用

在项目根目录直接执行：

```bash
./exec.py --help
```

### 安装后使用

```bash
# 安装基础版本
pip install pytbox

# 安装包含所有 CLI 功能的版本
pip install pytbox[cli]

# 然后使用
pytbox --help
```

## 功能特性

### 🎨 Rich 美化输出
- 彩色日志和状态提示
- 语法高亮显示配置文件
- 表格和树形结构显示
- 进度条和面板展示

### 📝 详细日志
- `--verbose, -v`: 显示详细调试信息
- `--quiet, -q`: 静默模式，只显示错误
- 智能的错误提示和建议

### 📊 多格式输出
- 支持 TOML、JSON、YAML 格式
- 语法高亮显示
- 文件输出和控制台显示

## 命令详解

### 基本命令结构

```bash
pytbox [全局选项] categraf [子命令] [选项] [参数]
```

### 全局选项

- `--version`: 显示版本信息
- `--help`: 显示帮助信息

### Categraf 命令组

#### 1. 获取实例配置

```bash
# 基本用法
pytbox categraf get-instances

# 指定输出格式
pytbox categraf get-instances --format json
pytbox categraf get-instances --format yaml

# 输出到文件
pytbox categraf get-instances --output config.toml

# 显示配置摘要
pytbox categraf get-instances --summary

# 树形结构显示
pytbox categraf get-instances --tree

# 详细输出模式
pytbox categraf get-instances --verbose

# 静默模式
pytbox categraf get-instances --quiet
```

**输出示例**：
```toml
[ping]
[[ping.instance]]
"10.1.1.1" = { name = "x", env = "prod"}

[prometheus]
[[prometheus.urls]]
"http://10.200.12.202:9100" = { name = "x", env = "prod"}
```

#### 2. 获取模板文件

```bash
# 获取模板内容
pytbox categraf get-template ping.toml.j2

# 显示模板信息
pytbox categraf get-template ping.toml.j2 --info

# 保存到文件
pytbox categraf get-template ping.toml.j2 --output template.j2

# 详细模式
pytbox categraf get-template ping.toml.j2 --verbose
```

#### 3. 渲染模板

```bash
# 使用命令行变量渲染
pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"10.1.1.1","name":"server1","env":"prod"}'

# 使用文件变量渲染
pytbox categraf render-template ping.toml.j2 \
  --data-file variables.json

# 预览模式（显示变量信息）
pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"10.1.1.1"}' --preview

# 输出到文件
pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"10.1.1.1","name":"server1","env":"prod"}' \
  --output rendered_config.toml
```

**变量文件示例** (`variables.json`):
```json
{
  "url": "10.1.1.1",
  "name": "server1",
  "env": "prod",
  "interface": "eth0"
}
```

#### 4. 列出模板

```bash
# 简单列表
pytbox categraf list-templates

# 详细信息
pytbox categraf list-templates --detailed
```

#### 5. 验证模板

```bash
# 验证模板语法
pytbox categraf validate-template ping.toml.j2

# 验证模板渲染
pytbox categraf validate-template ping.toml.j2 \
  --data '{"url":"10.1.1.1","name":"test","env":"dev"}'
```

## 使用场景示例

### 场景1：批量生成监控配置

```bash
# 1. 查看可用模板
pytbox categraf list-templates

# 2. 查看实例配置
pytbox categraf get-instances --tree

# 3. 为每个实例生成配置
pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"10.1.1.1","name":"web-server-1","env":"prod"}' \
  --output web-server-1.toml

pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"10.1.1.2","name":"web-server-2","env":"prod"}' \
  --output web-server-2.toml
```

### 场景2：调试模板问题

```bash
# 1. 验证模板语法
pytbox categraf validate-template ping.toml.j2 --verbose

# 2. 查看模板内容
pytbox categraf get-template ping.toml.j2 --info

# 3. 预览渲染效果
pytbox categraf render-template ping.toml.j2 \
  --data '{"url":"test"}' --preview --verbose
```

### 场景3：配置文件格式转换

```bash
# 将配置转换为不同格式
pytbox categraf get-instances --format json --output config.json
pytbox categraf get-instances --format yaml --output config.yaml
pytbox categraf get-instances --format toml --output config.toml
```

## Rich 输出特性

### 彩色日志
- ✅ 绿色：成功操作
- ⚠️ 黄色：警告信息
- ❌ 红色：错误信息
- ℹ️ 蓝色：一般信息
- 🔍 灰色：调试信息

### 语法高亮
自动检测文件类型并应用语法高亮：
- TOML 配置文件
- JSON 数据
- YAML 格式
- Jinja2 模板

### 表格显示
使用 `--detailed` 选项时，会以表格形式显示信息：

```
┏━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 模板名称      ┃ 大小   ┃ 行数 ┃ 路径                          ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ping.toml.j2  │ 156 字符│ 6 行 │ pytbox.categraf.jinja2/...    │
└───────────────┴────────┴──────┴───────────────────────────────┘
```

### 树形结构
使用 `--tree` 选项显示层次化数据：

```
Categraf 实例配置
├── ping
│   └── instance
│       └── Item 0
│           ├── 10.1.1.1
│           │   ├── name: x
│           │   └── env: prod
└── prometheus
    └── urls
        └── Item 0
            └── http://10.200.12.202:9100
                ├── name: x
                └── env: prod
```

## 错误处理

CLI 提供友好的错误提示：

```bash
# 模板不存在时的提示
❌ 模板 'nonexistent.j2' 不存在
ℹ️ 可用模板:
  - ping.toml.j2

# 语法错误时的提示
❌ 模板语法错误: Unexpected end of template. Line 3
```

## 性能优化

- 使用进度条显示长时间操作
- 并行处理多个模板信息
- 智能缓存机制
- 按需加载依赖

## 扩展功能

### 环境变量支持

```bash
export PYTBOX_DEFAULT_FORMAT=json
export PYTBOX_VERBOSE=true
pytbox categraf get-instances  # 自动使用环境变量配置
```

### 配置文件支持

创建 `~/.pytbox/config.toml`:

```toml
[cli]
default_format = "yaml"
verbose = true
quiet = false

[categraf]
template_dir = "/custom/templates"
```

这个 CLI 工具为你提供了强大而友好的命令行界面，无论是在开发环境还是生产环境中都能高效地管理 Categraf 配置。
