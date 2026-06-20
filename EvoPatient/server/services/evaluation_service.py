"""Evaluation service — AI assessment of student diagnosis against ground truth.

Phase 3: DB persistence via SessionService.

Pipeline:
  1. Generate standard diagnosis (ground truth) via Doctor.conclusion()
     using the FULL patient record (not vague).
  2. LLM compares student diagnosis vs ground truth on 4 dimensions.
  3. LLM generates teacher comment.
  4. Compute composite scores.
  5. Save to DB.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession

from core.api_call import llm_api
from core.doctor_agent import Doctor


_executor = ThreadPoolExecutor(max_workers=2)

# In-memory evaluation cache (kept for fast retrieval within the same process)
_eval_cache: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════
# Evaluation prompt template
# ═══════════════════════════════════════════════════════════════

EVALUATION_PROMPT = """You are a senior clinical teaching attending physician evaluating a medical student's
diagnosis performance. You have access to the complete medical record, the student's
diagnosis submission, the standard diagnosis, and the full consultation dialogue.

## PATIENT MEDICAL RECORD (GROUND TRUTH)
{full_patient_record}

## STANDARD DIAGNOSIS (REFERENCE ANSWER)
{standard_diagnosis}

## STUDENT'S DIAGNOSIS SUBMISSION
### 初步诊断 (Primary Diagnosis):
{student_primary}

### 诊断依据 (Evidence):
{student_evidence}

### 鉴别诊断 (Differential Diagnosis):
{student_differential}

### 建议检查 (Suggested Tests):
{student_tests}

## FULL CONSULTATION DIALOGUE
{dialogue}

## EVALUATION TASK
Evaluate the student's diagnosis on the following four dimensions, each scored 0-5:

1. **诊断正确性 (Diagnosis Correctness)**: Does the primary diagnosis match or come close to the
   standard diagnosis? 5=exact match, 3=partially correct, 0=completely wrong.
2. **依据充分性 (Evidence Sufficiency)**: Does the student cite specific symptoms and findings
   from the consultation that support their diagnosis? 5=comprehensive, 3=adequate, 0=insufficient.
3. **鉴别诊断合理性 (Differential Reasonableness)**: Are the alternative diagnoses clinically
   reasonable given the patient's presentation? 5=thorough, 3=partially, 0=irrelevant.
4. **检查建议合理性 (Test Reasonableness)**: Are the suggested tests appropriate and necessary
   for confirming the diagnosis? 5=exactly appropriate, 3=generally OK, 0=inappropriate.

Output your evaluation in exactly this format:

Score: <overall average 0-5>
诊断正确性: <0-5>
依据充分性: <0-5>
鉴别诊断合理性: <0-5>
检查建议合理性: <0-5>

## TEACHER COMMENT
Write 200-300 characters in Chinese. Provide encouraging feedback that:
- References specific findings from the consultation dialogue
- Points out 1-2 specific strengths
- Points out 1-2 specific areas for improvement
- Suggests what to focus on next time
"""


def _parse_evaluation(response: str) -> dict:
    """Parse structured evaluation output from LLM."""
    dims = {}
    dim_names = ["诊断正确性", "依据充分性", "鉴别诊断合理性", "检查建议合理性"]

    score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", response)
    overall = float(score_match.group(1)) if score_match else 3.0
    overall = round(min(max(overall, 0), 5), 1)

    for name in dim_names:
        m = re.search(rf"{name}:\s*(\d+(?:\.\d+)?)", response)
        val = float(m.group(1)) if m else 3.0
        dims[name] = {
            "score": round(min(max(val, 0), 5), 1),
            "max_score": 5,
            "reason": "",
        }

    comment_match = re.search(r"##\s*TEACHER\s*COMMENT\s*\n(.*?)$", response, re.DOTALL | re.IGNORECASE)
    teacher_comment = comment_match.group(1).strip() if comment_match else "请继续努力，多关注问诊的系统性和鉴别诊断的全面性。"
    if len(teacher_comment) > 500:
        teacher_comment = teacher_comment[:500]

    return {
        "overall_score": overall,
        "dimensions": dims,
        "teacher_comment": teacher_comment,
    }


def _extract_history_summary(resource: str) -> dict:
    """Extract structured sections from the patient record for display."""
    sections = {
        "personal_history": "",
        "physical_examination": "",
        "auxiliary_examination": "",
        "family_history": "",
    }

    patterns = {
        "personal_history": ["个人史", "既往史", "过敏史", "吸烟", "饮酒", "婚育史", "月经史"],
        "physical_examination": ["体格检查", "查体", "体温", "血压", "脉搏", "呼吸", "神志"],
        "auxiliary_examination": ["辅助检查", "检查", "MRI", "CT", "B超", "X线", "血常规", "尿常规", "心电图"],
        "family_history": ["家族史", "遗传"],
    }

    for section, keywords in patterns.items():
        for kw in keywords:
            idx = resource.find(kw)
            if idx >= 0:
                start = max(0, idx - 50)
                end = min(len(resource), idx + 200)
                text = resource[start:end].strip()
                if text:
                    sections[section] = text[:300]
                    break

    return sections


class EvaluationService:
    """Evaluates student diagnosis against ground truth, persists to DB."""

    @classmethod
    async def evaluate_diagnosis(
        cls,
        session_id: str,
        submission: dict,
        db: DbAsyncSession | None = None,
    ) -> dict:
        """Run the full evaluation pipeline in a thread pool.

        Args:
            session_id: The session identifier.
            submission: Dict with keys: primary_diagnosis, evidence,
                        differential_diagnosis, suggested_tests.
            db: Optional DB session for persistence.

        Returns:
            Dict with full evaluation result.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, cls._evaluate_sync, session_id, submission
        )

        # ── Persist to DB ──
        if db is not None:
            from server.services.session_service import SessionService

            await SessionService.save_evaluation(
                db,
                session_id=session_id,
                primary_diagnosis=submission.get("primary_diagnosis", ""),
                evidence=submission.get("evidence", ""),
                differential=submission.get("differential_diagnosis", ""),
                suggested_tests=submission.get("suggested_tests", ""),
                overall_score=result["overall_score"],
                consultation_score=result["consultation_quality"],
                diagnosis_score=result["diagnosis_accuracy"],
                dimension_scores=result["consultation_dimensions"],
                teacher_comment=result["teacher_comment"],
                standard_diagnosis=result["standard_diagnosis"],
                history_summary=result["history_summary"],
            )

        # Cache for fast retrieval
        _eval_cache[session_id] = result
        return result

    @classmethod
    def _evaluate_sync(cls, session_id: str, submission: dict) -> dict:
        """Synchronous evaluation logic (runs in thread pool)."""
        from server.services.session_service import SessionService

        try:
            ctx = SessionService.get_context(session_id)
        except KeyError:
            raise ValueError(f"Session {session_id} not found")

        # ── Step 1: Generate ground truth from FULL patient record ──
        full_prompt_data = dict(ctx.prompt_data)
        full_prompt_data["resource"] = ctx.resource
        if "vague_resource" not in full_prompt_data or not full_prompt_data.get("vague_resource"):
            full_prompt_data["vague_resource"] = ctx.vague_info

        doctor = Doctor(
            ctx.patient,
            ctx.office,
            ctx.main_complaint,
            str(ctx.directory),
            full_prompt_data,
        )

        dq_path = ctx.directory / "doctor_question.txt"
        if dq_path.exists():
            doctor.dialog_history = dq_path.read_text(encoding="utf-8")

        try:
            standard_diagnosis = doctor.conclusion()
        except Exception:
            standard_diagnosis = "无法生成标准诊断（API 错误）"

        # ── Step 2: Build evaluation prompt ──
        dialogue = ""
        if dq_path.exists():
            raw = dq_path.read_text(encoding="utf-8")
            if len(raw) > 3000:
                dialogue = "...(earlier dialogue omitted)\n" + raw[-3000:]
            else:
                dialogue = raw

        prompt = EVALUATION_PROMPT.format(
            full_patient_record=ctx.resource,
            standard_diagnosis=standard_diagnosis,
            student_primary=submission.get("primary_diagnosis", ""),
            student_evidence=submission.get("evidence", ""),
            student_differential=submission.get("differential_diagnosis", ""),
            student_tests=submission.get("suggested_tests", ""),
            dialogue=dialogue,
        )

        # ── Step 3: LLM evaluation ──
        try:
            response = llm_api([{"role": "user", "content": prompt}])
            eval_result = _parse_evaluation(response)
        except Exception:
            eval_result = {
                "overall_score": 3.0,
                "dimensions": {
                    "诊断正确性": {"score": 3.0, "max_score": 5, "reason": ""},
                    "依据充分性": {"score": 3.0, "max_score": 5, "reason": ""},
                    "鉴别诊断合理性": {"score": 3.0, "max_score": 5, "reason": ""},
                    "检查建议合理性": {"score": 3.0, "max_score": 5, "reason": ""},
                },
                "teacher_comment": "评估生成失败，请重试。",
            }

        # ── Step 4: Compute composite scores ──
        dims = eval_result["dimensions"]
        diagnosis_accuracy = sum(d["score"] for d in dims.values()) / len(dims)
        consultation_quality = min(diagnosis_accuracy, 5.0)
        overall = round(diagnosis_accuracy * 0.6 + consultation_quality * 0.4, 1)

        # ── Step 5: Extract history summary ──
        history_summary = _extract_history_summary(ctx.resource)

        result = {
            "evaluation_id": f"eval-{session_id}",
            "session_id": session_id,
            "overall_score": overall,
            "consultation_quality": consultation_quality,
            "diagnosis_accuracy": round(diagnosis_accuracy, 1),
            "consultation_dimensions": dims,
            "diagnosis_dimensions": dims,
            "teacher_comment": eval_result["teacher_comment"],
            "standard_diagnosis": standard_diagnosis,
            "history_summary": history_summary,
            "created_at": "",
        }

        _eval_cache[session_id] = result
        return result

    @classmethod
    def get_cached_evaluation(cls, session_id: str) -> dict | None:
        """Retrieve a previously computed evaluation from cache."""
        return _eval_cache.get(session_id)

    @classmethod
    async def get_evaluation_from_db(
        cls,
        session_id: str,
        db: DbAsyncSession,
    ) -> dict | None:
        """Retrieve evaluation from database."""
        from server.services.session_service import SessionService

        return await SessionService.get_evaluation_dict(db, session_id)
