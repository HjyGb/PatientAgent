<p align="center">
  <h1 align="center">PatientAgent</h1>
  <p align="center">基于 LLM 多智能体协同进化的标准化病人模拟系统</p>
</p>

<p align="center">
  <a href="https://github.com/HjyGb/PatientAgent"><img src="https://img.shields.io/badge/GitHub-Repository-2D8CFF.svg?logo=github" alt="GitHub"></a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-green.svg" alt="Python">
</p>

---

## 项目简介

PatientAgent 是一个基于大语言模型的多智能体医疗问诊模拟系统。系统通过 LLM 分别扮演**患者**和**医生**，自动进行真实的医患对话，用于医学教育培训、诊断能力评估等场景。

### 核心特性

- **多智能体架构**：患者 Agent 根据病历和角色档案生成自然语言回答；医生 Agent 动态提问并做出诊断
- **智能体协同进化**：高质量 Q&A 自动存入进化库，通过向量检索实现 few-shot 学习，Agent 越用越好
- **RAG 检索增强**：基于 FAISS 向量数据库的病历信息检索，支持 BM25+向量混合检索
- **专科医生招募**：主诊医生可动态招募专科医生协作诊断
- **交互模式**：支持人类扮演医生与 AI 患者实时对话
- **LLM 质量评估**：多维度自动评估患者回答和医生提问质量

### 基于论文

本项目基于 ACL 2025 论文 *"LLMs Can Simulate Standardized Patients via Agent Coevolution"* (arXiv:2412.11716) 的参考实现进行二次开发，在原有多智能体架构的基础上进行了以下改进：

- 升级至 LangChain 1.x 生态，修复所有兼容性问题
- 实现 LLM 驱动的真实质量评估模块（替代原 stub）
- 扩展患者角色池至 101 个多样化画像
- 新增 10 个跨科室仿真病例
- 增加交互式问诊模式
- 完善工程化配置（.env 模板、.gitignore、项目文档）

---

## 系统架构

```
┌──────────────────────────────────────────────────┐
│                  simulateflow.py                  │
│              (核心模拟流程编排)                     │
├──────────────────┬───────────────────────────────┤
│   Patient Agent  │       Doctor Agent             │
│   - 角色档案     │       - 诊断提问                │
│   - RAG 检索     │       - 专科招募                │
│   - 进化检索     │       - 对话总结                │
│   - 危机模拟     │       - 结论生成                │
├──────────────────┴───────────────────────────────┤
│                   共享基础设施                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ RAG 系统  │  │ Agent    │  │ 质量评估模块    │  │
│  │ FAISS +   │  │ Evolve   │  │ Relevance etc. │  │
│  │ BM25      │  │ CSV 存储  │  │ 6 维度评分     │  │
│  └──────────┘  └──────────┘  └────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.10+
- OpenAI 兼容 API（阿里百炼 / DeepSeek / 智谱 / OpenAI 等）

### 安装

```bash
git clone https://github.com/HjyGb/PatientAgent.git
cd PatientAgent

pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型名称
```

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | API Key（必填） |
| `BASE_URL` | API 端点 |
| `LLM_MODEL` | 主力对话模型 |
| `LLM_LITE_MODEL` | 轻量模型（评估/检测） |
| `EMBEDDING_MODEL` | 向量模型 |

### 运行

```bash
# 交互模式 — 你扮演医生
python interactive.py

# 批量自动运行
python run.py

# 构建覆盖池
python cover.py
```

---

## 项目结构

```
PatientAgent/
├── simulateflow.py                # 核心模拟流程
├── run.py                         # 批量运行入口
├── interactive.py                 # 交互式问诊
├── cover.py                       # 覆盖池构建
├── utils.py                       # 工具函数
├── Simulated/
│   ├── Prompt/prompt_data.json    # LLM Prompt 模板
│   └── simulated_patient/
│       ├── patient_agent.py       # 患者 Agent
│       ├── doctor_agent.py        # 医生 Agent
│       ├── doctor_recruit.py      # 专科招募
│       ├── agent_evolve.py        # 协同进化
│       ├── vagueness.py           # 信息模糊化
│       └── api_call.py            # LLM API 封装
├── RAG/
│   ├── rag.py                     # RAG 检索入口
│   ├── fusion_retrieval.py        # 混合检索
│   └── helper_functions.py        # 工具函数
├── dataset/
│   ├── patient_text.xlsx          # 患者数据集
│   └── Prompt_store/              # 子系统 Prompt
├── profile/profile_pool/          # 患者角色池 (101个)
├── make_task/                     # 评估模块 + Token 统计
└── docs/agents/                   # Agent 技能配置
```

---

## 评估维度

### 患者回答质量

| 维度 | 说明 |
|------|------|
| 相关性 | 是否直接回答了医生的问题 |
| 忠实性 | 是否基于病历信息，未编造症状 |
| 鲁棒性 | 是否像真实患者，未泄露专业诊断 |

### 医生提问质量

| 维度 | 说明 |
|------|------|
| 特异性 | 问题是否精准、明确 |
| 针对性 | 是否高效推进诊断 |
| 专业性 | 是否体现临床专业水平 |

---

## 致谢

本项目基于浙江大学 ZJUMAI 团队发表于 ACL 2025 的论文 [LLMs Can Simulate Standardized Patients via Agent Coevolution](https://arxiv.org/abs/2412.11716) 的开源实现进行二次开发。

## 许可证

Apache 2.0 License
