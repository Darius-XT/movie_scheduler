# 开发流程

## 启动

```bash
# 开发环境（推荐）
docker compose up -d
```

## 测试

```bash
cd backend && uv run pytest
```

规范见 [后端测试规范](../backend/docs/testing.md)，要点：

- 所有新增 public 方法必须有对应测试
- 测试目录镜像 `src/app/`，文件命名 `test_{被测模块名}.py`
- 用 `monkeypatch` 或构造函数注入隔离依赖，不做真实网络请求

## 代码修改后的检查

修改 Python 后端代码后，必须在仓库根目录运行全局 Pyright 检查：

```bash
pyright
```

发现 Pyright 报错时，优先按真实类型问题修复代码；如果是 SQLAlchemy ORM 动态字段等静态分析无法推断的场景，
只能使用项目允许的 `getattr()` + `cast()` 方式局部收敛类型，不能用 `cast()` 掩盖普通类型错误。

交付前必须满足：

- Pyright 全局检查无错误
- 后端测试通过：`cd backend && uv run pytest`
- 如果本机缺少 `pyright` 命令，必须在交付说明中明确写出未运行原因，不能默默跳过

## Git 规范

提交信息使用 Conventional Commits 格式：`<type>: <简短描述>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `refactor` | 重构（不改变行为）|
| `test` | 测试相关 |
| `chore` | 构建、依赖、配置 |
| `docs` | 文档 |

## 调试样本

`backend/.runtime/demo/` 保存各外部接口的原始响应快照，通过 `scripts/export_sample.py` 手动生成，其中的参数必须由用户手动设置修改，因此不应主动执行。调试参数（movie_id、city_id 等）统一在脚本顶部的常量块修改。
