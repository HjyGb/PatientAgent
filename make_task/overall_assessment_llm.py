"""Quality assessment stubs for EvoPatient.

The original evaluation module is not open-sourced.
This stub provides neutral scores so the simulation loop can run.
Replace with real evaluation logic if needed.
"""


def overall_assessment_patient(question: str, useful_info: str, ans: str, profile: str):
    """Evaluate patient answer quality.

    Returns:
        (score, relevance, faithfulness, robustness) — each 0-5 scale.
    """
    return (3, 3, 3, 3)


def overall_assessment_doctor(question: str, useful_info: str, answer: str):
    """Evaluate doctor question quality.

    Returns:
        (score, specificity, targetedness, professionalism) — each 0-5 scale.
    """
    return (3, 3, 3, 3)
