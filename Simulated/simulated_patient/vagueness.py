"""Generate vague (imprecise) patient information from structured medical records.

This module reads patient data from Excel, applies dropout-based obfuscation,
and uses LLM to produce a more naturalistic "vague" version. It no longer
writes back to prompt_data.json — callers should inject the returned values
into prompt_data themselves.
"""

import json
import random
import re
from pathlib import Path

import openpyxl
from Simulated.simulated_patient.api_call import llm_api


# ---------- Utility functions ----------

def select_random_positions(lst, percentage):
    """Randomly select index positions from a list by percentage."""
    if not lst or percentage <= 0:
        return []
    k = int(len(lst) * (percentage / 100.0))
    k = max(0, min(k, len(lst)))
    if k == 0:
        return []
    return random.sample(range(len(lst)), k)


def split_string_by_punctuation(text: str):
    """Split text into alternating punctuation / non-punctuation fragments.

    Example: 'a,b' -> ['a', ',', 'b']
    """
    pattern = re.compile(r'[^\w\s]|[\w\s]+', flags=re.UNICODE)
    return [m.group(0) for m in pattern.finditer(text or '')]


def random_dropout(split_tokens):
    """Randomly drop ~30% of fragments with heuristic context removal."""
    selected = select_random_positions(split_tokens, 30)
    to_delete = set()

    for pos in selected:
        token = split_tokens[pos]
        if token.isdigit():
            to_delete.add(pos)
            if pos + 1 < len(split_tokens):
                to_delete.add(pos + 1)
            if pos + 2 < len(split_tokens):
                to_delete.add(pos + 2)
        elif token.isalpha():
            if pos - 2 >= 0 and split_tokens[pos - 2].isdigit():
                to_delete.add(pos - 2)
            to_delete.add(pos)
        else:
            if pos - 1 >= 0 and split_tokens[pos - 1].isdigit():
                to_delete.add(pos - 1)
            if pos + 1 < len(split_tokens):
                to_delete.add(pos + 1)

    return [t for i, t in enumerate(split_tokens) if i not in to_delete]


def dropout_vague(text: str) -> str:
    tokens = split_string_by_punctuation(text or "")
    kept = random_dropout(tokens)
    return "".join(kept)


# ---------- Business logic ----------

def get_patient_info(sheet_name: str, row_number: int, col_number: int) -> str:
    """Read a cell from the patient Excel file and return the text.

    No longer writes to prompt_data.json.
    """
    xlsx_path = Path("dataset") / "patient_text.xlsx"
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"File not found: {xlsx_path}")

    wb = openpyxl.load_workbook(xlsx_path)
    try:
        sheet = wb[sheet_name]
        cell_value = sheet[row_number][col_number].value
    finally:
        wb.close()

    return str(cell_value or "")


def get_vague_patient_info(sheet_name: str, row_number: int, col_number: int) -> tuple[str, str]:
    """Read patient info -> apply dropout -> LLM vague generation.

    Returns (original_text, vague_text) without any file side-effects.
    Callers should inject these into prompt_data as needed.
    """
    patient_info = get_patient_info(sheet_name, row_number, col_number)
    patient_info_drop = dropout_vague(patient_info)

    # Read vagueness prompt template (read-only, no write-back)
    json_path = Path("Simulated") / "Prompt" / "prompt_data.json"
    if not json_path.is_file():
        raise FileNotFoundError(f"File not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "vagueness" not in data or not isinstance(data["vagueness"], list):
        raise KeyError("prompt_data.json is missing 'vagueness' or its type is not list")
    vagueness_prompt = "".join(data["vagueness"])
    prompt = vagueness_prompt.format(information=patient_info_drop)

    vague_patient_info = llm_api([{"role": "user", "content": prompt}])

    return patient_info, vague_patient_info
