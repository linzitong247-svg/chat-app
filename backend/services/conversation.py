# 对话管理服务（生产级写法）
"""
使用 RunnableWithMessageHistory 自动管理对话历史
LangChain 会自动处理：
- 从数据库加载历史消息
- 将历史注入到提示词
- 调用 LLM 生成回复
- 保存新消息到数据库
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.chain_builder import ChatChainBuilder
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器（支持普通对话和 RAG 对话）"""

    def __init__(self, api_key: str):
        """
        初始化

        Args:
            api_key: DeepSeek API Key
        """
        self.chain_builder = ChatChainBuilder(api_key)      # 创建链构建器
        self.rag_service: RAGService | None = None             # RAG 服务
        self.rag_chain = None                               # RAG 链
        self._chain = None                                  # 普通链

    # 首次访问时创建普通链 后续访问直接返回
    def _get_chain(self):
        """获取或创建普通对话链（懒加载）"""
        if self._chain is None:
            self._chain = self.chain_builder.create_history_aware_chain()
        return self._chain

    async def chat(                                         # 普通对话
        self,
        conversation_id: int,
        user_message: str
    ) -> str:
        """
        使用 LangChain 进行对话（生产级写法）

        RunnableWithMessageHistory 会自动：
        1. 加载历史消息（通过 SQLiteChatMessageHistory）
        2. 调用 LLM
        3. 保存新消息到数据库

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息

        Returns:
            AI 回复
        """
        try:
            logger.info(f"处理消息: conversation_id={conversation_id}")

            chain = self._get_chain()

            # 调用链 - LangChain 自动管理历史！
            ai_message = await chain.ainvoke(
                {"input": user_message},
                {"configurable": {"session_id": str(conversation_id)}}
            )

            logger.info(f"消息处理成功: conversation_id={conversation_id}")
            return ai_message

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            raise

    def init_rag(self, data_dir: str = "./data", persist_dir: str = "./chroma_db"): # RAG 初始化（
        """
        初始化 RAG 服务
        加载文档到向量库、创建rag链
        Args:
            data_dir: 文档目录
            persist_dir: 向量库持久化目录
        """
        try:
            self.rag_service = RAGService(persist_directory=persist_dir)    #传入向量库持久化目录 创建向量库服务实例
            self.rag_service.load_documents(data_dir)   # 用实例方法 加载文档到向量库

            # 创建 RAG 链
            if self.rag_service.is_ready():
                retriever = self.rag_service.get_retriever(k=3)
                self.rag_chain = self.chain_builder.create_rag_chain(retriever)
                logger.info("RAG 服务初始化成功")
            else:
                logger.warning("RAG 服务初始化失败：文档库为空")

        except Exception as e:
            logger.error(f"RAG 初始化失败: {e}")
            self.rag_service = None
            self.rag_chain = None

    async def chat_with_rag(
        self,
        conversation_id: int,
        user_message: str,
        use_knowledge: bool = True
    ) -> dict[str, any]:
        """
        使用 RAG 进行对话（生产级写法）

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            use_knowledge: 是否使用知识库

        Returns:
            包含回复和上下文的字典
        """
        try:
            logger.info(f"处理 RAG 消息: conversation_id={conversation_id}, use_knowledge={use_knowledge}")

            if not self.rag_chain or not use_knowledge:
                # 不使用知识库，普通对话
                ai_message = await self.chat(conversation_id, user_message)
                return {
                    "response": ai_message,
                    "context_used": [],
                    "conversation_id": conversation_id,
                    "timestamp": None
                }

            # 检索相关文档
            context_docs = self.rag_service.search(user_message, k=3)
            context_texts = [doc.page_content for doc in context_docs]

            # 调试日志：打印检索到的文档内容
            logger.info(f"检索到 {len(context_docs)} 个文档片段:")
            for i, doc in enumerate(context_docs):
                logger.info(f"  [Chunk {i}] source={doc.metadata.get('source', 'N/A')}: {doc.page_content[:100]}...")

            # 调用 RAG 链 - LangChain 自动管理历史！
            ai_message = await self.rag_chain.ainvoke(
                {"input": user_message},
                {"configurable": {"session_id": str(conversation_id)}}
            )

            logger.info(f"RAG 消息处理成功: conversation_id={conversation_id}")
            return {
                "response": ai_message,
                "context_used": context_texts,
                "conversation_id": conversation_id,
                "timestamp": None
            }

        except Exception as e:
            logger.error(f"处理 RAG 消息失败: {e}")
            # 降级到普通对话
            logger.info("降级到普通对话模式")
            ai_message = await self.chat(conversation_id, user_message)
            return {
                "response": ai_message,
                "context_used": [],
                "conversation_id": conversation_id,
                "timestamp": None
            }

    async def generate_title(self, conversation_id: int, first_message: str) -> str:
        """根据首条消息生成对话标题"""
        try:
            from services.chain_builder import ChatChainBuilder
            llm = self.chain_builder.create_llm(temperature=0.3)
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个标题生成助手。用10个字以内概括用户消息的主题，直接输出标题，不要加引号或其他格式。"),
                ("human", "{message}")
            ])

            chain = prompt | llm | StrOutputParser()
            title = await chain.ainvoke({"message": first_message})
            title = title.strip().strip('"\'')

            # 限制长度
            if len(title) > 20:
                title = title[:20]

            # 更新数据库
            from database import update_conversation_title
            update_conversation_title(conversation_id, title)

            logger.info(f"生成标题: conversation_id={conversation_id}, title={title}")
            return title

        except Exception as e:
            logger.error(f"生成标题失败: {e}")
            return ""

    def is_rag_ready(self) -> bool:
        """检查 RAG 是否就绪"""
        return self.rag_chain is not None and self.rag_service is not None


# 全局对话管理器实例
_conversation_manager: ConversationManager = None


def get_conversation_manager() -> ConversationManager:
    """获取对话管理器实例
    是「使用」已经创建好的对话管理器（从盒子里拿东西）"""
    global _conversation_manager
    if _conversation_manager is None:
        raise RuntimeError("对话管理器未初始化")
    return _conversation_manager


def init_conversation_manager(api_key: str):
    """初始化对话管理器
    是「创建」对话管理器（给空盒子装东西）"""
    global _conversation_manager
    _conversation_manager = ConversationManager(api_key)
    logger.info("对话管理器初始化成功")
