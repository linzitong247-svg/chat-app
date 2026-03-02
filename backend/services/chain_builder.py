# LangChain 链构建器
"""
生产级对话链构建：
- 使用 LCEL 语法（管道操作符）
- 使用 RunnableWithMessageHistory 自动管理历史
- 支持 RAG 检索增强
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
from operator import itemgetter
import logging

logger = logging.getLogger(__name__)


class ChatChainBuilder:
    """聊天链构建器（生产级写法）"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """
        初始化

        Args:
            api_key: DeepSeek API Key
            base_url: API 地址
        """
        self.api_key = api_key
        self.base_url = base_url
        self._chain = None
        self._rag_chain = None

    def create_llm(self, temperature: float = 0.7, streaming: bool = False):
        """创建 LLM 实例"""
        return ChatOpenAI(
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            model="deepseek-chat",
            temperature=temperature,
            request_timeout=60,
            streaming=streaming
        )

    def create_history_aware_chain(self, system_prompt: str = "你叫智言，是企业智能知识库问答助手。请将回复控制在200到250字。"):
        """
        创建带历史管理的对话链（生产级写法）

        使用 RunnableWithMessageHistory，LangChain 会自动：
        1. 从数据库加载历史消息
        2. 将历史消息注入到提示词中
        3. 调用 LLM 生成回复
        4. 将新消息保存到数据库

        Returns:
            RunnableWithMessageHistory: 可调用对象
        """
        llm = self.create_llm()

        # 创建提示词模板（使用 placeholder，LangChain 自动填充）
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),  # LangChain 自动填充历史
            ("human", "{input}")
        ])

        # 创建基础链（LCEL 方式）
        base_chain = prompt | llm | StrOutputParser()

        # 包装成带历史管理的链
        chain = RunnableWithMessageHistory(
            base_chain,
            # 工厂函数：根据 session_id 获取历史对象
            self._get_history_factory,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        logger.info("创建带历史管理的对话链")
        return chain

    def create_rag_chain(self, retriever, system_prompt: str = None):
        """
        创建带历史管理的 RAG 对话链（生产级写法）

        Args:
            retriever: 检索器对象
            system_prompt: 系统提示词

        Returns:
            RunnableWithMessageHistory: RAG 链
        """
        llm = self.create_llm()

        # 默认 RAG 系统提示词
        if system_prompt is None:
            system_prompt = """你叫智言，是企业智能知识库问答助手。基于以下上下文回答用户的问题。

如果上下文中没有相关信息，请说"根据已知信息无法回答"。

回答要求：
1. 回复控制在200到250字
2. 必须使用 Markdown 格式，结构清晰
3. 必须使用小标题（###）、列表（- 或 1.）、加粗（**）等格式
4. 每个要点用列表呈现，关键词加粗

上下文：
{context}"""

        # 创建 RAG 提示词
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),  # LangChain 自动填充
            ("human", "{input}")
        ])

        # 使用 LCEL 构建 RAG 基础链
        # 关键：retriever 需要先提取 input 字符串，才能正确检索
        base_chain = (
            {
                "context": itemgetter("input") | retriever,
                "input": itemgetter("input"),
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        # 包装成带历史管理的 RAG 链
        rag_chain = RunnableWithMessageHistory(
            base_chain,
            self._get_history_factory,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        logger.info("创建带历史管理的 RAG 对话链")
        return rag_chain

    def _get_history_factory(self, session_id: str):
        """
        历史对象工厂函数

        RunnableWithMessageHistory 会调用这个函数获取 ChatMessageHistory 对象

        Args:
            session_id: 会话 ID（对应 conversation_id）

        Returns:
            SQLiteChatMessageHistory 对象
        """
        from services.chat_history import SQLiteChatMessageHistory
        return SQLiteChatMessageHistory(conversation_id=int(session_id))


# ============ 使用示例 ============

"""
# 示例 1：简单对话（生产级写法）
builder = ChatChainBuilder(api_key="your-api-key")
chain = builder.create_history_aware_chain()

# 调用 - LangChain 自动管理历史！
response = chain.invoke(
    {"input": "我叫小明"},
    {"configurable": {"session_id": "123"}}  # 自动加载/保存历史
)
print(response)


# 示例 2：RAG 对话（生产级写法）
builder = ChatChainBuilder(api_key="your-api-key")
rag_chain = builder.create_rag_chain(retriever)

# 调用 - 自动检索 + 自动管理历史！
response = rag_chain.invoke(
    {"input": "公司年假几天？"},
    {"configurable": {"session_id": "123"}}
)
print(response)
"""
