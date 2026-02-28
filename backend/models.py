# Pydantic 数据模型
"""
API 请求和响应的数据模型定义

所有模型使用 Pydantic BaseModel，提供：
- 自动数据验证
- 类型检查
- JSON 序列化/反序列化
- API 文档自动生成
"""
from __future__ import annotations
from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    """
    创建对话请求模型

    用于创建新的对话会话。

    Attributes:
        title (Optional[str]): 对话标题，默认为 None（后端会设置为"新对话"）

    Example:
        >>> req = CreateConversationRequest(title="技术讨论")
        >>> req = CreateConversationRequest()  # 使用默认标题
    """
    title: str | None = None  # 对话标题


class SendMessageRequest(BaseModel):
    """
    发送消息请求模型

    用于普通聊天模式，发送用户消息并获取 AI 回复。

    Attributes:
        conversation_id (int): 对话 ID，指定消息发送到哪个会话
        message (str): 用户消息内容

    Example:
        >>> req = SendMessageRequest(
        ...     conversation_id=1,
        ...     message="你好，请介绍一下自己"
        ... )
    """
    conversation_id: int
    message: str


class ConversationResponse(BaseModel):
    """
    对话响应模型

    返回对话的基本信息，用于列表展示和详情查询。

    Attributes:
        id (int): 对话唯一标识符
        title (str): 对话标题
        created_at (str): 创建时间，格式为 "YYYY-MM-DD HH:MM:SS"

    Example:
        >>> resp = ConversationResponse(
        ...     id=1,
        ...     title="技术讨论",
        ...     created_at="2026-02-16 14:30:00"
        ... )
    """
    id: int
    title: str
    created_at: str


class MessageResponse(BaseModel):
    """
    消息响应模型

    返回单条消息的详细信息。

    Attributes:
        role (str): 消息角色，"user" 或 "assistant"
        content (str): 消息内容
        created_at (str): 创建时间，ISO 8601 格式

    Example:
        >>> resp = MessageResponse(
        ...     role="assistant",
        ...     content="你好！我是 AI 助手",
        ...     created_at="2026-02-16T14:30:00"
        ... )
    """
    role: str
    content: str
    created_at: str


class ChatResponse(BaseModel):
    """
    聊天响应模型

    普通聊天模式的响应，包含对话 ID 和 AI 回复消息。

    Attributes:
        conversation_id (int): 对话 ID
        message (MessageResponse): AI 回复消息，包含 role、content、created_at

    Example:
        >>> resp = ChatResponse(
        ...     conversation_id=1,
        ...     message=MessageResponse(
        ...     role="assistant",
        ...     content="你好！有什么可以帮助你的？",
        ...     created_at="2026-02-16T14:30:00"
        )

        ... )
    """
    conversation_id: int
    message: MessageResponse


class RAGChatRequest(BaseModel):
    """
    RAG 聊天请求模型

    用于 RAG（检索增强生成）模式，AI 会先检索知识库再回答。

    Attributes:
        conversation_id (int): 对话 ID，指定消息发送到哪个会话
        message (str): 用户消息内容
        use_knowledge (bool): 是否使用知识库，默认为 True。
            - True: 先检索知识库相关内容，再基于检索结果回答
            - False: 降级为普通聊天模式

    Example:
        >>> req = RAGChatRequest(
        ...     conversation_id=1,
        ...     message="公司年假有几天？",
        ...     use_knowledge=True
        ... )
    """
    conversation_id: int
    message: str
    use_knowledge: bool = True  # 是否使用知识库


class RAGChatResponse(BaseModel):
    """
    RAG 聊天响应模型

    RAG 模式的响应，除了 AI 回复外还包含检索到的上下文信息。

    Attributes:
        conversation_id (int): 对话 ID
        response (str): AI 回复内容（Markdown 格式）
        context_used (List[str]): 检索到的相关上下文片段列表，
            空列表表示未使用知识库或未找到相关内容
        timestamp (Optional[str]): 响应时间戳，ISO 8601 格式

    Example:
        >>> resp = RAGChatResponse(
        ...     conversation_id=1,
        ...     response="根据公司政策，年假为5天。",
        ...     context_used=["公司年假5天..."],
        ...     timestamp="2026-02-16T14:30:00"
        ... )
    """
    conversation_id: int
    response: str
    context_used: list[str]
    timestamp: str | None = None
