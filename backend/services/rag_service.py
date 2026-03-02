# RAG 服务模块
# 负责文档加载、切分、向量化、检索等功能

import os
import shutil
import logging
from typing import List, Optional
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 检测是否使用 SiliconFlow API
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "")

if "siliconflow" in EMBEDDING_API_BASE.lower():
    # 使用自定义 Embeddings（避免 LangChain 兼容性问题）
    from services.custom_embeddings import SiliconFlowEmbeddings
    USE_CUSTOM_EMBEDDINGS = True
    logger.info("检测到 SiliconFlow API，使用自定义 Embeddings")
else:
    from langchain_openai import OpenAIEmbeddings
    USE_CUSTOM_EMBEDDINGS = False


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

        # 配置 embeddings API
        embedding_api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        embedding_api_base = os.getenv("EMBEDDING_API_BASE", "")
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        if USE_CUSTOM_EMBEDDINGS:
            # 使用自定义 SiliconFlow Embeddings
            logger.info(f"使用 SiliconFlow Embeddings: {embedding_model}")
            self.embeddings = SiliconFlowEmbeddings(
                api_key=embedding_api_key,
                api_base=embedding_api_base,
                model=embedding_model
            )
        elif embedding_api_base:
            # 使用自定义 API（其他提供商）
            logger.info(f"使用自定义 Embeddings API: {embedding_api_base}")
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=embedding_api_key,
                openai_api_base=embedding_api_base,
                model=embedding_model,
                chunk_size=20
            )
        else:
            # 使用 OpenAI 官方 API
            logger.info("使用 OpenAI 官方 Embeddings API")
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=embedding_api_key,
                model=embedding_model
            )

        self.is_loaded = False


    def load_documents(self, data_dir: str = "./data") -> None:     # 加载文档到向量库
        """
        加载文档到向量库（启动时调用）
        - 如果向量库已存在且有数据，直接加载，不重复添加
        - 如果向量库为空或不存在，才从文件加载

        Args:
            data_dir: 文档所在目录
        """
        try:
            # 确保数据目录存在
            os.makedirs(data_dir, exist_ok=True)

            # 如果向量库目录已存在，尝试直接加载
            if os.path.exists(self.persist_directory):
                logger.info("检测到已有向量库，尝试加载...")
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                    collection_metadata={"hnsw:space": "cosine"}
                )
                # 检查向量库是否有数据
                try:
                    count = self.vectorstore._collection.count()
                    if count > 0:
                        self.is_loaded = True
                        logger.info(f"已加载现有向量库，共 {count} 个向量，跳过重复导入")
                        return
                    else:
                        logger.info("向量库为空，将从文件重新加载")
                except Exception as e:
                    logger.warning(f"检查向量库失败: {e}，将重新创建")
                    self.vectorstore = None

            # 向量库不存在或为空，从文件加载
            all_files = os.listdir(data_dir)
            doc_files = [f for f in all_files if f.endswith(('.txt', '.pdf', '.docx'))]
            if not doc_files:
                logger.warning(f"在 {data_dir} 目录下未找到支持的文档")
                return

            # 加载所有文档
            documents = []
            for file_name in doc_files:
                file_path = os.path.join(data_dir, file_name)
                logger.info(f"正在加载文档: {file_path}")

                try:
                    file_ext = file_name.rsplit('.', 1)[-1].lower()
                    loader = self._get_loader(file_path, file_ext)
                    docs = loader.load()

                    # 统一设置 source 为文件名（与 add_document 保持一致）
                    for doc in docs:
                        doc.metadata["source"] = file_name

                    documents.extend(docs)
                    logger.info(f"成功加载 {file_name}，共 {len(docs)} 个文档块")
                except Exception as e:
                    logger.error(f"加载文件 {file_name} 失败: {e}")

            if not documents:
                logger.warning("未能加载任何文档")
                return

            # 切分文档（chunk_size=300 平衡上下文完整性和 token 限制）
            logger.info("正在切分文档...")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=80,
                length_function=len,
                separators=["\n\n", "\n", "。", " ", ""]
            )
            splits = splitter.split_documents(documents)

            logger.info(f"文档切分完成，共 {len(splits)} 段")

            # 创建新的向量库
            logger.info("创建新的向量库...")
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_metadata={"hnsw:space": "cosine"}
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

    def _get_loader(self, file_path: str, file_type: str):
        """根据文件类型返回对应的 Loader"""
        loaders = {
            'txt': lambda: TextLoader(file_path, encoding='utf-8'),
            'pdf': lambda: PyPDFLoader(file_path),
            'docx': lambda: Docx2txtLoader(file_path)
        }
        loader_func = loaders.get(file_type.lower())
        if not loader_func:
            logger.warning(f"不支持的文件类型: {file_type}，使用 TextLoader")
            return loaders['txt']()
        return loader_func()

    def add_document(self, file_path: str, file_type: str, filename: str) -> int:
        """
        添加单个文档到向量库
        - 加载文档
        - 切分 (chunk_size=500, chunk_overlap=50)
        - 添加 metadata: {"source": filename, "type": file_type}
        - 返回切分后的 chunk 数量

        Args:
            file_path: 文件路径
            file_type: 文件类型 (txt, pdf, docx)
            filename: 存储的文件名（用于 metadata）

        Returns:
            切分后的 chunk 数量
        """
        try:
            # 加载文档
            loader = self._get_loader(file_path, file_type)
            docs = loader.load()

            # 添加 metadata
            for doc in docs:
                doc.metadata["source"] = filename
                doc.metadata["type"] = file_type

            # 切分文档
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=80,
                length_function=len,
                separators=["\n\n", "\n", "。", " ", ""]
            )
            splits = splitter.split_documents(docs)

            # 添加到向量库
            if self.vectorstore is None:
                # 如果向量库不存在，创建新的
                self.vectorstore = Chroma.from_documents(
                    documents=splits,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory,
                    collection_metadata={"hnsw:space": "cosine"}
                )
                self.is_loaded = True
            else:
                # 添加到现有向量库
                self.vectorstore.add_documents(splits)

            logger.info(f"文档 {filename} 已添加到向量库，共 {len(splits)} 个 chunk")
            return len(splits)

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            raise

    def remove_document(self, filename: str) -> bool:
        """
        从向量库移除指定文档（通过 metadata 过滤）

        Args:
            filename: 要移除的文件名

        Returns:
            是否成功移除
        """
        try:
            if not self.vectorstore:
                logger.warning("向量库未加载")
                return False

            # ChromaDB 通过 metadata filter 删除
            # 需要先获取所有文档的 ID，然后删除
            collection = self.vectorstore._collection

            # 获取所有匹配的文档 ID
            results = collection.get(
                where={"source": filename},
                include=["documents", "metadatas"]
            )

            if results and results['ids']:
                # 删除匹配的文档
                collection.delete(ids=results['ids'])
                logger.info(f"文档 {filename} 已从向量库移除，删除 {len(results['ids'])} 个 chunk")
                return True
            else:
                logger.warning(f"未找到文件名为 {filename} 的文档")
                return False

        except Exception as e:
            logger.error(f"移除文档失败: {str(e)}")
            raise

    def rebuild_index(self, data_dir: str = "./data") -> int:
        """
        重建整个向量库
        - 清空向量库中的所有数据
        - 重新加载 data/ 目录下所有文档
        - 返回文档数量

        Args:
            data_dir: 文档所在目录

        Returns:
            文档数量
        """
        try:
            # 第一步：清空现有向量库中的所有数据
            if self.vectorstore is not None:
                try:
                    collection = self.vectorstore._collection
                    # 获取所有文档的 ID
                    all_docs = collection.get(include=["documents"])
                    if all_docs and all_docs.get('ids'):
                        # 删除所有文档
                        collection.delete(ids=all_docs['ids'])
                        logger.info(f"已清空向量库，删除 {len(all_docs['ids'])} 个向量")
                except Exception as e:
                    logger.warning(f"清空向量库失败: {e}")

                # 重置向量库引用
                self.vectorstore = None
                self.is_loaded = False

            # 第二步：重新加载所有文档
            # 切分并添加新文档
            documents = []
            doc_files = [f for f in os.listdir(data_dir) if f.endswith(('.txt', '.pdf', '.docx'))]

            for file_name in doc_files:
                file_path = os.path.join(data_dir, file_name)
                logger.info(f"正在加载文档: {file_path}")

                try:
                    file_ext = file_name.rsplit('.', 1)[-1].lower()
                    loader = self._get_loader(file_path, file_ext)
                    docs = loader.load()

                    # 统一设置 source 为文件名（与 add_document 保持一致）
                    for doc in docs:
                        doc.metadata["source"] = file_name

                    documents.extend(docs)
                    logger.info(f"成功加载 {file_name}，共 {len(docs)} 个文档块")
                except Exception as e:
                    logger.error(f"加载文件 {file_name} 失败: {e}")

            if not documents:
                logger.warning("未能加载任何文档")
                return 0

            # 切分文档
            logger.info("正在切分文档...")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=80,
                length_function=len,
                separators=["\n\n", "\n", "。", " ", ""]
            )
            splits = splitter.split_documents(documents)
            logger.info(f"文档切分完成，共 {len(splits)} 段")

            # 创建新的向量库（覆盖旧数据）
            logger.info("创建新的向量库...")
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_metadata={"hnsw:space": "cosine"}
            )
            self.is_loaded = True
            logger.info(f"向量库重建完成，共 {len(splits)} 个向量")

            return len(doc_files)

        except Exception as e:
            logger.error(f"重建向量库失败: {str(e)}", exc_info=True)
            raise

    def get_document_preview(self, file_path: str, max_chars: int = 3000) -> str:
        """
        获取文档预览（前 max_chars 字符）

        Args:
            file_path: 文件路径
            max_chars: 最大字符数

        Returns:
            文档预览内容
        """
        try:
            # 确定文件类型
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            loader = self._get_loader(file_path, file_ext)
            docs = loader.load()

            if docs:
                # 返回第一个文档的内容（截取指定长度）
                content = docs[0].page_content
                return content[:max_chars] + "..." if len(content) > max_chars else content
            return ""

        except Exception as e:
            logger.error(f"获取文档预览失败: {str(e)}")
            return f"预览失败: {str(e)}"