# PatientAgent 2.0 — 项目总览与进度

## 项目目标

在 Python AI Agent 引擎之上，构建面向**医学生临床教学的标准化病人模拟问诊平台**。
三级目标：求职简历项目 → 毕业设计 → 真实医院落地。

---

## 技术栈

```
┌──────────────────────────────────────────┐
│  React 19 SPA (Vite 8 + TypeScript 6)   │  ← patient-agent-ui/
│  Tailwind CSS v4 + Zustand 5             │
├──────────────────────────────────────────┤
│  FastAPI (uvicorn)  REST + SSE           │  ← EvoPatient/server/
│  SQLAlchemy 2.0 + SQLite                 │
├──────────────────────────────────────────┤
│  core/ 共享 Python 包                     │  ← EvoPatient/core/
│  Patient Agent / Doctor Agent / RAG      │
│  Agent Coevolution / Vagueness           │
└──────────────────────────────────────────┘
```

---

## 进度总览

### ✅ Phase 0: 基础设施重构

| 子任务 | 状态 | 说明 |
|--------|------|------|
| `core/` 共享包重构 | ✅ | `Simulated/simulated_patient/` → `core/` |
| FastAPI 脚手架 | ✅ | `server/main.py`, `config.py`, `dependencies.py` |
| DB 模型 (SQLAlchemy 2.0) | ✅ | `users`, `sessions`, `messages`, `evaluations` |
| Pydantic v2 Schemas | ✅ | `auth`, `case`, `session`, `evaluation` |
| 4 个 Router + 2 个 Service | ✅ | `auth`, `cases`, `sessions`, `evaluations` |

**关键文件:**
- `EvoPatient/server/main.py` — FastAPI app入口
- `EvoPatient/server/models/` — 4张表的ORM定义
- `EvoPatient/server/schemas/` — API接口类型定义

---

### ✅ Phase 1: 核心 API + 流式对话

| 子任务 | 状态 | 说明 |
|--------|------|------|
| `llm_api_stream()` | ✅ | 逐 token yield 的流式 LLM 调用 |
| `Patient.patient_ans_stream()` | ✅ | 流式患者回答 + StopIteration 安全包装 |
| SSE 端点 | ✅ | `GET /sessions/{id}/messages/stream` |
| 10 个 REST API | ✅ | cases CRUD, load, messages, info |
| React 前端 4 列 Grid | ✅ | LeftSidebar / ChatPanel / MedicalForm / EvaluatePanel |
| Zustand 3 Store | ✅ | `case-store`, `chat-store`, `record-store` |
| SSE EventSource 流式渲染 | ✅ | token 逐字追加 + 完成后评分标签 |

**关键文件:**
- `EvoPatient/core/api_call.py` — `llm_api_stream()`
- `EvoPatient/core/patient_agent.py` — `patient_ans_stream()`
- `EvoPatient/server/services/chat_service.py` — `_safe_next()` 包装
- `patient-agent-ui/src/components/interview/ChatPanel.tsx` — SSE 消费

---

### ✅ Phase 2: 专业评估引擎

| 子任务 | 状态 | 说明 |
|--------|------|------|
| Ground Truth 生成 | ✅ | `Doctor.conclusion()` 基于完整病历 |
| LLM 4维评估 | ✅ | 诊断正确性/依据充分性/鉴别诊断合理性/检查建议合理性 |
| 教师评语 (中文) | ✅ | 引用对话 + 优点 + 改进建议 |
| 综合评分 | ✅ | overall = 诊断×0.6 + 问诊×0.4 |
| 评估弹窗 UI | ✅ | EvaluateModal: 总分、维度、评语、标准诊断 |

**关键文件:**
- `EvoPatient/server/services/evaluation_service.py` — 4步评估流水线
- `patient-agent-ui/src/components/evaluation/EvaluateModal.tsx`

---

### ✅ Phase 3: 生产加固

| 子任务 | 状态 | 说明 |
|--------|------|------|
| SessionService (DB持久化) | ✅ | 会话/消息/评估全部落盘 |
| ChatService 轮次追踪 | ✅ | 原子递增 + DB消息保存 |
| EvaluationService DB存储 | ✅ | 评估结果双写 (内存缓存 + DB) |
| JWT 认证 (软模式) | ✅ | 有token返回用户，无token允许匿名 |
| 历史记录 API | ✅ | `GET /sessions/history` DB分页查询 |
| Toast 通知系统 | ✅ | success/error/warning/info 4类型 |
| 输入防抖 | ✅ | ChatPanel 300ms guard 防重复发送 |
| Auth Store (前端) | ✅ | JWT token localStorage 持久化 |
| 左侧栏历史列表 | ✅ | `useQuery` 拉取真实历史数据 |
| 错误兜底 | ✅ | Toast 替代 alert，网络中断强提示 |

**关键文件:**
- `EvoPatient/server/services/session_service.py` — 完整DB会话管理
- `patient-agent-ui/src/stores/toast-store.ts` — Toast状态管理
- `patient-agent-ui/src/stores/auth-store.ts` — JWT认证状态
- `patient-agent-ui/src/components/ui/ToastContainer.tsx`

---

### ⬜ 未完成：Phase 4 (毕业设计完善)

| 任务 | 优先级 | 工作量估算 |
|------|--------|-----------|
| **口腔科垂直化配置** | ⭐⭐⭐ | 1-2天 |
| 诊断维度雷达图 (Recharts) | ⭐⭐ | 半天 |
| PDF 评估报告导出 (reportlab) | ⭐⭐ | 1天 |
| 移动端响应式适配 | ⭐ | 1-2天 |
| 教师管理后台 | ⭐⭐ | 3-5天 |
| Alembic 数据库迁移 | ⭐ | 半天 |
| pytest + React Testing Library | ⭐ | 1-2天 |

---

### ⬜ 未完成：Phase 5 (生产部署)

| 任务 | 优先级 | 工作量估算 |
|------|--------|-----------|
| Docker Compose (Nginx + FastAPI + SQLite) | ⭐⭐ | 半天 |
| PostgreSQL 迁移 | ⭐ | 半天 (改一行连接串) |
| structlog 日志 + Sentry | ⭐ | 1天 |

---

## 文件地图

### 后端 (EvoPatient/)

```
EvoPatient/
├── core/                          # 共享 AI Agent 包
│   ├── patient_agent.py           # 患者 Agent + 流式方法
│   ├── doctor_agent.py            # 医生 Agent + conclusion()
│   ├── agent_evolve.py            # Agent Coevolution 进化
│   ├── vagueness.py               # 病历模糊化 (30% dropout)
│   ├── api_call.py                # LLM + Embedding API + 流式
│   └── rag/                       # RAG 检索
│       ├── rag.py                 # FAISS 稠密检索 (主入口)
│       ├── helper_functions.py    # BailianEmbeddings 等
│       └── fusion_retrieval.py    # BM25+FAISS 混合检索 (demo)
│
├── server/                        # FastAPI 服务层
│   ├── main.py                    # App 入口 + CORS + lifespan
│   ├── config.py                  # 环境变量配置
│   ├── dependencies.py            # DB引擎 + JWT认证
│   ├── models/                    # SQLAlchemy ORM
│   │   ├── user.py, session.py, message.py, evaluation.py
│   ├── schemas/                   # Pydantic v2 接口类型
│   │   ├── auth.py, case.py, session.py, evaluation.py
│   ├── routers/                   # API 路由
│   │   ├── auth.py, cases.py, sessions.py, evaluations.py
│   └── services/                  # 业务逻辑
│       ├── case_service.py        # 病例加载 + 科室匹配
│       ├── chat_service.py        # 问答处理 + SSE流 + DB持久
│       ├── session_service.py     # 会话生命周期 + 历史
│       └── evaluation_service.py  # 4步评估流水线
│
├── dataset/
│   ├── patient_text.xlsx          # 10个跨科室仿真病例
│   ├── patient_evolve.csv         # 患者进化库 (760KB)
│   └── doctor_evolve_*.csv        # 医生进化库 (按科室)
│
├── docs/
│   ├── vector-retrieval.md        # 向量检索系统文档
│   └── project-status.md          # 本文档
│
├── test_e2e.py                    # 全自动端到端测试脚本
├── simulateflow.py                # 核心模拟流程
├── interactive.py                 # 交互式问诊 (命令行)
└── run.py                         # 批量自动运行
```

### 前端 (patient-agent-ui/)

```
patient-agent-ui/src/
├── App.tsx                        # 路由 + QueryClient + ToastContainer
├── index.css                      # Tailwind + CSS变量 + 动画
│
├── lib/
│   └── api-client.ts              # API 封装 (fetch + JWT)
│
├── stores/                        # Zustand 状态管理
│   ├── auth-store.ts              # JWT token + 用户信息 (localStorage)
│   ├── case-store.ts              # sessionId + 病例状态
│   ├── chat-store.ts              # messages[] + 流式 + turn
│   ├── record-store.ts            # 诊断草稿 (localStorage) + 评估
│   └── toast-store.ts             # Toast 通知队列
│
├── pages/
│   ├── InitPage.tsx               # 初始化页: 工号+病例号→加载
│   └── InterviewPage.tsx          # 4列Grid主页面
│
├── components/
│   ├── ui/
│   │   └── ToastContainer.tsx     # 右上角通知组件
│   ├── interview/
│   │   ├── LeftSidebar.tsx        # 患者头像 + 历史列表
│   │   ├── ChatPanel.tsx          # SSE流式聊天 + 防抖
│   │   ├── MedicalForm.tsx        # 诊断表单 + 自动保存
│   │   └── EvaluatePanel.tsx      # 评估概览卡片
│   └── evaluation/
│       └── EvaluateModal.tsx      # 完整评估报告弹窗
```

---

## 当前数据库状态

| 表 | 行数 | 说明 |
|---|---|---|
| users | 0 | 暂无注册 (soft auth模式) |
| sessions | 4 | 历史问诊会话 |
| messages | 18 | Q&A记录 (含评分) |
| evaluations | 2 | AI评估报告 |

---

## 启动命令

```bash
# 后端
cd d:/Project/PatientAgent/EvoPatient
uvicorn server.main:app --reload --port 8000

# 前端
cd d:/Project/PatientAgent/patient-agent-ui
npm run dev

# 自动化测试 (无需医学知识)
cd d:/Project/PatientAgent/EvoPatient
python test_e2e.py
```

---

## 下一步建议

按优先级排序：

1. **口腔科垂直化** — 最具差异化价值。添加口腔科配置 + 3-5 个口腔仿真病例
2. **诊断雷达图** — 半天工作量，评估报告视觉效果质的飞跃
3. **PDF 导出** — 可打印的正式评估报告
4. **Docker 部署** — 一键启动全套服务
