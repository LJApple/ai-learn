# Enterprise Knowledge Base

企业智能知识库系统 - 基于 RAG 架构的 AI 问答平台

## 项目结构

```
knowledge-base/
├── backend/                 # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # 业务逻辑
│   │   │   ├── llm/        # LLM 服务
│   │   │   ├── vector/     # 向量数据库
│   │   │   ├── retrieval/  # 检索服务
│   │   │   └── ingestion/  # 数据摄取
│   │   └── utils/          # 工具函数
│   ├── tests/              # 测试
│   └── requirements.txt
├── frontend/               # 前端界面 (Next.js)
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docker/                 # Docker 配置
├── scripts/                # 部署脚本
└── docker-compose.yml
```

## 快速开始

```bash
# 启动所有服务
docker-compose up -d

# 访问服务
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000
# - Milvus: http://localhost:19530
```

## 技术栈

- **后端**: FastAPI, LangChain, SQLAlchemy
- **前端**: Next.js, shadcn/ui, TailwindCSS
- **数据库**: PostgreSQL, Milvus, Redis
- **LLM**: Qwen2.5 / vLLM
- **向量**: bge-large
