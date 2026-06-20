# PatientAgent 项目深度分析 — 复习文档

> 生成日期：2026-06-20  
> 基于项目 `d:/Project/PatientAgent/EvoPatient/` 的完整源码分析  
> 涵盖：架构设计、数据集全链路、Agent Coevolution 机制、Doctor Agent 角色、批量模拟

---

## 目录

1. [项目概述](#1-项目概述)
2. [高层架构](#2-高层架构四层架构)
3. [核心文件结构](#3-核心文件结构)
4. [数据集详解](#4-数据集详解)
5. [Agent Coevolution（智能体共进化）](#5-agent-coevolution智能体共进化)
6. [Doctor Agent（医生智能体）](#6-doctor-agent医生智能体)
7. [批量模拟（模式一）](#7-批量模拟模式一ai-医生-vs-ai-病人)
8. [数据全链路：来源 → 用途 → 去向](#8-数据全链路来源--用途--去向)
9. [核心设计亮点速查](#9-核心设计亮点速查)

---

## 1. 项目概述

**PatientAgent** 是一个基于 LLM 的多智能体（Multi-Agent）模拟系统，用于模拟**标准化病人-医生问诊**场景。

- **论文来源**：*"LLMs Can Simulate Standardized Patients via Agent Coevolution"* (arXiv:2412.11716, ACL 2025)
- **应用场景**：医学教育训练 — 让医学生与 AI 病人进行模拟对话练习问诊能力
- **技术栈**：Python + Streamlit + OpenAI API + FAISS (向量检索) + LangChain + Sentence-Transformers
- **运行方式**：Streamlit Web UI / 命令行交互 / 批量自动化模拟

---

## 2. 高层架构（四层架构）

```
┌─────────────────────────────────────────────────────┐
│              表现层 (Presentation)                    │
│  app.py (Streamlit 4页 SPA)  │  interactive.py (CLI)│
├─────────────────────────────────────────────────────┤
│              编排层 (Orchestration)                   │
│       simulateflow.py  (init_session + flow)         │
│       run.py  (批量循环)  │  cover.py  (覆盖池)       │
├─────────────────────────────────────────────────────┤
│              智能体层 (Agent Layer)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │Patient Agent │ │Doctor Agent  │ │Doctor Recruit│ │
│  │  (患者智能体)│ │ (医生智能体) │ │ (专科招募)   │ │
│  └──────┬───────┘ └──────┬───────┘ └──────────────┘ │
│         │                │                           │
│  ┌──────┴────────────────┴───────────────────────┐  │
│  │        Agent Coevolution (智能体共进化)        │  │
│  │        agent_evolve.py — Few-Shot 检索+存储    │  │
│  └───────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│              基础设施层 (Infrastructure)              │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │api_call  │ │ RAG系统  │ │ Quality Assessment │  │
│  │(LLM客户端)│ │(FAISS)   │ │ (LLM自动评分)      │  │
│  └──────────┘ └──────────┘ └────────────────────┘  │
│  ┌──────────┐ ┌──────────┐                         │
│  │Vagueness │ │ Prompt   │                         │
│  │(信息模糊)│ │ Store    │                         │
│  └──────────┘ └──────────┘                         │
└─────────────────────────────────────────────────────┘
```

### 三种运行入口

| 入口 | 文件 | 用途 |
|------|------|------|
| **Web UI** | `app.py` | Streamlit 4 页 SPA：病例选择 → 问诊对话 → 提交诊断 → 评估报告 |
| **CLI 交互** | `interactive.py` | 命令行交互，人扮演医生打字提问，AI 扮演病人回答 |
| **批量模拟** | `run.py` | 自动化循环，遍历 Excel 中所有病例（行 2–1300），AI 医生 vs AI 病人 |

三个入口都通过 `simulateflow.init_session()` 做统一初始化。

---

## 3. 核心文件结构

```
EvoPatient/
├── app.py                          # Streamlit Web UI (核心前端，4页SPA)
├── interactive.py                  # CLI 交互入口
├── run.py                          # 批量自动化模拟 (遍历1300条病例)
├── cover.py                        # 覆盖池构建 (生成 pool.csv)
├── simulateflow.py                 # ★ 编排层: init_session() + flow()
├── utils.py                        # 工具函数 (prompt加载, **标记解析, token计数)
│
├── Simulated/simulated_patient/
│   ├── patient_agent.py            # ★ 患者智能体 — 核心组件
│   ├── doctor_agent.py             # ★ 医生智能体 — 自动问诊+子专科招募
│   ├── doctor_recruit.py           # 专科医生递归招募 (独立实现，含拓扑支持)
│   ├── agent_evolve.py             # ★ Agent共进化 — Few-Shot存储/检索
│   ├── vagueness.py                # 病历信息模糊化 (dropout + LLM)
│   └── api_call.py                 # LLM/Embedding 统一客户端
│
├── RAG/
│   ├── rag.py                      # ★ RAG检索 (FAISS + SHA256缓存)
│   ├── helper_functions.py         # BailianEmbeddings, BM25, 文本切分
│   ├── fusion_retrieval.py         # 混合检索 BM25+FAISS (未主用)
│   └── rag_pdf.py                  # PDF RAG (未主用)
│
├── make_task/
│   └── overall_assessment_llm.py   # ★ LLM自动评估 (患者回答+医生提问质量)
│
├── dataset/
│   ├── patient_text.xlsx           # ★ 核心数据源 (5个Sheet的Excel)
│   ├── patient_evolve.csv          # 患者侧进化库 (88行，持续增长)
│   ├── doctor_evolve_*.csv         # 医生侧进化库 (按科室分离)
│   ├── patient_data.json           # 汇总的患者JSON数据
│   ├── pool.csv                    # 主诉覆盖池 (cover.py生成)
│   ├── Prompt_store/               # 备用Prompt模板
│   └── bulit_dataset.py            # 数据集构建脚本
│
├── Simulated/Prompt/
│   └── prompt_data.json            # ★ 核心Prompt模板库 (20个模板)
│
├── profile/profile_pool/           # 100种患者性格画像 (0.txt ~ 99.txt)
│
├── exp1/                           # 批量实验输出目录 (时间戳子目录)
├── interactive/                    # 交互实验输出目录
└── docs/                           # 设计文档
```

---

## 4. 数据集详解

### 4.1 数据集总体结构

```
dataset/
├── patient_text.xlsx          ← ★ 核心数据源 (Excel多Sheet)
├── patient_data.json          ← 汇总的JSON格式患者数据
├── patient_evolve.csv         ← 患者侧进化库 (运行时自动积累)
├── doctor_evolve_呼吸内科.csv  ← 医生侧进化库-呼吸内科
├── doctor_evolve_耳鼻喉科.csv  ← 医生侧进化库-耳鼻喉科
├── doctor_evolve_Otolaryngology.csv ← 英文版-耳鼻喉科
├── doctor_evolve_Internal Medicine.csv / Triage.csv / Respiratory Medicine.csv
├── pool.csv                   ← 主诉覆盖池 (embedding向量)
└── Prompt_store/              ← 备用Prompt模板库
```

### 4.2 核心数据源：patient_text.xlsx

包含 **5 个独立的 Sheet**（对应医院信息系统的不同模块）：

| Sheet 名称 | 来源系统 | 内容 |
|------------|----------|------|
| `患者基本信息` | HIS (医院信息系统) | 患者编号、年龄、性别等 |
| `病程记录_首次病程` | EMR (电子病历) | **首次就诊的完整病程记录**（主数据） |
| `检查_MRI检查` | RIS (放射信息系统) | MRI 等影像检查报告 |
| `病理_全部病理` | PIS (病理信息系统) | 病理检查结果 |
| `专科检查_专科检查` | 专科系统 | 耳鼻喉等专科检查结果 |

`bulit_dataset.py` 按 **Patient-SN** 聚合这 5 个 Sheet，输出 `patient_data.json`。

### 4.3 两套数据：resource vs vague_info

| 维度 | resource (完整版) | vague_info (模糊版) |
|------|-------------------|---------------------|
| 来源 | Excel 原始值 | `vagueness.py` 处理后 |
| 风格 | 精确医学术语 | 口语化、含糊不清 |
| 用途 | 给 RAG 系统做检索源 | 给 Patient Agent 模拟病人真实记忆 |
| 示例 | "患者于2024年3月无明显诱因出现反复咳嗽…" | "大概前段时间开始咳嗽吧，也记不太清具体啥时候…" |

**模糊化流程**：
```
Excel 精确病历
    ↓ random_dropout: 随机删除 ~30% tokens (数字/日期/专业术语优先)
信息缺损版本
    ↓ LLM + vagueness prompt ("你怎么像病人那样把这句话说模糊...")
自然模糊版本 (病人视角的真实表述)
```

### 4.4 进化库数据 (Evolution Store)

**Patient Evolution CSV** (`patient_evolve.csv`)：
```
列: qus_embedding | question | rag_info | answer | requirements
     (768d向量)   (医生问题)  (检索上下文) (患者回答) (动态行为要求)
已有: 88 行高质量 Q&A 对
```

**Doctor Evolution CSV** (`doctor_evolve_{科室}.csv`)：
```
列: question1 | qus_embedding | rag_info1 | answer1 |
     qus2_embedding | question2 | answer2 | rag_info2

已有: 呼吸内科 24条 + 耳鼻喉科 22条 + 英文版 各若干条
```

这些数据**不是预置的**，而是在每次模拟运行时**自动积累**。

### 4.5 患者性格画像 (profile_pool)

- **位置**：`profile/profile_pool/{0..99}.txt`
- **数量**：99 个实际存在的文件
- **内容示例**：

  > 你是一位男性，一直以来都比较独立，喜欢自己解决问题，不太依赖他人。但目前你的家庭处于低收入状态…由于对疾病、治疗或者未来充满担忧，你时常感到焦虑不安。你接受过高中教育…

- **用途**：`Patient.generate_patient_question()` 中随机选取一个，影响患者说话风格和回答语气

---

## 5. Agent Coevolution（智能体共进化）

### 5.1 核心原理

让 AI 患者在对话中不断"学习"，高质量的历史问答对自动存档，未来作为 Few-Shot 示例检索使用，形成**自举循环**。

```
┌─────────────────── 一轮问答 ──────────────────┐
│                                                │
│  Doctor: "咳嗽持续多久了？"                     │
│      ↓                                         │
│  Patient: RAG检索病历 + Evolution检索 → 生成回答  │
│      ↓                                         │
│  LLM 评估回答质量 (0-5分)                        │
│      ↓                                         │
│  ┌─ score ≥ 3 ─────────────────────────────┐  │
│  │ 1. 提取 dynamic_requirements             │  │
│  │ 2. question → get_text_embedding()       │  │
│  │ 3. 余弦相似度去重 (阈值 > 0.95)           │  │
│  │ 4. 存入 patient_evolve.csv               │  │
│  └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘

未来某次新对话:
  Doctor 提问 "你有咳痰的症状吗？"
      ↓
  get_text_embedding(question) → 768d 向量
      ↓
  在 patient_evolve.csv 中找 top-2 最相似的历史 Q&A
      ↓
  把这些历史 Q&A 注入 Prompt 作为 Few-Shot 示例
      ↓
  Patient 参考这些示例，生成更高质量的回答
```

### 5.2 完整自举循环

```
                    ┌──────────────┐
                    │  新问答发生   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ LLM 质量评估  │
                    └──────┬───────┘
                           ↓
                    score ≥ 3 ?
                   ╱           ╲
                 否              是
                 ↓               ↓
              丢弃          ┌──────────────┐
                            │ Embedding向量化│
                            └──────┬─────────┘
                                   ↓
                            ┌──────────────────┐
                            │ 检索进化库已有条目 │
                            │ cos_sim > 0.95?  │ ← 去重
                            └──────┬───────────┘
                                   ↓
                          重复?    /   新条目?
                         丢弃     /       ↓
                               ┌────────────────┐
                               │ store_patient_qa│
                               └───────┬────────┘
                                       ↓
                               ┌────────────────────────┐
                               │ 下次对话被检索为 Few-Shot │
                               └────────┬───────────────┘
                                        ↓
                               ┌────────────────────────┐
                               │ 作为示例注入下一轮 Prompt │
                               │ → Agent 自我改进        │
                               └────────────────────────┘
```

### 5.3 两个维度的进化

| 进化维度 | Patient Side | Doctor Side |
|----------|-------------|-------------|
| **存储对象** | 单条 Q&A 对 | Q1→A1→Q2 **转移对** |
| **存储条件** | patient score ≥ 3 | doctor score ≥ 3 **且** patient score ≥ 1 |
| **去重阈值** | cos_sim > 0.95 | cos_sim(Q1) > 0.8 **且** cos_sim(Q2) > 0.8 |
| **核心思路** | 记录"这个回答好" | 记录"这个问题好 → 追问了什么" |

### 5.4 为什么起作用

| 作用 | 机制 | 效果 |
|------|------|------|
| **质量自举** | 只有高分 Q&A 才存档，低分丢弃 | 进化库越来越"精"，Few-Shot 质量越来越高 |
| **去重防止退化** | 余弦相似度 > 0.95 的条目跳过 | 避免同类示例泛滥导致模式坍塌 |
| **动态行为约束** | 每次存档时会提取 `requirements`（如"用第一人称""添加口语语气词"） | 后续回答能自动继承该问题的特定行为要求 |
| **科室专项化** | Doctor 进化库按科室分离存储 | 不同科室的医生能检索到本专业的历史最佳实践 |

---

## 6. Doctor Agent（医生智能体）

### 6.1 角色定位

Doctor Agent 在系统中扮演**双重角色**：

```
┌─────────────────────────────────────────────┐
│              Doctor Agent                    │
│                                              │
│  【模式一: AI 医生 vs AI 病人】               │
│   run.py 批量模拟: 全自动对话                 │
│                                              │
│  【模式二: 医学生 vs AI 病人】                 │
│   app.py / interactive.py: 人类扮演医生       │
│   Doctor Agent 仅提供辅助诊断建议              │
└─────────────────────────────────────────────┘
```

### 6.2 核心能力矩阵

| 方法 | 触发时机 | 功能 |
|------|---------|------|
| `doctor_qus()` | 每轮问诊 | 生成下一个问诊问题（RAG + Evolution + 子专家摘要 + 对话摘要 → LLM） |
| `conclusion()` | 信息足够后 | 生成最终诊断结论 |
| `recruit()` | 病情复杂时 | 动态招募专科医生 |
| `make_summary()` | 每 3 轮 | 压缩对话历史为结构化摘要 |
| `doctor_crisis_answer()` | 随机紧急事件 | 处理病人突发状况 |

### 6.3 doctor_qus() 完整链路

```
Doctor.doctor_qus(上一轮患者回答, 患者评分, rel, faith, human)
│
├─ 1. agent_evolving_doctor(evolve_csv, record)
│      └─ Embedding 检索历史最佳 Q1→A1→Q2 转移对作为 Few-Shot
│
├─ 2. 构造 prompt (doctor_question_info 模板)
│      └─ 填入: {科室} {主诉} {summary} {dialog_history}
│              {few_shot_example} {patient_info}
│
├─ 3. 处理子专科医生 (sub_doctor)
│      └─ 对每个 recruited 的子医生:
│           ├─ 子医生独立问诊一轮
│           ├─ patient_ans() 返回回答
│           └─ 子医生 make_summary()
│      └─ 将所有子医生的 summary 追加到主 prompt
│
├─ 4. LLM 生成下一个问题
│
├─ 5. 解析并存储
│      ├─ match_star(response, "*") → 提取 **question** 标记
│      └─ match_star(response, "#") → 提取 ##category## 标记
│
├─ 6. 质量评估
│      ├─ overall_assessment_doctor(qus, useful_info, answer)
│      └─ → (score, specificity, targetedness, professionalism)
│
├─ 7. 若 score ≥ 3 → store_doctor_qa() 存入进化库
│
├─ 8. 每 3 轮 → make_summary() 压缩历史
│
└─ 返回: next_question (或 "skip" / "conclusion")
```

### 6.4 子专科医生招募 (Recruit)

当病例复杂、跨越多个科室时，主医生可以自动招募子专科医生：

```
内科医生 (主)
    │
    ├─ recruit() → LLM判断需要 呼吸内科、心内科
    │
    ├─ 呼吸内科医生 (子)
    │   ├─ doctor_qus("气短和咳嗽的关系?")
    │   ├─ patient_ans() → 回答
    │   └─ make_summary() → "呼吸方面: 持续干咳1月, 无痰, 气短在活动后加重"
    │
    ├─ 心内科医生 (子)
    │   ├─ doctor_qus("胸痛的性质和诱因?")
    │   ├─ patient_ans() → 回答
    │   └─ make_summary() → "心脏方面: 偶有胸闷, 无心悸, 血压正常"
    │
    └─ 主医生的 prompt 中注入所有子医生 summary
       → 综合判断 → 问出更精准的问题
```

- **非递归版本** (`doctor_agent.py` 中的 `Doctor.recruit()`)：单层招募，检查文件避免重复
- **递归版本** (`doctor_recruit.py` 中的 `Recruit` 类)：支持多层拓扑（DAG/Tree/Chain），部分功能未完全整合

### 6.5 对话摘要机制

对话变长会导致 LLM context 超限，因此每 **3 轮**自动压缩：

```python
self.dialog_turn += 1
if self.dialog_turn % self.summary_trun == 0:  # 每3轮
    self.make_summary()                         # LLM压缩历史
    # self.summary = 压缩后的摘要
    # self.dialog_history = "" 清空原始对话
```

---

## 7. 批量模拟（模式一：AI 医生 vs AI 病人）

### 7.1 run.py 做什么

```python
row_number = cache()                    # 从断点文件读取上次运行到的行号
while row_number <= 1300:              # 遍历 Excel 中所有 1300 条病例
    row_number += 1
    flow(sheet_name, row_number, col_number)  # 执行一次完整模拟
    write_cache(row_number)            # 写入断点 → 支持中断恢复
```

每次调用 `flow()` 执行完整流程：
- AI 医生自动提问（RAG + Evolution 检索生成问题）
- AI 病人自动回答（RAG + Evolution + Profile 生成口语化回答）
- 最多 10 轮对话，中间随机注入一次危机事件
- 结束时 AI 医生自动生成诊断结论

### 7.2 批量模拟的核心作用

| 作用 | 说明 |
|------|------|
| **积累进化数据** | 批量运行 1300 条病例 → 大量 Q&A 对 → 筛选高质量（score≥3）存入进化库 → 进化库越丰富，后续模拟质量越高 |
| **生成训练语料** | 批量产生的对话数据可作为医学 NLP 训练/评估语料 |
| **覆盖全科室** | 覆盖 Excel 中所有科室、所有难度的病例，确保进化库的多样性 |
| **断点续传** | `case_cache.txt` 记录当前进度，中断后可无缝恢复 |

### 7.3 结果存放位置与文件说明

每次模拟在 `exp1/` 下创建一个时间戳目录：

```
exp1/
├── 1780545654.339371/          ← 一次完整模拟 (Unix 时间戳命名)
│   ├── resource.txt            ← 患者完整精确病历 (Excel原文)
│   ├── vague.txt               ← 模糊化后的患者信息
│   ├── doctor_question.txt     ← 完整医患对话记录 (纯文本)
│   ├── question_record.csv     ← ★ 结构化逐轮记录
│   ├── doctor_record/          ← 按科室分的医生评分记录
│   │   └── Otolaryngology_1.csv
│   ├── conclusion.txt          ← AI 医生的最终诊断结论
│   ├── crisis.txt              ← 随机注入的危机事件日志
│   ├── token_count/            ← 每轮 token 用量统计
│   │   ├── token_overall.txt   ← 累计总量
│   │   └── token_stream.txt    ← 逐轮明细
│   └── time_cost.txt           ← 最后一轮耗时 (秒)
│
├── 1781928266.0527635/         ← 另一次模拟
│   └── ... (同上结构)
│
└── ... (共13+个实验目录)
```

**question_record.csv 结构**：

| 列 | 含义 | 示例 |
|-----|------|------|
| `row` | Excel 行号 | `2` |
| `question` | 医生提问 | "Can you tell me more about..." |
| `answer` | 患者回答 | "嗯，那个，我右耳这个闷堵的感觉..." |
| `token_count_doctor` | 医生回合 token | `566` |
| `token_count_patient` | 患者回合 token | `672` |
| `resource` | 原始病历摘要 | "1、患者。2、缘于1年前..." |
| `doctor_time` | 医生思考耗时 | `6.7s` |
| `patient_time` | 患者回答耗时 | `16.4s` |
| `question_cnt` | 问题中文字数 | `0` (英文) |
| `answer_cnt` | 回答中文字数 | `228` |

---

## 8. 数据全链路：来源 → 用途 → 去向

### 8.1 全景数据流图

```
                        ┌── 静态数据 (预置) ──┐
                        │                     │
              ┌─────────┴────────┐  ┌─────────┴─────────┐
              │ patient_text.xlsx│  │profile/profile_pool│
              │  (5个Sheet)      │  │   (100个性格文件)  │
              └────────┬─────────┘  └─────────┬──────────┘
                       │                      │
                       ↓                      │
              ┌────────────────┐              │
              │ vagueness.py   │              │
              │ random_dropout  │              │
              │ + LLM 模糊化    │              │
              └───────┬────────┘              │
                      │                      │
          ┌───────────┴──────────┐            │
          ↓                      ↓            ↓
    resource               vague_info     profile
  (精确完整病历)         (模糊病人表述)  (患者性格画像)
          │                     │            │
          │    ┌────────────────┴────────────┘
          │    │
          ↓    ↓
   ┌──────────────────────────────────────────────┐
   │           Prompt 模板填充                       │
   │   Simulated/Prompt/prompt_data.json           │
   │   (20个模板)                                   │
   └──────────────────────┬───────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │Patient Agent│  │Doctor Agent│  │Quality Eval  │
   │ patient_ans │  │ doctor_qus │  │ assessment   │
   └──────┬──────┘  └─────┬──────┘  └──────┬───────┘
          │               │                │
          │    Q&A pair   │    score ≥ 3   │
          │               │                │
          ↓               ↓                ↓
   ┌─────────────────────────────────────────────────┐
   │          Agent Coevolution (动态积累)             │
   │                                                 │
   │  patient_evolve.csv   ← 患者侧高质量Q&A存档       │
   │  doctor_evolve_{科室}.csv ← 医生侧高质量Q&A存档    │
   │                                                 │
   │  → 下次对话时 Embedding 检索 → Few-Shot 注入      │
   └─────────────────────────────────────────────────┘
                          │
                          ↓
   ┌─────────────────────────────────────────────────┐
   │              输出层 (实验产物)                     │
   │                                                 │
   │  exp1/{timestamp}/     ← 批量模拟结果             │
   │  interactive/{timestamp}/ ← 交互模式结果          │
   │  pool.csv (cover.py)   ← 主诉覆盖池              │
   │  question_record.csv   ← 顶层便利副本             │
   └─────────────────────────────────────────────────┘
```

### 8.2 逐项数据详表

| 数据资产 | 来源 | 去向/用途 |
|----------|------|----------|
| **patient_text.xlsx** | 医院病历(预置, 5 Sheet) | → `resource` (RAG检索源) → `vague_info` (模糊化) → `patient_data.json` → Streamlit UI 病例卡片 |
| **profile_pool/*.txt** | 预置人设(99个) | → Patient 主诉生成 → Patient 回答风格控制 |
| **prompt_data.json** | 手工设计(20模板) | → 所有 Agent 的 Prompt 构造 |
| **patient_evolve.csv** | 运行时自动生成 (score≥3) | → Few-Shot 注入 Patient Prompt → 持续积累，质量自举 |
| **doctor_evolve_*.csv** | 运行时自动生成 (双重条件) | → Few-Shot 注入 Doctor Prompt → 按科室隔离进化 |
| **pool.csv** | cover.py 批量生成 | → 主诉覆盖检索池 |
| **exp1/{ts}/* 和 interactive/{ts}/* ** | run.py / interactive.py | → 实验记录 / 分析 / 论文数据 |
| **case_cache.txt** | run.py / cover.py 写入 | → 断点续传，避免重复运行 |

---

## 9. 核心设计亮点速查

| 亮点 | 说明 |
|------|------|
| **Agent Coevolution** | 高质量 Q&A 自动存入进化库，通过 Embedding 相似度检索做 Few-Shot，Agent 随时间自我改进 |
| **Vagueness 模糊化** | 不是简单用原始病历，而是通过 dropout + LLM 转成病人真实口吻的模糊表述 |
| **RAG + FAISS 缓存** | 每个会话内 Embedding 只算一次，SHA256 hash 命中直接复用 |
| **多科室专科招募** | Doctor Agent 可动态招募子专科医生（递归拓扑），模拟多学科会诊 |
| **四维质量评估** | 每轮回答自动 LLM 评分 (相关性/忠实度/拟人度/综合)，高分存档进化 |
| **危机事件注入** | 随机回合注入医疗紧急情况，测试医生的应急能力 |
| **对话摘要压缩** | 每 3 轮 LLM 压缩一次对话历史，防止 context 超限 |
| **兼容 OpenAI/国产 API** | 统一 `api_call` 客户端，通过 `BASE_URL` 环境变量适配百炼/DashScope 等 |
| **本地 Embedding 支持** | 支持 BGE-large-zh 本地模型做 embedding (免费 + GPU 加速) |
| **断点续传** | `case_cache.txt` 记录批量模拟进度，中断可恢复 |

---

> **核心理念总结**：整个系统分为**静态层**（预置的 Excel 病历、Profile、Prompt 模板）提供基础素材，**动态层**（evolution CSV）在运行时从高质量对话中自动生长，并反过来通过 Few-Shot 检索提升后续对话质量。这个"**运行即训练**"的闭环正是 Agent Coevolution 的核心机制。
