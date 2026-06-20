# 向量检索系统

PatientAgent 使用两级独立向量检索，分别服务于**知识获取（RAG）**和**风格学习（Agent Coevolution）**。

---

## 目录

- [总体架构](#总体架构)
- [第一级：RAG 病历检索](#第一级rag-病历检索)
- [第二级：Evolution 进化检索](#第二级evolution-进化检索)
- [混合检索（独立 Demo）](#混合检索独立-demo)
- [向量模型](#向量模型)
- [存储位置](#存储位置)
- [关键参数速查](#关键参数速查)

---

## 总体架构

```
  医生提问: "您发烧几天了？"
  │
  ├── ▶ RAG (FAISS 稠密检索)
  │     文件: core/rag/rag.py
  │     返回: 病历中最相关的 2 个文本块
  │     作用: 告诉 AI "病情档案里写了什么"（事实约束）
  │
  └── ▶ Evolution (CSV 余弦全量比对)
  │     文件: core/agent_evolve.py
  │     返回: 历史上最相似的 1-2 条高质量问答
  │     作用: 告诉 AI "以前好的回答是怎么说的"（风格模仿）
  │
  ▼ 合并注入 Prompt:
  ┌────────────────────────────────────────────┐
  │ System: 你是一个没有医学知识的患者...        │
  │ Profile: 35岁女性，性格温和...               │
  │                                             │
  │ Medical Info (RAG):                         │
  │   5天前出现发热，体温最高39.2℃...            │
  │                                             │
  │ Example (Evolution):                        │
  │   类似提问1: "您发烧几天了？"                │
  │   类似回答1: "烧了好几天了..."               │
  │                                             │
  │ Current Question: 您发烧几天了？             │
  └────────────────────────────────────────────┘
  │
  ▼ LLM 生成
  "哎呀大夫，烧了有四五天了吧，一直三十八九度的样子..."
```

---

## 第一级：RAG 病历检索

### 文件位置

- `core/rag/rag.py` — 主入口 `rag_patient()`
- `core/rag/helper_functions.py` — `BailianEmbeddings`、`FAISS`、文本分块工具

### 检索流程

```
完整病历文本 (~2000字)
  │
  ├─ RecursiveCharacterTextSplitter
  │   chunk_size   = 120 字符
  │   chunk_overlap = 40 字符
  │   → 切出约 20 个文本块
  │
  ├─ BailianEmbeddings.encode()
  │   → 每块 → 1024维向量
  │   → FAISS.from_documents()
  │   → 内存索引（SHA256 缓存键）
  │
  └─ 医生提问 → embed_query()
       → FAISS.similarity_search(query, k=2)
       → 返回 top-2 最相似病历片段
```

### 策略：纯稠密向量检索

| 参数 | 值 | 说明 |
|------|-----|------|
| 分块大小 | 120 字符 | 小切片，精确匹配症状细节 |
| 重叠大小 | 40 字符 | 33% 重叠，避免关键信息被切在边界 |
| Top-K | 2 | 只取最相关 2 块，保持上下文精简 |
| 相似度算法 | L2 欧氏距离 | FAISS 默认，稠密语义匹配 |
| 距离 → 相似度 | 距离越小越相关 | 同义词自动关联（"发烧"↔"发热"） |

### 缓存机制

```python
# core/rag/rag.py
_VECTOR_STORE_CACHE: dict[str, FAISS] = {}

def _make_cache_key(resource, chunk_size, chunk_overlap):
    return hashlib.sha256(
        f"{resource}|{chunk_size}|{chunk_overlap}".encode()
    ).hexdigest()
```

- **Key**: 病历内容 + 分块参数的 SHA256 哈希
- **生命周期**: 整个会话期间有效（同一份病历被多次查询）
- **收益**: 避免重复 embedding，每轮节省约 2.3 秒（CPU 模式）
- **清理**: `clear_vector_cache()` — 会话间调用

### 为什么不用 BM25 混合？

`RAG/fusion_retrieval.py` 中的 BM25+FAISS 混合策略是独立的 demo，主流程只用纯稠密检索。原因：

1. 病历文本较短（~2000 字），稠密语义匹配已足够覆盖
2. BM25 词汇匹配在短文本场景增益小
3. 减少系统复杂度和维护成本

---

## 第二级：Evolution 进化检索

### 文件位置

- `core/agent_evolve.py` — 全部进化逻辑

### 存入流程（进化写入）

```
每次高质量问答 (患者回答评分 ≥ 3)
  │
  ├─ get_text_embedding(question) → 1024维向量
  │
  ├─ 遍历 CSV 中已有向量
  │   cos_sim(new_vec, stored_vec)
  │   │
  │   └─ > 0.95 → 跳过写入（去重）
  │       ≤ 0.95 → 追加到 CSV：
  │         qus_embedding | question | rag_info | answer | requirements
  │
  └─ 同时 LLM 提取动态要求 (requirements)
       → 存入 CSV 供后续 Few-Shot 时使用
```

### 检索流程（Few-Shot 召回）

```
当前医生提问
  │
  ├─ embed(question) → 1024维向量 v_new
  │
  ├─ 遍历 CSV 中所有行:
  │   for each row:
  │     v_stored = parse(row["qus_embedding"])
  │     sim = cosine_similarity(v_new, v_stored)
  │     if sim > threshold:
  │       rank[row] = sim
  │
  ├─ 按 sim 降序排列
  │
  └─ 取 top-1~2 条 → 作为 Few-Shot 示例注入 Prompt
```

### 策略：全量余弦相似度遍历

| 参数 | Patient | Doctor | 说明 |
|------|---------|--------|------|
| 检索阈值 | > 0.9 | > 0.25 | Patient 极严格（避免错误示例污染），Doctor 宽松（鼓励多样性） |
| Top-K | 1~2 条 | 1~2 条 | ≥2 条取 top-2，1-2 条取 top-1，0 条返回空 |
| 去重阈值 | > 0.95 | > 0.8 (两对) | 存入时检查，防止重复累积 |
| 相似度算法 | 余弦相似度 | 余弦相似度 | 对文本长度不敏感，适合问答语义比较 |

### 余弦相似度公式

```python
# core/agent_evolve.py
def get_cosine_similarity(embedding_i, embedding_j):
    embedding_i = np.array(embedding_i)
    embedding_j = np.array(embedding_j)
    denom = np.linalg.norm(embedding_i) * np.linalg.norm(embedding_j)
    if denom == 0:
        return 0.0
    return embedding_i.dot(embedding_j) / denom
```

### Patient vs Doctor 阈值差异原因

```
Patient 阈值 0.9 (极高):
  ─ 患者回答质量直接影响用户体验
  ─ 一个不匹配的示例可能导致"幻觉回答"
  ─ 宁可少召回（甚至不召回），也绝不能召回错误示例

Doctor 阈值 0.25 (极低):
  ─ 医生提问鼓励多样性，不同角度的诊断思路都有价值
  ─ 低阈值 → 更多样化的 Few-Shot 示例
  ─ 两对问答联合判断 (>0.8) → 双重校验防偏
```

---

## 混合检索（独立 Demo）

### 文件位置

`RAG/fusion_retrieval.py`

### 策略：BM25 + FAISS 加权融合

```
                    ┌──────────────┐
   query ──────────┤ BM25 关键字匹配 ├──→ bm25_scores
                    └──────────────┘
                    ┌──────────────┐
   query ──────────┤ FAISS 向量检索 ├──→ vector_scores
                    └──────────────┘
                            │
                    ┌───────▼────────┐
                    │  Min-Max 归一化  │
                    │  combined =     │
                    │    α · vec      │
                    │  + (1-α) · bm25 │
                    │  α = 0.5        │
                    └───────┬────────┘
                            ▼
                      top-k 结果
```

### 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| α (向量权重) | 0.5 | 语义和关键词各占一半 |
| 1-α (BM25 权重) | 0.5 | 同上 |
| 归一化 | Min-Max | 将两组分数缩放到 [0, 1] 区间 |
| 距离转换 | 1.0 - normalized_dist | FAISS L2 → 相似度分数 |

### 状态

⚠️ **当前未接入主流程**。`fusion_retrieval()` 仅在 `run_demo()` 中被调用，不作为 `rag_patient()` 的检索策略。如需启用，可将 `rag_patient()` 中的 FAISS 调用替换为 `fusion_retrieval()`。

---

## 向量模型

### BailianEmbeddings（LangChain 包装器）

```python
# core/rag/helper_functions.py
class BailianEmbeddings(Embeddings):
    """嵌入包装器：本地 BGE-large-zh 或远程 API"""
```

| 属性 | 值 |
|------|-----|
| 本地模型 | `BAAI/bge-large-zh-v1.5` |
| 本地维度 | 1024 |
| 远程模型 | 由环境变量 `EMBEDDING_MODEL` 指定 |
| 加载方式 | 懒加载（首次调用时初始化，全局单例） |
| 切换方式 | 设置 `EMBEDDING_MODEL=local` 使用本地，否则使用远程 API |

### API 嵌入（`core/api_call.py`）

```python
def get_text_embedding(text: str, model=None) -> list:
    """获取文本嵌入向量，用于 Evolution 中的 Q&A 编码"""
```

- 与 `BailianEmbeddings` 共享同一份模型配置
- 进化库的 Q&A 向量同样来源此函数

---

## 存储位置

| 数据 | 存储位置 | 格式 | 生命周期 |
|------|----------|------|----------|
| RAG FAISS 索引 | **内存** `_VECTOR_STORE_CACHE` (Python dict) | FAISS Index 对象 | 单次会话 |
| patient_evolve.csv | `dataset/patient_evolve.csv` | CSV: `qus_embedding, question, rag_info, answer, requirements` | 永久累积 |
| doctor_evolve_{科室}.csv | `dataset/doctor_evolve_*.csv` | CSV: `question1, qus_embedding, rag_info1, answer1, qus2_embedding, question2, answer2, rag_info2` | 永久累积 |
| pool.csv | `dataset/pool.csv` | 主诉向量池（由 `cover.py` 生成） | 按需重建 |

### 文件大小参考

```
dataset/
├── patient_evolve.csv          760 KB  (患者进化库)
├── doctor_evolve_耳鼻喉科.csv   228 KB
├── doctor_evolve_呼吸内科.csv   229 KB
├── doctor_evolve_Otolaryngology.csv  319 KB
├── doctor_evolve_Internal Medicine.csv   86 B  (空/极少数据)
├── doctor_evolve_Respiratory Medicine.csv  86 B
├── doctor_evolve_Triage.csv     86 B
├── patient_text.xlsx            14 KB  (原始病例)
└── pool.csv                     (由 cover.py 按需生成)
```

---

## 关键参数速查

### RAG (`core/rag/rag.py`)

```
chunk_size        = 120       # 文本分块大小（字符数）
chunk_overlap     = 40        # 块间重叠（字符数）
top_k             = 2         # 返回最相似块数
retriever_type    = FAISS     # 检索器类型
distance_metric   = L2        # FAISS 距离度量
cache_key         = SHA256    # 缓存键哈希算法
```

### Evolution (`core/agent_evolve.py`)

```
patient_threshold   = 0.9     # 患者检索的最小余弦相似度
doctor_threshold    = 0.25    # 医生检索的最小余弦相似度
patient_dedup       = 0.95    # 患者去重阈值
doctor_dedup        = 0.8     # 医生去重阈值（两对联合判断）
top_k               = 1-2     # Few-Shot 示例数量
similarity_metric   = cosine  # 相似度算法
```

### Fusion (`RAG/fusion_retrieval.py`)

```
alpha               = 0.5     # 向量分数权重 (1-α 为 BM25 权重)
normalization       = min-max # 分数归一化方法
distance_to_score   = 1.0 - dist_norm  # 距离 → 相似度转换
```

---

## 代码调用链

```
Patient.patient_ans()
  ├── rag_patient(question, resource, size=120, overlap=40, top_k=2)
  │     └── encode_from_string() → FAISS.from_documents() [首次]
  │     └── vectorstore.as_retriever(k=2) [每次]
  │           └── retrieve_context_per_question()
  │
  └── agent_evolving_patient(csv_path, question)
        ├── get_text_embedding(question)            # 计算查询向量
        ├── read_qus_embedding_from_csv()           # 读取全部已有向量
        ├── get_cosine_similarity() × N             # 全量比对
        ├── get_most_related_qus()                  # 排序取 top-k
        └── get_evolve_info()                       # 读取完整行数据
```

---

## 设计原则

1. **两级解耦** — RAG 和 Evolution 独立运行，互不依赖。任意一级失败不影响另一级
2. **严格去重** — 进化库通过余弦阈值 >0.95 去重，防止重复数据膨胀
3. **内存缓存** — RAG 索引缓存在内存中，同一次会话不重复构建
4. **懒加载** — 本地 embedding 模型只在首次调用时加载，全局单例共享
5. **渐进增强** — Evolution 库为空时不报错，返回空示例，系统降级为纯 RAG 模式
6. **阈值差异化** — Patient 和 Doctor 使用不同检索/去重阈值，匹配各自场景特点
