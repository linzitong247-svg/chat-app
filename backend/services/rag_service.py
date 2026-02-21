# RAG 服务模块
# 负责文档加载、切分、向量化、检索等功能

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class RAGService:
    """RAG 知识库服务
    加载文档到向量库、检索相关文档、获取检索器
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        初始化 RAG 服务

        Args:
            persist_directory: 向量库持久化路径
        """
        self.persist_directory = persist_directory
        self.vectorstore = None
        # 使用 OpenAI Embeddings
        self.embeddings = OpenAIEmbeddings()
        self.is_loaded = False


    def load_documents(self, data_dir: str = "./data") -> None:     # 加载文档到向量库
        """
        加载文档到向量库

        Args:
            data_dir: 文档所在目录
        """
        try:
            # 确保数据目录存在
            os.makedirs(data_dir, exist_ok=True)

            # 检查是否有文档
            doc_files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
            if not doc_files:
                logger.warning(f"在 {data_dir} 目录下未找到 txt 文档")
                return

            # 加载所有文档
            documents = []
            for file_name in doc_files:
                file_path = os.path.join(data_dir, file_name)
                logger.info(f"正在加载文档: {file_path}")

                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
                documents.extend(docs)

            if not documents:
                logger.warning("未能加载任何文档")
                return

            # 切分文档
            logger.info("正在切分文档...")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", "。", " ", ""]
            )
            splits = splitter.split_documents(documents)

            logger.info(f"文档切分完成，共 {len(splits)} 段")

            # 创建或加载向量库
            if os.path.exists(self.persist_directory):
                logger.info("加载现有向量库...")
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            else:
                logger.info("创建新的向量库...")
                self.vectorstore = Chroma.from_documents(
                    documents=splits,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory
                )

            self.is_loaded = True
            logger.info(f"向量库创建完成，保存在: {self.persist_directory}")

        except Exception as e:
            logger.error(f"加载文档失败: {str(e)}")
            raise

    def search(self, query: str, k: int = 5) -> List[Document]:
        """
        检索相关文档

        Args:
            query: 查询内容
            k: 返回文档数量

        Returns:
            相关文档列表
        """
        if not self.is_loaded or not self.vectorstore:
            raise ValueError("向量库未加载，请先调用 load_documents()")

        try:
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )
            results = retriever.invoke(query)
            return results
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            raise

    def get_retriever(self, k: int = 3):
        """
        获取检索器

        Args:
            k: 返回文档数量

        Returns:
            检索器对象
        """
        if not self.is_loaded or not self.vectorstore:
            raise ValueError("向量库未加载，请先调用 load_documents()")

        return self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )

    def is_ready(self) -> bool:
        """检查向量库是否已加载"""
        return self.is_loaded and self.vectorstore is not None