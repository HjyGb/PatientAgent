<p align="center">
  <h1 align="center">PatientAgent 2.0</h1>
  <p align="center">基于 LLM 多智能体协同进化的标准化病人模拟问诊平台<br/>
  面向医学生临床教学 · 毕业设计 · 真实医院落地</p>
</p>

<p align="center">
  <a href="https://github.com/HjyGb/PatientAgent"><img src="https://img.shields.io/badge/GitHub-Repository-2D8CFF.svg?logo=github" alt="GitHub"></a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/React-19-61DAFB.svg?logo=react" alt="React">
</p>

---

## 项目简介

PatientAgent 是一个基于大语言模型的多智能体医疗问诊模拟系统。2.0 版本在原始研究代码之上构建了完整的 **Web 教学平台**：React 前端 + FastAPI 后端 + 流式对话 + AI 诊断评估，可直接用于医学生临床教学。

```
医学生 (Web 浏览器)
    │  SSE 流式对话
    ▼
┌─────────────────────────────────────────┐
│  React 19 SPA                           │
│  4 列 Grid：历史 | 聊天 | 病历 | 评估     │
└──────────────┬──────────────────────────┘
               │  REST + SSE (JWT)
               ▼
┌─────────────────────────────────────────┐
│  FastAPI Server                         │
│  会话管理 · 消息持久化 · 评估引擎         │
└──────────────┬──────────────────────────┘
               │  Python 调用
               ▼
┌─────────────────────────────────────────┐
│  core/ AI Agent 引擎                    │
│  Patient · Doctor · RAG · Evolution      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  SQLite DB  ·  FAISS 向量库  ·  Excel   │
└─────────────────────────────────────────┘
```

### 核心特性

**教学平台（2.0 新增）**
- **流式对话**：SSE token-by-token 渲染，真实问诊体验
- **AI 诊断评估**：4 维评估引擎 + 教师评语 + 标准诊断参考
- **用户隔离**：6 位工号免密登录，每人独立会话历史
- **数据库持久化**：会话、消息、评估全量落盘，可回看
- **移动端适配**：响应式布局（进行中）

**AI 引擎（继承自 1.0）**
- **多智能体架构**：患者 Agent 根据病历和角色档案生成自然语言回答；医生 Agent 动态提问并做出诊断
- **智能体协同进化**：高质量 Q&A 自动存入进化库，通过向量检索实现 few-shot 学习，越用越准
- **RAG 检索增强**：FAISS 稠密向量检索 + BM25 混合检索
- **专科医生招募**：主诊医生可动态招募专科医生协作诊断
- **LLM 质量评估**：多维度自动评估患者回答和医生提问质量

### 基于论文

本项目基于 ACL 2025 论文 *"LLMs Can Simulate Standardized Patients via Agent Coevolution"* (arXiv:2412.11716) 的开源实现进行二次开发。

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+
- OpenAI 兼容 API（阿里百炼 / DeepSeek / 智谱 / OpenAI 等）

### 1. 安装

```bash
git clone https://github.com/HjyGb/PatientAgent.git
cd PatientAgent

# Python 依赖
pip install -r EvoPatient/requirements.txt

# 前端依赖
cd patient-agent-ui && npm install && cd ..
```

### 2. 配置

```bash
cp EvoPatient/.env.example EvoPatient/.env
# 编辑 .env，填入 API Key 和模型名称
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key | **必填** |
| `BASE_URL` | API 端点 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 主力对话模型 | **必填** |
| `LLM_LITE_MODEL` | 轻量模型 | **必填** |
| `EMBEDDING_MODEL` | 向量模型 | `text-embedding-ada-002` |

### 3. 启动

```bash
# 终端 1：后端
cd EvoPatient
uvicorn server.main:app --reload --port 8000

# 终端 2：前端
cd patient-agent-ui
npm run dev
```

浏览器打开 `http://localhost:5173`，输入工号 `000000`，选择科室和病例即可开始问诊。

### 4. 测试

```bash
cd EvoPatient
python test_e2e.py    # 全自动端到端测试（无需医学知识）
```

---

## 项目结构

```
PatientAgent/
│
├── EvoPatient/                         # 后端 (Python FastAPI)
│   ├── core/                           # 共享 AI Agent 包
│   │   ├── patient_agent.py            #   患者 Agent + 流式方法
│   │   ├── doctor_agent.py             #   医生 Agent + 诊断生成
│   │   ├── agent_evolve.py             #   智能体协同进化
│   │   ├── api_call.py                 #   LLM API + Embedding + 流式
│   │   ├── vagueness.py                #   信息模糊化
│   │   └── rag/                        #   FAISS/BGE 稠密检索
│   ├── server/                         # FastAPI 服务层
│   │   ├── main.py                     #   应用入口 + 生命周期
│   │   ├── config.py                   #   环境配置
│   │   ├── dependencies.py             #   DB引擎 + JWT认证
│   │   ├── models/                     #   SQLAlchemy ORM (4表)
│   │   ├── schemas/                    #   Pydantic v2 接口定义
│   │   ├── routers/                    #   auth / cases / sessions / evaluations
│   │   └── services/                   #   业务逻辑编排
│   ├── dataset/
│   │   └── patient_text.xlsx           #   10 个跨科室仿真病例
│   ├── docs/                           #   项目文档
│   ├── test_e2e.py                     #   端到端测试
│   └── interactive.py                  #   命令行交互模式
│
├── patient-agent-ui/                   # 前端 (React + TypeScript)
│   └── src/
│       ├── pages/
│       │   ├── InitPage.tsx            #   工号 + 病例选择
│       │   └── InterviewPage.tsx       #   4 列 Grid 问诊主页面
│       ├── components/
│       │   ├── interview/              #   LeftSidebar / ChatPanel / MedicalForm / EvaluatePanel
│       │   ├── evaluation/             #   EvaluateModal (完整评估弹窗)
│       │   └── ui/                     #   ToastContainer
│       ├── stores/                     #   Zustand: auth / case / chat / record / toast
│       └── lib/api-client.ts           #   API 封装 + JWT 附件
│
├── docs/                               # 项目文档
│   ├── project-status.md               #   进度总览
│   └── vector-retrieval.md             #   向量检索系统说明
│
├── Simulated/                          # 原始研究代码 (保留)
│   └── simulated_patient/
│       ├── patient_agent.py
│       ├── doctor_agent.py
│       ├── agent_evolve.py
│       └── ...
│
├── RAG/                                # 原始 RAG 模块 (保留)
├── dataset/                            # 原始数据集 (保留)
├── run.py                              # 批量自动运行
├── cover.py                            # 覆盖池构建
└── README.md
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/quick-login` | 免密登录（6位工号） |
| GET | `/api/v1/cases` | 病例列表（分页/筛选） |
| POST | `/api/v1/cases/{id}/load` | 加载病例 → 创建会话 |
| POST | `/api/v1/sessions/{id}/messages` | 发送问题（阻塞版） |
| GET | `/api/v1/sessions/{id}/messages/stream?question=` | SSE 流式问答 |
| POST | `/api/v1/sessions/{id}/diagnosis` | 提交诊断 |
| GET | `/api/v1/sessions/{id}/evaluation` | 获取评估报告 |
| GET | `/api/v1/sessions/history` | 历史会话列表 |
| GET | `/api/v1/departments` | 科室列表 |

启动后端后访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

---

## 评估维度

### AI 引擎：患者回答质量

| 维度 | 说明 |
|------|------|
| 相关性 | 是否直接回答了医生的问题 |
| 忠实性 | 是否基于病历信息，未编造症状 |
| 鲁棒性 | 是否像真实患者，未泄露专业诊断 |

### 教学评估：学生诊断质量

| 维度 | 说明 |
|------|------|
| 诊断正确性 | 是否接近标准答案 |
| 依据充分性 | 证据是否支撑诊断结论 |
| 鉴别诊断合理性 | 鉴别疾病列举是否合理 |
| 检查建议合理性 | 建议检查是否必要且充分 |

综合评分 = 问诊质量 × 0.4 + 诊断准确性 × 0.6

---

## 开发路线

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 基础设施重构 (FastAPI + DB) | ✅ |
| 1 | 流式对话 + React 前端 | ✅ |
| 2 | AI 诊断评估引擎 | ✅ |
| 3 | 生产加固 (JWT/持久化/防抖) | ✅ |
| 4 | 毕设完善 (口腔科/雷达图/PDF/管理后台) | ⬜ |
| 5 | 生产部署 (Docker/PostgreSQL) | ⬜ |

详见 [docs/project-status.md](docs/project-status.md)

---

## 致谢

本项目基于浙江大学 ZJUMAI 团队发表于 ACL 2025 的论文 [LLMs Can Simulate Standardized Patients via Agent Coevolution](https://arxiv.org/abs/2412.11716) 的开源实现进行二次开发。

## 许可证

Apache 2.0 License
