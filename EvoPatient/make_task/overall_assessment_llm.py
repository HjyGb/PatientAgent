"""LLM-based quality assessment for patient answers and doctor questions.

Replaces the stub that returned neutral scores. Uses llm_api_lite()
(cheaper model) for efficiency since evaluation runs every Q&A turn.
"""

import re
from pathlib import Path

from Simulated.simulated_patient.api_call import llm_api_lite
from utils import read_prompt


def _parse_scores(response: str, *dim_names: str) -> tuple[int, ...]:
    """Parse structured score output from LLM.

    Expected format:
        Score: <overall>
        Dim1: <0-5>
        Dim2: <0-5>
        ...

    Args:
        response: LLM response text.
        *dim_names: Expected dimension names in order (e.g., "Relevance", "Faithfulness", "Robustness").

    Returns:
        Tuple of int scores in order: (overall_score, dim1, dim2, ...).
        Falls back to (3, 3, 3, ...) on parse failure.
    """
    # Extract overall score
    score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", response)
    overall = float(score_match.group(1)) if score_match else 3.0
    overall = round(min(max(overall, 0), 5))

    dims = []
    for name in dim_names:
        m = re.search(rf"{name}:\s*(\d+(?:\.\d+)?)", response, re.IGNORECASE)
        val = float(m.group(1)) if m else 3.0
        dims.append(round(min(max(val, 0), 5)))

    return (overall, *dims)


def overall_assessment_patient(
    question: str,
    useful_info: str,
    ans: str,
    profile: str,
) -> tuple[int, int, int, int]:
    """Evaluate patient answer quality using LLM.

    Returns:
        (score, relevance, faithfulness, robustness) — each 0-5.
    """
    try:
        prompt_data = read_prompt()
        prompt_tpl = prompt_data.get("patient_assessment", "")
        if not prompt_tpl:
            return (3, 3, 3, 3)

        prompt = prompt_tpl.format(
            profile=profile or "No profile available",
            information=useful_info or "No medical information available",
            question=question,
            answer=ans,
        )
        messages = [{"role": "user", "content": prompt}]
        response = llm_api_lite(messages)

        overall, relevance, faithfulness, robustness = _parse_scores(
            response, "Relevance", "Faithfulness", "Robustness"
        )
        return (overall, relevance, faithfulness, robustness)

    except Exception as e:
        print(f"[patient assessment] LLM evaluation failed: {e}, using defaults")
        return (3, 3, 3, 3)


def overall_assessment_doctor(
    question: str,
    useful_info: str,
    answer: str,
) -> tuple[int, int, int, int]:
    """Evaluate doctor question quality using LLM.

    Returns:
        (score, specificity, targetedness, professionalism) — each 0-5.
    """
    try:
        prompt_data = read_prompt()
        prompt_tpl = prompt_data.get("doctor_assessment", "")
        if not prompt_tpl:
            return (3, 3, 3, 3)

        prompt = prompt_tpl.format(
            information=useful_info or "No medical information available",
            question=question,
            answer=answer,
        )
        messages = [{"role": "user", "content": prompt}]
        response = llm_api_lite(messages)

        overall, specificity, targetedness, professionalism = _parse_scores(
            response, "Specificity", "Targetedness", "Professionalism"
        )
        return (overall, specificity, targetedness, professionalism)

    except Exception as e:
        print(f"[doctor assessment] LLM evaluation failed: {e}, using defaults")
        return (3, 3, 3, 3)
