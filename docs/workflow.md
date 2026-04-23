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

规范见 [后端测试规范](backend-testing.md)，要点：

- 所有新增 public 方法必须有对应测试
- 测试目录镜像 `src/app/`，文件命名 `test_{被测模块名}.py`
- 用 `monkeypatch` 或构造函数注入隔离依赖，不做真实网络请求

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
