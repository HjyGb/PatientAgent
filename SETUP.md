# EvoPatient 环境配置与运行指南

## 快速启动

### 1. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key 和模型名称
```

### 4. 运行

```bash
# 测试单次对话（需在 simulateflow.py 底部手动调用 flow()）
python -c "from simulateflow import flow; flow()"

# 交互模式（你扮演医生）
python interactive.py

# 批量运行
python run.py
```

---

## .env 配置说明

| 变量 | 说明 |
|---|---|
| `BASE_URL` | OpenAI 兼容 API 端点 |
| `OPENAI_API_KEY` | API Key（必填） |
| `LLM_MODEL` | 主力对话模型 |
| `LLM_LITE_MODEL` | 轻量模型（评估/检测任务） |
| `EMBEDDING_MODEL` | 向量检索模型 |

支持任何 OpenAI 兼容的 API 服务（阿里百炼、DeepSeek、智谱等），只需修改 `BASE_URL` 和对应的模型名称。

---

## 代码修改记录

以下是为了兼容 langchain 1.x 所做的修改：

### 1. `RAG/helper_functions.py` — langchain 1.x 适配

| 原导入 | 新导入 |
|---|---|
| `from langchain.document_loaders import PyPDFLoader` | `from langchain_community.document_loaders import PyPDFLoader` |
| `from langchain.vectorstores import FAISS` | `from langchain_community.vectorstores import FAISS` |
| `from langchain.text_splitter import RecursiveCharacterTextSplitter` | `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| `from langchain_core.pydantic_v1 import BaseModel, Field` | `from pydantic import BaseModel, Field` |
| `from langchain import PromptTemplate` | `from langchain_core.prompts import PromptTemplate` |

### 2. `RAG/fusion_retrieval.py` — langchain 1.x 适配

| 原导入 | 新导入 |
|---|---|
| `from langchain.docstore.document import Document` | `from langchain_core.documents import Document` |

### 3. `.env` 加载顺序修复

`simulateflow.py`、`cover.py` 中 `load_dotenv()` 已移至所有 project import 之前，确保 `api_call.py` 在检查环境变量前 `.env` 已被加载。

### 4. `make_task/overall_assessment_llm.py` — 评估 stub

原始评估模块未开源，创建了返回中性分数的 stub：
- `overall_assessment_patient()` 返回 `(3, 3, 3, 3)`
- `overall_assessment_doctor()` 返回 `(3, 3, 3, 3)`
