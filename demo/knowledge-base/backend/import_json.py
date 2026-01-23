"""导入公司知识 JSON 到知识库（保留图片）"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.document import Document, SourceType, DocumentStatus
from app.models.user import User
from app.services.ingestion import document_indexer
from sqlalchemy import select


def log(msg: str):
    """立即输出日志"""
    print(msg, flush=True)


def traverse_tree(node: dict, parent_title: str = "", documents: list = None) -> list:
    """遍历树形结构，提取所有文档节点"""
    if documents is None:
        documents = []

    title = node.get("title", "").strip()
    content = node.get("content", "")  # 保留原始 HTML 内容
    update_time = node.get("updateTime", "")

    # 构建完整标题（包含父级标题）
    full_title = f"{parent_title} > {title}" if parent_title else title

    if content and content.strip():
        documents.append({
            "title": full_title,
            "content": content,  # 保留 HTML，包含图片标签
            "update_time": update_time
        })

    # 递归处理子节点
    children = node.get("children", [])
    for child in children:
        traverse_tree(child, full_title, documents)

    return documents


async def get_default_user(db: AsyncSession):
    """获取默认用户"""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("数据库中没有用户，请先创建用户")
    return user


async def import_documents_from_json(json_file: str):
    """从 JSON 文件导入文档到知识库"""
    log("=== 开始导入 JSON 知识库（保留图片） ===")

    # 读取 JSON 文件
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取所有文档节点
    all_documents = []
    result = data.get("result", [])
    for node in result:
        traverse_tree(node, "", all_documents)

    log(f"从 JSON 中提取了 {len(all_documents)} 个文档节点")

    success_count = 0
    failed_count = 0

    # 创建数据库会话
    async with async_session_factory() as db:
        # 获取默认用户
        user = await get_default_user(db)
        log(f"使用用户: {user.username}")

        # 导入每个文档
        for i, doc_data in enumerate(all_documents):
            try:
                # 创建临时文本文件（存储 HTML 内容）
                storage_path = Path("app/data/files")
                storage_path.mkdir(parents=True, exist_ok=True)

                file_name = f"temp_{i}.html"
                file_path = storage_path / file_name

                # 写入 HTML 内容
                html_content = f"<h1>{doc_data['title']}</h1>\n{doc_data['content']}"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                # 创建文档记录
                document = Document(
                    title=doc_data["title"],
                    source_type=SourceType.HTML,  # 使用 HTML 类型
                    file_path=str(file_path),
                    file_size=len(html_content.encode("utf-8")),
                    permission_level="public",
                    owner_id=user.id,
                    department_id=user.department_id,
                    status=DocumentStatus.PENDING,
                    # 在 metadata 中保存原始 HTML
                    doc_metadata={
                        "original_html": doc_data["content"],
                        "has_images": "<img" in doc_data["content"]
                    }
                )

                db.add(document)
                await db.commit()
                await db.refresh(document)

                log(f"[{i+1}/{len(all_documents)}] 正在索引: {doc_data['title'][:40]}...")

                # 索引文档
                await document_indexer.index_document(db, document.id)

                # 删除临时文件
                file_path.unlink(missing_ok=True)

                success_count += 1
                log(f"✓ 完成: {doc_data['title'][:40]}...")

            except Exception as e:
                failed_count += 1
                log(f"✗ 失败 [{doc_data['title'][:40]}...]: {e}")
                continue

    log(f"\n=== 导入完成 ===")
    log(f"成功: {success_count}")
    log(f"失败: {failed_count}")


if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "1.json"

    asyncio.run(import_documents_from_json(json_file))
