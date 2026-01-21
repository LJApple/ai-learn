# 知识库系统测试总结

## 已创建的测试文件

### 测试代码
- `backend/tests/test_api.py` - API 端点测试
- `backend/tests/test_services.py` - 服务层单元测试
- `backend/test_syntax.py` - Python 语法检查脚本

### 测试配置
- `backend/pyproject.toml` - 项目配置和测试设置
- `TESTING.md` - 详细测试指南

### 启动脚本
- `scripts/dev.sh` - Linux/Mac 开发启动脚本
- `scripts/dev.bat` - Windows 开发启动脚本

## 快速开始测试

### Windows 用户
```batch
cd E:\code\demo\knowledge-base
scripts\dev.bat
```

### Linux/Mac 用户
```bash
cd knowledge-base
chmod +x scripts/dev.sh
./scripts/dev.sh
```

## 测试层级

```
┌─────────────────────────────────────────────────────────────┐
│                      测试金字塔                              │
├─────────────────────────────────────────────────────────────┤
│                        E2E 测试                              │
│                    (Docker Compose)                          │
│  ┌───────────────────────────────────────────────────────┐  │
││                      集成测试                            │  │
││                 (API + Database)                         │  │
││  ┌───────────────────────────────────────────────────┐  │  │
│││                    单元测试                          │  │  │
│││            (Services, Models, Utils)                 │  │  │
│││  ┌───────────────────────────────────────────────┐  │  │  │
││││                  语法检查                        │  │  │  │
││││           (Python AST Validation)                │  │  │  │
│││└───────────────────────────────────────────────┘  │  │  │
││└───────────────────────────────────────────────────┘  │  │
│└───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 手动测试步骤

### 第一步：启动基础设施

```batch
# Windows
scripts\dev.bat

# 或手动启动
docker-compose up -d postgres redis minio etcd milvus-minio milvus
```

### 第二步：启动后端

```batch
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 第三步：运行测试

```batch
# 语法检查
python test_syntax.py

# 单元测试
pytest tests/ -v

# 带覆盖率的测试
pytest tests/ --cov=app --cov-report=html
```

### 第四步：API 手动测试

```batch
# 健康检查
curl http://localhost:8000/health

# 访问 API 文档
# 浏览器打开: http://localhost:8000/docs
```

## 测试覆盖范围

| 模块 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| API 端点 | test_api.py | 健康检查、认证、路由 |
| 服务层 | test_services.py | Embedding、Chunker、Parser |
| 数据模型 | - | SQLAlchemy 模型验证 |
| 向量检索 | - | Milvus 集成测试 |

## 当前状态

✅ 代码结构完整
✅ 测试框架配置完成
⏳ 等待本地环境运行

## 下一步

1. **安装依赖**
   ```batch
   cd backend
   pip install -r requirements.txt
   pip install pytest pytest-asyncio httpx
   ```

2. **配置环境**
   ```batch
   # 复制并编辑 .env
   copy backend\.env.example backend\.env
   ```

3. **启动服务并测试**
   ```batch
   # 启动基础设施
   docker-compose up -d

   # 运行测试
   pytest tests/ -v
   ```

## 测试结果示例

成功运行后应看到类似输出：

```
tests/test_api.py::TestHealth::test_health_check PASSED
tests/test_api.py::TestChat::test_chat_requires_auth PASSED
tests/test_services.py::TestTextChunker::test_chunk_empty_text PASSED

======================== 15 passed in 2.34s ========================
```
