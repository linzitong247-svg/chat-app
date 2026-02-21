# DeepSeek 聊天应用

基于 DeepSeek API 的智能聊天应用，支持多轮对话和 RAG 知识库功能。

---

## 功能特性

### 🎯 核心功能
- **多轮对话**：支持连续对话，自动维护上下文
- **RAG 知识库**：基于公司文档的智能问答
- **对话历史**：自动保存和查看历史记录
- **现代界面**：基于 Vue 3 + Element Plus 的美观界面

### 📚 知识库支持
- 支持上传 TXT 文档
- 自动切分和向量化
- 智能检索相关内容
- 集成到对话流程中

---

## 快速开始

### 1. 环境准备

#### 后端依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 前端依赖
```bash
cd frontend
npm install
```

### 2. 配置 API Key

创建 `.env` 文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
DEEPSEEK_API_KEY=your-api-key-here
```

### 3. 启动服务

#### 方式1：分别启动
```bash
# 启动后端
 后端（带自动重载）：
  cd D:\claude_project\chat-app\backend
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 启动前端
  cd D:\claude_project\chat-app\frontend
  npm run dev

 # 这样两边修改代码都会自动刷新，不用手动重启。
```

#### 方式2：使用 Docker
```bash
docker-compose up -d
```

### 4. 访问地址

- **前端界面**：http://localhost:3000
- **后端 API**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs

---

## 项目结构

```
chat-app/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI 主程序
│   ├── models.py           # 数据模型
│   ├── database.py         # 数据库操作
│   ├── services/           # 业务逻辑
│   │   ├── conversation.py      # 对话管理（生产级）
│   │   ├── chain_builder.py    # LangChain 链构建（LCEL）
│   │   ├── chat_history.py      # SQLite 历史适配器
│   │   └── rag_service.py      # RAG 服务
│   ├── data/               # 知识库文档
│   │   ├── company_policy.txt
│   │   └── product_info.txt
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # 组件
│   │   │   ├── Chat.vue    # 聊天界面
│   │   │   └── History.vue # 历史记录
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 入口文件
│   ├── index.html          # HTML 模板
│   ├── package.json        # Node 依赖
│   └── vite.config.js      # Vite 配置
└── README.md              # 项目说明
```

---

## API 接口

### 对话管理
- `POST /api/conversations` - 创建新对话
- `GET /api/conversations` - 获取对话列表
- `GET /api/conversations/{id}` - 获取对话详情
- `DELETE /api/conversations/{id}` - 删除对话
- `PUT /api/conversations/{id}/title` - 更新标题

### 聊天接口
- `POST /api/chat` - 普通聊天
- `POST /api/chat/rag` - RAG 聊天
- `GET /api/rag/status` - RAG 状态

### 数据格式

#### 聊天请求
```json
{
  "conversation_id": 123,
  "message": "公司年假几天？",
  "use_knowledge": true
}
```

#### 聊天响应（RAG）
```json
{
  "conversation_id": 123,
  "response": "根据公司政策，正式员工每年享有5天年假。",
  "context_used": ["公司年假5天..."],
  "timestamp": "2024-01-01T10:00:00"
}
```

---

## 使用指南

### 1. 发起对话
1. 在左侧点击"新建对话"
2. 在输入框输入问题
3. 点击"发送"按钮
4. 等待 AI 回复

### 2. 使用知识库
- 开启"使用知识库"开关后，AI 会基于上传的文档回答
- 可以同时上传多个文档
- 系统会自动处理文档并建立索引

### 3. 管理对话
- 点击左侧对话列表切换对话
- 点击垃圾桶图标删除对话
- 对话历史自动保存

---

## 开发指南

### 后端架构
- **FastAPI**：高性能 Web 框架
- **LangChain**：AI 应用框架
  - **LCEL**（LangChain Expression Language）：管道式链构建
  - **RunnableWithMessageHistory**：自动管理对话历史
- **SQLite**：轻量级数据库
- **Chroma**：向量数据库

### 前端架构
- **Vue 3**：现代前端框架
- **Element Plus**：UI 组件库
- **Vue Router**：路由管理
- **Axios**：HTTP 客户端

### 数据流程
```
用户输入 → 前端 → FastAPI → LangChain → DeepSeek API → 返回结果
                                    ↓
                              RAG 知识库检索
                                    ↓
                              SQLiteChatMessageHistory
                              (自动管理对话历史)
```

### 核心代码示例

#### 使用 RunnableWithMessageHistory（生产级写法）
```python
# services/chain_builder.py
from langchain_core.runnables import RunnableWithMessageHistory

# 创建带历史管理的链
chain = RunnableWithMessageHistory(
    base_chain,
    lambda session_id: SQLiteChatMessageHistory(int(session_id)),
    input_messages_key="input",
    history_messages_key="chat_history",
)

# 调用 - LangChain 自动管理历史！
response = chain.invoke(
    {"input": "你好"},
    {"configurable": {"session_id": "123"}}
)
```

---

## 常见问题

### 1. CORS 错误
确保后端 CORS 配置正确，前端代理正常工作。

### 2. API Key 错误
检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确。

### 3. 向量库加载慢
文档越大，加载时间越长。可以调整 `chunk_size` 参数。

### 4. 前端连接失败
确认后端服务是否启动，端口是否正确。

---

## 学习重点

### 技术要点
1. **前后端分离**：RESTful API 设计
2. **AI 集成**：LangChain + DeepSeek API
3. **RAG 技术**：文档处理、向量化、检索
4. **对话历史管理**：使用 `RunnableWithMessageHistory` 自动管理
5. **组件化开发**：Vue 3 组件设计

### LangChain 生产级实践
- **LCEL 语法**：`prompt | llm | parser` 管道式写法
- **RunnableWithMessageHistory**：自动加载/保存对话历史
- **SQLite 适配器**：自定义 `ChatMessageHistory` 连接数据库

### 面试重点
- "为什么选择 RunnableWithMessageHistory 而不是手动管理历史？"
  - 答：自动管理历史，代码更简洁，符合 LangChain 最佳实践
- "RAG 如何提升回答准确性？"
- "如何将 SQLite 数据库适配为 LangChain 的历史管理？"
  - 答：继承 `BaseChatMessageHistory`，实现 `messages` 属性和 `add_message` 方法

---

## 扩展功能

### 待实现功能
- [ ] 文件上传界面
- [ ] 对话导出功能
- [ ] 用户认证系统
- [ ] 流式输出支持
- [ ] 多人协作功能

### 性能优化
- [ ] Redis 缓存
- [ ] 数据库分表
- [ ] 异步任务队列
- [ ] CDN 静态资源

---

## 许可证

MIT License