# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

EvoPatient — a multi-agent simulation system that uses LLMs to simulate standardized patient-doctor medical consultations. This is the reference implementation for the paper "LLMs Can Simulate Standardized Patients via Agent Coevolution" (arXiv:2412.11716, ACL 2025).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run batch simulation (iterates rows 2–1300 from dataset/patient_text.xlsx)
python run.py

# Interactive mode — you play the doctor, the AI is the patient
python interactive.py

# Build the cover pool (embeds chief complaints into dataset/pool.csv)
python cover.py

# Build patient_data.json from the Excel dataset
cd dataset && python bulit_dataset.py
```

**Note:** The existing CLAUDE.md and README mention `python simulateflow.py` as an entry point — this file has no `if __name__ == "__main__"` block and cannot be run directly. It is a library module called by `run.py`, `interactive.py`, and `cover.py`.

## Environment setup

All API keys and model names are read from environment variables via `python-dotenv` from a `.env` file at the project root. **Do not edit source files** to set API keys (the README's instructions to edit `api_call.py` are outdated — the code uses env vars exclusively).

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | API key (OpenAI-compatible) | **required** |
| `BASE_URL` | Custom API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Primary chat model | (must be set) |
| `LLM_LITE_MODEL` | Cheaper/faster chat model | (must be set) |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-ada-002` |

The `.env` is loaded inside `api_call.py` and again at the top of each runnable script (`run.py`, `interactive.py`, `cover.py`, `simulateflow.py`) as a safety measure.

## Architecture

### Entry points

| Script | Purpose |
|---|---|
| `run.py` | Batch loop: reads `case_cache.txt` for resume position, iterates Excel rows, calls `simulateflow.flow()` |
| `interactive.py` | Human-as-doctor mode: pick a patient row, type questions, get AI patient responses with quality scores |
| `cover.py` | Generates medical cover summaries and embeds chief complaints into `dataset/pool.csv` (used for retrieval) |

All three call `simulateflow.init_session()` for shared setup.

### Core simulation loop ([`simulateflow.py`](simulateflow.py))

1. **`init_session()`** — loads a patient record from `dataset/patient_text.xlsx`, applies dropout-based obfuscation via `vagueness.py` to create a "vague" version (simulating a real patient's imprecise recall), assigns a department via LLM, generates a chief complaint, and creates the output directory structure.
2. **`flow()`** — runs the full doctor-patient dialogue loop: the Doctor agent asks questions, the Patient agent answers. A random "crisis event" (medical emergency) is injected mid-consultation. Runs up to 10 turns. When the Doctor returns `"conclusion"`, the loop ends early and a diagnosis is generated.

### Agent components

- **Patient Agent** ([`patient_agent.py`](Simulated/simulated_patient/patient_agent.py)) — generates answers using: (1) a randomly-selected character profile from `profile/profile_pool/`, (2) RAG-retrieved medical context from the patient's full record, and (3) few-shot examples from the evolution store (`dataset/patient_evolve.csv` — past high-quality Q&A pairs retrieved by cosine similarity). When answer quality scores ≥ 3, dynamic requirements are extracted and stored for future few-shot use.

- **Doctor Agent** ([`doctor_agent.py`](Simulated/simulated_patient/doctor_agent.py)) — asks diagnostic questions drawing on: the patient's chief complaint, a rolling summary of dialogue history (summarized every 3 turns), few-shot examples from the specialty's evolution CSV (`dataset/doctor_evolve_{office}.csv`), and summaries from recruited sub-specialists. Produces a final diagnosis via `conclusion()`. Also handles crisis response via `doctor_crisis_answer()`.

- **Doctor Recruit** ([`doctor_recruit.py`](Simulated/simulated_patient/doctor_recruit.py)) — dynamically recruits specialist doctors based on the patient's condition. Two implementations exist: `Doctor.recruit()` (tightly coupled to Doctor, used in the main flow) and the standalone `Recruit` class (configurable topology support — DAG, tree, chain — partially implemented, not wired into the main flow).

### Agent coevolution ([`agent_evolve.py`](Simulated/simulated_patient/agent_evolve.py))

The key contribution of the paper. High-quality Q&A pairs are stored per-specialty in CSV files. Before each agent action, the system retrieves the most similar past Q&A via cosine similarity on text embeddings. This acts as dynamic few-shot learning — agents improve over time as the evolution store accumulates good examples.

- Patient evolution: `dataset/patient_evolve.csv` — columns: `qus_embedding, question, rag_info, answer, requirements`
- Doctor evolution: `dataset/doctor_evolve_{office}.csv` — columns: `question1, qus_embedding, rag_info1, answer1, qus2_embedding, question2, answer2, rag_info2`

Deduplication in the store: new entries with cosine similarity > 0.95 (patient) or > 0.8 for both Q&A pairs (doctor) to existing entries are skipped.

### RAG system ([`RAG/`](RAG/))

Three retrieval paths, but only `rag_patient()` from `rag.py` is used in the agent code:

- **[`rag.py`](RAG/rag.py)** — primary retrieval: chunks the patient's medical record with `RecursiveCharacterTextSplitter`, indexes with FAISS + BailianEmbeddings (a LangChain-compatible wrapper over the raw OpenAI client), retrieves top-k relevant chunks per question. Called by both Patient and Doctor agents.
- **[`fusion_retrieval.py`](RAG/fusion_retrieval.py)** — hybrid retrieval combining BM25 (keyword) + FAISS (vector) scores with configurable `alpha` weighting. Not used by agents; has a standalone `run_demo()`.
- **[`rag_pdf.py`](RAG/rag_pdf.py)** — PDF-specific RAG pipeline. Not used by agents; has a standalone `run_demo()` that references an external PDF and `evaluation/evalute_rag` (not present in the repo).

**[`helper_functions.py`](RAG/helper_functions.py)** contains `BailianEmbeddings` (LangChain `Embeddings` subclass — uses the raw OpenAI client to avoid langchain-openai format issues with DashScope/Bailian endpoints), text chunking utilities, BM25 helpers, and retry logic.

### API layer ([`api_call.py`](Simulated/simulated_patient/api_call.py))

Unified LLM client providing three functions:
- `llm_api(messages)` — primary chat model (env: `LLM_MODEL`)
- `llm_api_lite(messages)` — cheaper/faster chat model (env: `LLM_LITE_MODEL`)
- `get_text_embedding(text)` / `get_code_embedding(code)` — embeddings (env: `EMBEDDING_MODEL`)

Token usage is automatically accumulated in `make_task/token_count/` via `token_counter()`. After each simulation run, these files are moved into the experiment directory.

**Note:** There is a secondary embedding module at `embedding_function/sentence_embedding.py` that uses `OPENAI_API_BASE` (not `BASE_URL`) for the base URL. It is **not used** by the main agent code — `api_call.get_text_embedding()` and `RAG/helper_functions.BailianEmbeddings` are the active embedding paths.

### Vagueness / obfuscation ([`vagueness.py`](Simulated/simulated_patient/vagueness.py))

Reads structured patient data from Excel → applies random dropout (~30% of tokens, with heuristic context removal for dates/numbers) → sends the degraded text to an LLM with a "vagueness" prompt to generate naturalistic imprecise patient recall. Returns `(original_text, vague_text)` — no longer writes to `prompt_data.json` (callers inject values themselves).

### Evaluation (quality scoring)

Quality assessment functions are defined in [`make_task/overall_assessment_llm.py`](make_task/overall_assessment_llm.py). **The current implementation is a stub** — it returns neutral scores of 3 for all metrics. The original evaluation module was not open-sourced. Replace these stubs with real LLM-based evaluation if needed.

- `overall_assessment_patient(question, useful_info, ans, profile)` → `(score, relevance, faithfulness, robustness)`
- `overall_assessment_doctor(question, useful_info, answer)` → `(score, specificity, targetedness, professionalism)`

Both are lazy-imported in the agent files to avoid circular dependencies.

### Memory stream ([`Simulated/memory/memory_stream.py`](Simulated/memory/memory_stream.py))

Provides `memory_store()` and `summary()` for periodically summarizing doctor-patient dialogue into `memory_warehouse.txt`. **Not used by the main simulation flow** — the Doctor class has its own `make_summary()` method that manages dialogue summaries internally. This module appears to be from an earlier iteration or alternative flow path.

### Prompt templates

The primary prompt store is [`Simulated/Prompt/prompt_data.json`](Simulated/Prompt/prompt_data.json) — a JSON object where each value is a list of strings concatenated at runtime by `read_prompt()` in [`utils.py`](utils.py). A secondary store exists at [`dataset/Prompt_store/prompt_data.json`](dataset/Prompt_store/prompt_data.json) (not used by the main flow). Both directories also contain `txt_to_json.py` helper scripts for converting text templates to JSON format.

### Output format

Each simulation run creates a timestamped directory under `exp1/` containing:
- `resource.txt` / `vague.txt` — patient data (original and obfuscated)
- `question_record.csv` — per-turn Q&A with timing, token metrics, Chinese character counts
- `doctor_record/{office}_{level}.csv` — per-doctor question scoring with quality dimensions
- `conclusion.txt` — final diagnosis
- `crisis.txt` — emergency event log (if triggered)
- `token_count/` — accumulated token usage (moved from `make_task/token_count/`)
- `time_cost.txt` — wall-clock time for the last turn

A convenience copy of `question_record.csv` is also written at the project root.

### Dataset

- `dataset/patient_text.xlsx` — source patient data (multi-sheet Excel, referenced at row/cell granularity)
- `dataset/patient_data.json` — built by `dataset/bulit_dataset.py`, aggregates across sheets by patient ID
- `dataset/patient_evolve.csv` — patient-side evolution store
- `dataset/doctor_evolve_{office}.csv` — doctor-side evolution stores (one per specialty)
- `dataset/pool.csv` — cover pool (embeddings of chief complaints, built by `cover.py`)

## Agent skills

### Issue tracker

GitHub Issues on `HjyGb/PatientAgent`. PRs are not a request surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary — identity mapping for all five canonical triage roles. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo — one `CONTEXT.md` + `docs/adr/` at the root. See `docs/agents/domain.md`.
