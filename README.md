# PytBox

[![PyPI version](https://img.shields.io/pypi/v/pytbox.svg)](https://pypi.org/project/pytbox/)
[![Python version](https://img.shields.io/pypi/pyversions/pytbox.svg)](https://pypi.org/project/pytbox/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个集成了多种服务和实用工具的 Python 包，专为运维开发场景设计。包含 VictoriaMetrics、滴答清单(Dida365)、飞书等服务的集成工具，以及常用的时间处理等实用工具。

## 特性

- 🔍 **VictoriaMetrics 集成** - 提供时序数据库查询功能
- ⏰ **时间工具** - 常用的时间戳处理工具
- 📊 **统一响应格式** - 标准化的 API 响应结构
- 🛠 **基础工具类** - 提供 API 基类和通用功能
- 🧪 **完整测试** - 包含单元测试确保代码质量

## 安装

### 从 PyPI 安装

```bash
pip install pytbox
```

### 从源码安装

```bash
git clone https://github.com/your-username/pytbox.git
cd pytbox
pip install -e .
```

## 快速开始

### VictoriaMetrics 查询

```python
from pytbox.victoriametrics import VictoriaMetrics

# 初始化 VictoriaMetrics 客户端
vm = VictoriaMetrics(url="http://localhost:8428", timeout=5)

# 查询指标数据
result = vm.query('ping_average_response_ms')

if result.is_success():
    print("查询成功:", result.data)
else:
    print("查询失败:", result.msg)
```

### 时间工具使用

```python
from pytbox.utils.timeutils import TimeUtils

# 获取当前时间戳（秒）
timestamp = TimeUtils.get_timestamp()
print(f"当前时间戳: {timestamp}")

# 获取当前时间戳（毫秒）
timestamp_ms = TimeUtils.get_timestamp(now=False)
print(f"当前时间戳(毫秒): {timestamp_ms}")
```

### 使用基础 API 类

```python
from pytbox.common.base import BaseAPI

class MyAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://api.example.com")
    
    def make_request(self):
        # 记录请求日志
        log = self.log_request("GET", "/users", {"param": "value"})
        print("请求日志:", log)
        
        # 检查会话存活时间
        age = self.get_session_age()
        print(f"会话存活时间: {age} 秒")

api = MyAPI()
api.make_request()
```

### 统一响应格式

```python
from pytbox.utils.response import ReturnResponse

# 创建成功响应
success_response = ReturnResponse(
    code=0,
    msg="操作成功",
    data={"user_id": 123, "username": "admin"}
)

# 创建错误响应
error_response = ReturnResponse(
    code=1,
    msg="用户未找到",
    data=None
)

# 检查响应状态
if success_response.is_success():
    print("操作成功:", success_response.data)

if error_response.is_error():
    print("操作失败:", error_response.msg)
```

## 设计规格（Specs）

- [Feishu Client Spec](docs/specs/2026-02-feishu/README.md)
- [Dida365 Refactor Spec](docs/specs/2026-02-dida365-refactor/README.md)

## 文档

- [Dida365 使用文档](docs/dida365.md)

## API 文档

### VictoriaMetrics

#### `VictoriaMetrics(url, timeout=3)`

VictoriaMetrics 时序数据库客户端。

**参数:**
- `url` (str): VictoriaMetrics 服务器地址
- `timeout` (int): 请求超时时间，默认 3 秒

**方法:**

##### `query(query: str) -> ReturnResponse`

执行 PromQL 查询。

**参数:**
- `query` (str): PromQL 查询语句

**返回:**
- `ReturnResponse`: 统一响应格式，包含查询结果

### TimeUtils

#### `TimeUtils.get_timestamp(now=True) -> int`

获取时间戳。

**参数:**
- `now` (bool): True 返回秒级时间戳，False 返回毫秒级时间戳

**返回:**
- `int`: 时间戳

### ReturnResponse

统一的响应格式类，包含以下状态码：

- `0` - 成功 (SUCCESS)
- `1` - 一般错误 (ERROR)
- `2` - 警告 (WARNING)
- `3` - 未授权 (UNAUTHORIZED)
- `4` - 资源未找到 (NOT_FOUND)
- `5` - 请求超时 (TIMEOUT)
- `6` - 参数错误 (INVALID_PARAMS)
- `7` - 权限不足 (PERMISSION_DENIED)
- `8` - 服务不可用 (SERVICE_UNAVAILABLE)
- `9` - 数据库错误 (DATABASE_ERROR)
- `10` - 网络错误 (NETWORK_ERROR)

**方法:**
- `is_success() -> bool`: 判断是否为成功响应
- `is_error() -> bool`: 判断是否为错误响应

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black src/ tests/
```

### 代码检查

```bash
ruff check src/ tests/
```

## 环境变量

可以通过以下环境变量进行配置：

- `VICTORIAMETRICS_URL`: VictoriaMetrics 服务器地址（默认: http://localhost:8428）

## 发布流程

项目使用 GitHub Actions 自动发布到 PyPI：

1. 使用发布脚本创建标签（默认先预览并确认）：
   ```bash
   ./publish.sh
   ```
2. 如需手动指定标签（必须完整格式）：
   ```bash
   ./publish.sh v0.1.1-20260212
   ```
3. CI/自动化场景可跳过确认：
   ```bash
   ./publish.sh --yes
   ```
4. GitHub Actions 会在 `v*` 标签推送后自动构建并发布到 PyPI

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 更新日志

### v0.1.0
- 初始版本发布
- 添加 VictoriaMetrics 集成
- 添加时间工具类
- 添加统一响应格式
- 添加基础 API 工具类

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/your-username/pytbox/issues)
- 发送邮件至 houm01@foxmail.com

---

**PytBox** - 让运维开发更简单！ 🚀
