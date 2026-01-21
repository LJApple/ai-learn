# 测试指南

## 环境要求

- Python 3.11+
- Docker & Docker Compose
- Node.js 20+ (用于前端)

## 快速测试

### 1. 语法检查

```bash
cd backend
python test_syntax.py
```

### 2. 单元测试

```bash
cd backend

# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_api.py -v

# 运行测试并显示覆盖率
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

### 3. Docker 集成测试

```bash
# 启动所有服务
docker-compose up -d

# 等待服务就绪
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

## API 测试

### 健康检查

```bash
curl http://localhost:8000/health
```

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "title=测试文档" \
  -F "source_type=pdf" \
  -F "permission_level=department"
```

### 问答测试

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "公司年假政策是什么？",
    "top_k": 5
  }'
```

### 获取会话列表

```bash
curl http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 手动测试清单

### 后端功能

- [ ] 健康检查接口响应正常
- [ ] 文档上传成功
- [ ] 文档列表返回正确
- [ ] 问答返回答案和来源
- [ ] 会话历史保存正常
- [ ] 权限过滤生效

### 前端功能

- [ ] 页面正常加载
- [ ] 可以发送问题
- [ ] 答案正常显示
- [ ] 来源信息显示
- [ ] 文档上传可用

## 性能测试

### 使用 Apache Bench

```bash
# 测试问答接口
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -p request.json \
  -T application/json \
  http://localhost:8000/api/v1/chat/completions
```

### 使用 wrk

```bash
wrk -t4 -c100 -d30s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -s post.lua \
  http://localhost:8000/api/v1/chat/completions
```

## 调试技巧

### 查看 Docker 日志

```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f backend
docker-compose logs -f milvus
docker-compose logs -f postgres
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入数据库容器
docker-compose exec postgres psql -U kb_user -d knowledge_base

# 进入 Milvus 容器
docker-compose exec milvus bash
```

### 数据库检查

```sql
-- 查看文档数量
SELECT COUNT(*) FROM documents;

-- 查看文档状态
SELECT status, COUNT(*) FROM documents GROUP BY status;

-- 查看最近的消息
SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;
```

## 常见问题

### 1. Milvus 连接失败

```bash
# 检查 Milvus 是否运行
docker-compose ps milvus

# 重启 Milvus
docker-compose restart milvus
```

### 2. 向量维度不匹配

确保配置文件中的维度与模型一致：
```
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5  # 1024 维
MILVUS_DIMENSION=1024
```

### 3. LLM 服务无响应

检查 vLLM 服务是否启动：
```bash
curl http://localhost:8001/health
```

## CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: cd backend && pytest tests/ -v
```
