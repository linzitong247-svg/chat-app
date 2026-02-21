# FastAPI 主文件
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware  # 跨域资源共享
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# 加载 .env 文件
load_dotenv()

from models import (
    CreateConversationRequest,
    SendMessageRequest,
    ConversationResponse,
    ChatResponse,
    RAGChatRequest,
    RAGChatResponse
)
from database import (
    create_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
    update_conversation_title
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
    logger.info("DeepSeek 聊天应用启动中...")

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
    logger.info("DeepSeek 聊天应用关闭")


# ============ 创建 FastAPI 应用 ============

app = FastAPI(
    title="DeepSeek 聊天 API",
    description="基于 LangChain 的多轮对话系统",
    version="1.0.0",
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
        "message": "DeepSeek 聊天 API",
        "version": "1.0.0",
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

        # 从数据库获取对话详情 并 检查对话是否存在
        conversation = get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        # 获取对话管理器
        manager = get_conversation_manager()

        # 调用对话管理器（LangChain 自动管理历史）
        ai_message = await manager.chat(
            conversation_id=request.conversation_id,
            user_message=request.message
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

        # 检查对话是否存在
        conversation = get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        # 获取对话管理器
        manager = get_conversation_manager()

        # 检查 RAG 是否可用
        if not manager.is_rag_ready():
            logger.warning("RAG 未初始化，降级到普通对话")
            ai_message = await manager.chat(
                conversation_id=request.conversation_id,
                user_message=request.message
            )
            return RAGChatResponse(
                conversation_id=request.conversation_id,
                response=ai_message,
                context_used=[],
                timestamp=datetime.now().isoformat()
            )

        # 调用 RAG 对话
        result = await manager.chat_with_rag(
            conversation_id=request.conversation_id,
            user_message=request.message,
            use_knowledge=request.use_knowledge
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


# ============ 启动说明 ============

if __name__ == "__main__":
    import uvicorn

    print("""
    ╔════════════════════════════════════════════════╗
    ║       DeepSeek 聊天应用 - 后端服务             ║
    ╠════════════════════════════════════════════════╣
    ║  启动前请确保:                                  ║
    ║  1. 设置 DEEPSEEK_API_KEY 环境变量              ║
    ║  2. 或在代码中硬编码 API Key（不推荐）          ║
    ╚════════════════════════════════════════════════╝

    启动命令:
        python main.py

    或使用 uvicorn:
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000)
