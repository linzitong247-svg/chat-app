# SQLite 聊天历史适配器
"""
将 SQLite 数据库适配为 LangChain 的 ChatMessageHistory 接口
使用 RunnableWithMessageHistory 自动管理对话历史
"""
import logging
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List

logger = logging.getLogger(__name__)


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """
    SQLite 聊天历史适配器

    将 LangChain 的消息格式与 SQLite 数据库格式互相转换，
    使 RunnableWithMessageHistory 能够自动管理历史消息。

    用法：
        history = SQLiteChatMessageHistory(conversation_id=123)
        # LangChain 会自动调用 messages 属性和 add_message 方法
    """

    def __init__(self, conversation_id: int):
        """
        初始化

        Args:
            conversation_id: 对话 ID
        """
        self.conversation_id = conversation_id

    @property
    def messages(self) -> List[BaseMessage]:
        """
        获取历史消息（LangChain 格式）

        RunnableWithMessageHistory 会调用这个属性获取历史消息

        Returns:
            LangChain 消息对象列表
        """
        from database import get_messages

        db_msgs = get_messages(self.conversation_id)
        result = []

        for msg in db_msgs:
            if msg["role"] == "user":
                result.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                result.append(AIMessage(content=msg["content"]))

        return result

    def add_message(self, message: BaseMessage) -> None:
        """
        添加消息到数据库

        RunnableWithMessageHistory 会自动调用这个方法保存新消息

        Args:
            message: LangChain 消息对象
        """
        from database import add_message

        if isinstance(message, HumanMessage):
            add_message(self.conversation_id, "user", message.content)
        elif isinstance(message, AIMessage):
            add_message(self.conversation_id, "assistant", message.content)
        else:
            logger.warning(f"不支持的消息类型: {type(message)}")

    def clear(self) -> None:
        """
        清空历史（可选实现）

        本项目不需要清空功能，留空即可
        """
        pass
