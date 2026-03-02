# 数据库连接和操作
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent / "conversations.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    return conn


def init_db():
    """初始化数据库表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 创建对话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        """)

        # 创建知识库文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                upload_time TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                chunk_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        logger.info("数据库初始化成功")

    except sqlite3.Error as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        conn.close()


# ============ 对话操作 ============

def create_conversation(title: str = "新对话") -> int:
    """创建新对话，返回对话 ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title,)
        )
        conn.commit()

        conversation_id = cursor.lastrowid
        logger.info(f"创建对话: ID={conversation_id}, title={title}")
        return conversation_id

    except sqlite3.Error as e:
        logger.error(f"创建对话失败: {e}")
        raise
    finally:
        conn.close()


def get_conversation(conversation_id: int) -> Dict[str, Any]:
    """获取对话详情 用于检查对话是否存在"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    except sqlite3.Error as e:
        logger.error(f"获取对话失败: {e}")
        raise
    finally:
        conn.close()


def list_conversations(limit: int = 50) -> List[Dict[str, Any]]:
    """获取对话列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"获取对话列表失败: {e}")
        raise
    finally:
        conn.close()


def update_conversation_title(conversation_id: int, title: str):
    """更新对话标题"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()

        logger.info(f"更新对话标题: ID={conversation_id}, title={title}")

    except sqlite3.Error as e:
        logger.error(f"更新对话标题失败: {e}")
        raise
    finally:
        conn.close()


def delete_conversation(conversation_id: int):
    """删除对话（及其所有消息）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 先删除消息
        cursor.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )

        # 再删除对话
        cursor.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,)
        )

        conn.commit()
        logger.info(f"删除对话: ID={conversation_id}")

    except sqlite3.Error as e:
        logger.error(f"删除对话失败: {e}")
        raise
    finally:
        conn.close()


def delete_all_conversations():
    """删除所有对话和消息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 先删除所有消息
        cursor.execute("DELETE FROM messages")

        # 再删除所有对话
        cursor.execute("DELETE FROM conversations")

        conn.commit()
        deleted_count = cursor.rowcount
        logger.info(f"已删除所有对话数据")

        return deleted_count

    except sqlite3.Error as e:
        logger.error(f"删除所有对话失败: {e}")
        raise
    finally:
        conn.close()


# ============ 消息操作 ============

def add_message(conversation_id: int, role: str, content: str) -> int:
    """添加消息，返回消息 ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        conn.commit()

        message_id = cursor.lastrowid
        logger.info(f"添加消息: conversation_id={conversation_id}, role={role}")
        return message_id

    except sqlite3.Error as e:
        logger.error(f"添加消息失败: {e}")
        raise
    finally:
        conn.close()


def get_messages(conversation_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """获取对话的所有消息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT * FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (conversation_id, limit)
        )
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"获取消息失败: {e}")
        raise
    finally:
        conn.close()


def get_message_count(conversation_id: int) -> int:
    """获取对话的消息数量"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        count = cursor.fetchone()[0]
        return count

    except sqlite3.Error as e:
        logger.error(f"获取消息数量失败: {e}")
        return 0
    finally:
        conn.close()


# 初始化数据库（当模块被导入时）
init_db()


# ============ 知识库文档操作 ============

def create_knowledge_document(
    filename: str,
    original_name: str,
    file_type: str,
    file_size: int
) -> int:
    """创建知识库文档记录，返回文档 ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """INSERT INTO knowledge_documents (filename, original_name, file_type, file_size, upload_time)
               VALUES (?, ?, ?, ?, ?)""",
            (filename, original_name, file_type, file_size, upload_time)
        )
        conn.commit()

        doc_id = cursor.lastrowid
        logger.info(f"创建知识库文档: ID={doc_id}, filename={filename}")
        return doc_id

    except sqlite3.Error as e:
        logger.error(f"创建知识库文档失败: {e}")
        raise
    finally:
        conn.close()


def list_knowledge_documents() -> list[dict]:
    """获取所有活跃的知识库文档"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT * FROM knowledge_documents
               WHERE status = 'active'
               ORDER BY upload_time DESC"""
        )
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"获取知识库文档列表失败: {e}")
        raise
    finally:
        conn.close()


def get_knowledge_document(doc_id: int) -> dict | None:
    """获取单个知识库文档"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM knowledge_documents WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    except sqlite3.Error as e:
        logger.error(f"获取知识库文档失败: {e}")
        raise
    finally:
        conn.close()


def get_document_by_filename(filename: str) -> dict | None:
    """根据文件名获取文档"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM knowledge_documents WHERE filename = ? AND status = 'active'",
            (filename,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    except sqlite3.Error as e:
        logger.error(f"根据文件名获取文档失败: {e}")
        raise
    finally:
        conn.close()


def delete_knowledge_document(doc_id: int) -> bool:
    """删除知识库文档（软删除，设置 status='deleted'）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE knowledge_documents SET status = 'deleted' WHERE id = ?",
            (doc_id,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"删除知识库文档: ID={doc_id}")
            return True
        return False

    except sqlite3.Error as e:
        logger.error(f"删除知识库文档失败: {e}")
        raise
    finally:
        conn.close()
