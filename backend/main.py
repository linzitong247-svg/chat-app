# FastAPI 主文件
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware  # 跨域资源共享
from contextlib import asynccontextmanager
import logging
import os
import asyncio
import uuid
import shutil
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 加载 .env 文件
load_dotenv()

from models import (
    CreateConversationRequest,
    SendMessageRequest,
    ConversationResponse,
    ChatResponse,
    RAGChatRequest,
    RAGChatResponse,
    KnowledgeDocument,
    DocumentUploadResponse,
    RebuildResponse,
    DocumentPreviewResponse
)
from database import (
    create_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
    delete_all_conversations,
    update_conversation_title,
    get_message_count,
    create_knowledge_document,
    list_knowledge_documents,
    get_knowledge_document,
    delete_knowledge_document,
    get_document_by_filename
)
from services.conversation import init_conversation_manager, get_conversation_manager

# ============ 日志配置 ============

# 获取日志文件的绝对路径
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'app.log')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ],
    force=True  # 强制覆盖已有的日志配置
)

logger = logging.getLogger(__name__)

# ============ 应用生命周期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的处理"""
    # 启动时执行
    logger.info("=" * 50)
    logger.info("智言 · 企业智库 V2.0 启动中...")

    # 从环境变量读取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("未设置 DEEPSEEK_API_KEY 环境变量，请设置后重启")
        # 开发环境可以硬编码（不推荐）
        # api_key = "your-api-key-here"

    if api_key:
        # 初始化对话管理器
        init_conversation_manager(api_key)
        # 初始化 RAG 服务
        manager = get_conversation_manager()
        manager.init_rag(data_dir="./data", persist_dir="./chroma_db")
        logger.info("服务初始化完成")
    else:
        logger.error("DEEPSEEK_API_KEY 未设置，聊天功能将不可用")

    yield

    # 关闭时执行
    logger.info("智言 · 企业智库关闭")


# ============ 创建 FastAPI 应用 ============

app = FastAPI(
    title="智言 · 企业智库 API",
    description="基于 LangChain 的企业级 RAG 智能问答系统",
    version="2.0.0",
    lifespan=lifespan
)

# ============ CORS 配置 ============

# 从环境变量读取允许的前端地址，默认为本地开发地址
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# ============ 基础接口 ============

@app.get("/")
async def root():
    """健康检查"""
    return {
        "message": "智言 · 企业智库 API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# ============ 对话管理接口 ============

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation_endpoint(request: CreateConversationRequest):
    """
    创建新对话

    - title: 对话标题（可选，默认"新对话"）
    """
    try:
        logger.info(f"创建对话: title={request.title}")

        title = request.title or "新对话"
        conversation_id = create_conversation(title)

        conversation = get_conversation(conversation_id)

        return ConversationResponse(
            id=conversation["id"],
            title=conversation["title"],
            created_at=conversation["created_at"]
        )

    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations", response_model=list[ConversationResponse])
async def list_conversations_endpoint(limit: int = 50):
    """
    获取对话列表

    - limit: 返回数量限制
    """
    try:
        logger.info("获取对话列表")

        conversations = list_conversations(limit)

        return [
            ConversationResponse(
                id=c["id"],
                title=c["title"],
                created_at=c["created_at"]
            )
            for c in conversations
        ]

    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_endpoint(conversation_id: int):
    """获取对话元数据"""
    try:
        conversation = get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        return ConversationResponse(
            id=conversation["id"],
            title=conversation["title"],
            created_at=conversation["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: int):
    """删除对话"""
    try:
        logger.info(f"删除对话: ID={conversation_id}")

        delete_conversation(conversation_id)

        return {"message": "对话已删除"}

    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations")
async def delete_all_conversations_endpoint():
    """删除所有对话"""
    try:
        logger.info("删除所有对话")

        count = delete_all_conversations()

        return {"message": f"已删除 {count} 条对话"}

    except Exception as e:
        logger.error(f"删除所有对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int):
    """获取对话的所有消息"""
    try:
        logger.info(f"获取对话消息: ID={conversation_id}")

        # 检查对话是否存在
        conversation = get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        from database import get_messages
        messages = get_messages(conversation_id)

        # 转换为前端期望的格式
        result = []
        for msg in messages:
            result.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["created_at"]
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/conversations/{conversation_id}/title")
async def update_conversation_title_endpoint(conversation_id: int, title: str):
    """更新对话标题"""
    try:
        logger.info(f"更新对话标题: ID={conversation_id}, title={title}")

        update_conversation_title(conversation_id, title)

        return {"message": "标题已更新"}

    except Exception as e:
        logger.error(f"更新标题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 消息接口 ============

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: SendMessageRequest):
    """
    发送消息并获取 AI 回复（普通对话）

    使用 RunnableWithMessageHistory 自动管理对话历史

    - conversation_id: 对话 ID
    - message: 用户消息
    """
    try:
        logger.info(f"收到消息: conversation_id={request.conversation_id}")

        conversation = get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        manager = get_conversation_manager()

        # 检查是否为首条消息
        msg_count = get_message_count(request.conversation_id)

        ai_message = await manager.chat(
            conversation_id=request.conversation_id,
            user_message=request.message
        )

        # 首条消息后异步生成标题
        if msg_count == 0:
            asyncio.create_task(
                manager.generate_title(request.conversation_id, request.message)
            )

        return ChatResponse(
            conversation_id=request.conversation_id,
            message={
                "role": "assistant",
                "content": ai_message,
                "created_at": datetime.now().isoformat()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/rag", response_model=RAGChatResponse)
async def rag_chat_endpoint(request: RAGChatRequest):
    """
    发送消息并获取 AI 回复（带 RAG 知识库）

    使用 RunnableWithMessageHistory 自动管理对话历史

    - conversation_id: 对话 ID
    - message: 用户消息
    - use_knowledge: 是否使用知识库（默认 true）
    """
    try:
        logger.info(f"收到 RAG 消息: conversation_id={request.conversation_id}, use_knowledge={request.use_knowledge}")

        conversation = get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        manager = get_conversation_manager()

        # 检查是否为首条消息
        msg_count = get_message_count(request.conversation_id)

        if not manager.is_rag_ready():
            logger.warning("RAG 未初始化，降级到普通对话")
            ai_message = await manager.chat(
                conversation_id=request.conversation_id,
                user_message=request.message
            )

            if msg_count == 0:
                asyncio.create_task(
                    manager.generate_title(request.conversation_id, request.message)
                )

            return RAGChatResponse(
                conversation_id=request.conversation_id,
                response=ai_message,
                context_used=[],
                timestamp=datetime.now().isoformat()
            )

        result = await manager.chat_with_rag(
            conversation_id=request.conversation_id,
            user_message=request.message,
            use_knowledge=request.use_knowledge
        )

        # 首条消息后异步生成标题
        if msg_count == 0:
            asyncio.create_task(
                manager.generate_title(request.conversation_id, request.message)
            )

        return RAGChatResponse(
            conversation_id=result["conversation_id"],
            response=result["response"],
            context_used=result["context_used"],
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG 聊天失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 知识库管理接口 ============

# 上传目录配置
UPLOAD_DIR = Path(__file__).parent / "data"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/api/knowledge/documents", response_model=list[KnowledgeDocument])
async def list_documents():
    """获取知识库文档列表"""
    try:
        logger.info("获取知识库文档列表")
        documents = list_knowledge_documents()
        return documents
    except Exception as e:
        logger.error(f"获取知识库文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge/documents", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档到知识库
    - 支持 .txt, .pdf, .docx 格式
    - 自动添加到向量库
    """
    try:
        logger.info(f"上传文档: {file.filename}, content_type: {file.content_type}")

        # 1. 验证文件类型
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        if file_ext not in ['txt', 'pdf', 'docx']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 txt, pdf, docx"
            )

        # 2. 生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # 3. 保存文件
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        file_size = len(content)

        logger.info(f"文件已保存: {file_path}, 大小: {file_size} bytes")

        # 4. 检查文件名是否已存在
        existing = get_document_by_filename(unique_filename)
        if existing:
            # 删除旧记录
            delete_knowledge_document(existing['id'])

        # 5. 保存到数据库
        doc_id = create_knowledge_document(
            filename=unique_filename,
            original_name=file.filename,
            file_type=file_ext,
            file_size=file_size
        )

        logger.info(f"数据库记录已创建: ID={doc_id}")

        # 6. 添加到向量库
        manager = get_conversation_manager()
        chunk_count = 0
        if manager and manager.rag_service:
            try:
                chunk_count = manager.rag_service.add_document(
                    file_path=str(file_path),
                    file_type=file_ext,
                    filename=unique_filename
                )
                logger.info(f"向量库更新完成: chunks={chunk_count}")
            except Exception as e:
                logger.error(f"向量库更新失败: {e}")
                # 即使向量库更新失败，也返回成功（文件已保存）

        return DocumentUploadResponse(
            id=doc_id,
            filename=unique_filename,
            original_name=file.filename,
            message="文档上传成功",
            chunks=chunk_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/knowledge/documents/{doc_id}")
async def delete_document_endpoint(doc_id: int):
    """删除知识库文档"""
    try:
        logger.info(f"删除知识库文档: ID={doc_id}")

        # 获取文档信息
        doc = get_knowledge_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 从数据库软删除
        delete_knowledge_document(doc_id)

        # 从向量库删除
        manager = get_conversation_manager()
        if manager.rag_service:
            manager.rag_service.remove_document(doc['filename'])

        # 删除文件
        file_path = UPLOAD_DIR / doc['filename']
        if file_path.exists():
            file_path.unlink()

        return {"message": "文档已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge/rebuild", response_model=RebuildResponse)
async def rebuild_vector_store():
    """重建向量库"""
    try:
        logger.info("重建向量库")

        manager = get_conversation_manager()
        if not manager:
            raise HTTPException(status_code=500, detail="对话管理器未初始化")

        if not manager.rag_service:
            raise HTTPException(status_code=500, detail="RAG 服务未初始化")

        # 获取文档数量
        documents = list_knowledge_documents()

        # 重建向量库
        logger.info(f"开始重建向量库，文档数量: {len(documents)}")
        doc_count = manager.rag_service.rebuild_index(data_dir=str(UPLOAD_DIR))

        logger.info(f"向量库重建完成: documents={doc_count}")

        return RebuildResponse(
            success=True,
            message="向量库重建成功",
            document_count=doc_count,
            chunk_count=0  # 暂时返回0，因为数据库没有存储chunk数量
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重建向量库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/documents/{doc_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(doc_id: int):
    """预览文档内容"""
    try:
        logger.info(f"预览文档: ID={doc_id}")

        doc = get_knowledge_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        file_path = UPLOAD_DIR / doc['filename']
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        manager = get_conversation_manager()
        if not manager.rag_service:
            raise HTTPException(status_code=500, detail="RAG 服务未初始化")

        content = manager.rag_service.get_document_preview(str(file_path))

        return DocumentPreviewResponse(
            content=content,
            filename=doc['original_name']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 调试接口 ============

@app.get("/api/debug/chunks")
async def debug_chunks():
    """调试：查看向量库中所有 chunk 内容"""
    try:
        manager = get_conversation_manager()
        if not manager.rag_service or not manager.rag_service.vectorstore:
            return {"error": "向量库未加载"}

        collection = manager.rag_service.vectorstore._collection
        results = collection.get(include=["documents", "metadatas"])

        chunks = []
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
            chunks.append({
                "index": i,
                "source": meta.get("source", "unknown"),
                "content": doc[:200],
                "length": len(doc)
            })

        return {"total": len(chunks), "chunks": chunks}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/search")
async def debug_search(q: str = "报销流程"):
    """调试：测试向量检索结果"""
    try:
        manager = get_conversation_manager()
        if not manager.rag_service:
            return {"error": "RAG 未初始化"}

        docs = manager.rag_service.search(q, k=3)
        results = []
        for i, doc in enumerate(docs):
            results.append({
                "rank": i,
                "source": doc.metadata.get("source", "unknown"),
                "content": doc.page_content
            })

        return {"query": q, "results": results}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/embedding")
async def debug_embedding(q: str = "报销流程"):
    """调试：直接测试 SiliconFlow embedding API"""
    try:
        manager = get_conversation_manager()
        embeddings = manager.rag_service.embeddings

        # 直接调用 embedding
        result = embeddings.embed_query(q)
        return {
            "query": q,
            "embedding_length": len(result),
            "first_5": result[:5],
            "status": "OK"
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


# ============ 启动说明 ============

if __name__ == "__main__":
    import uvicorn

    print("""
    ╔══════════════════════════════════════════════════╗
    ║       智言 · 企业智库 V2.0 - 后端服务           ║
    ╠══════════════════════════════════════════════════╣
    ║  启动前请确保:                                    ║
    ║  1. 设置 DEEPSEEK_API_KEY 环境变量                ║
    ║  2. 或在代码中硬编码 API Key（不推荐）            ║
    ╚══════════════════════════════════════════════════╝

    启动命令:
        python main.py

    或使用 uvicorn:
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000)
