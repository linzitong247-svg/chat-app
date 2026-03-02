# -*- coding: utf-8 -*-
"""
自定义 SiliconFlow Embeddings
直接调用 API，避免 LangChain OpenAIEmbeddings 的兼容性问题
"""
import os
import requests
from typing import List
from langchain_core.embeddings import Embeddings
from dotenv import load_dotenv

load_dotenv()


class SiliconFlowEmbeddings(Embeddings):
    """SiliconFlow Embeddings - 直接调用 API"""

    def __init__(
        self,
        api_key: str = None,
        api_base: str = "https://api.siliconflow.cn/v1",
        model: str = "Qwen/Qwen3-Embedding-8B",
        batch_size: int = 20
    ):
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1")
        self.model = model or os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
        self.batch_size = batch_size

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """调用 API 生成向量"""
        response = requests.post(
            f"{self.api_base}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "input": texts,
                "encoding_format": "float"
            },
            timeout=60
        )

        if response.status_code != 200:
            raise ValueError(f"Embedding API 错误: {response.status_code} - {response.text}")

        result = response.json()
        # 按 index 排序返回
        embeddings = [None] * len(texts)
        for item in result["data"]:
            embeddings[item["index"]] = item["embedding"]

        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入多个文档"""
        all_embeddings = []

        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = self._embed(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        return self._embed([text])[0]


# 使用示例
if __name__ == "__main__":
    embeddings = SiliconFlowEmbeddings()

    # 测试
    vec = embeddings.embed_query("年假")
    print(f'维度: {len(vec)}')
    print(f'前5个值: {vec[:5]}')
