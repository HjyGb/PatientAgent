"""Main simulation flows for PatientAgent.

Provides:
  - init_session: shared setup logic (create dirs, load patient, assign dept, generate complaint)
  - flow: full doctor-patient dialogue simulation
"""

import csv
import os
import time
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

# Load .env BEFORE any project imports that may check env vars at module level
from dotenv import load_dotenv
load_dotenv()

from core.vagueness import get_vague_patient_info
from core.patient_agent import Patient
from core.doctor_agent import Doctor
from utils import (
    ensure_parent,
    match_star_strict,
    read_prompt,
    clean_token_count,
    get_token_count,
    count_chinese_characters,
)


@dataclass
class SessionContext:
    """Holds the initialized state for a simulation session."""
    directory: Path
    resource: str
    vague_info: str
    prompt_data: dict
    patient: Patient
    office: str
    main_complaint: str


def init_session(
    sheet_name: str,
    row_number: int,
    col_number: int,
    output_dir: str = "exp1",
) -> SessionContext:
    """Common initialization: create dirs, load patient, assign dept, generate complaint.

    Args:
        sheet_name: Excel sheet name to read patient data from.
        row_number: Row number in the Excel sheet.
        col_number: Column number in the Excel sheet.
        output_dir: Parent directory for experiment output.

    Returns:
        A SessionContext with all initialized state.
    """
    clean_token_count()

    test_label = str(time.time())
    parent_folder = Path(output_dir)
    directory = parent_folder / test_label
    (directory / "doctor_record").mkdir(parents=True, exist_ok=True)
    print(f"Folder {test_label} created in {parent_folder}.")

    # Read patient full info + vague info
    resource, vague_info = get_vague_patient_info(sheet_name, row_number, col_number)

    # Save original resource and vague info
    (directory / "resource.txt").write_text(resource, encoding="utf-8")
    (directory / "vague.txt").write_text(vague_info, encoding="utf-8")

    prompt_data = read_prompt()
    # Inject runtime data (vagueness.py no longer writes to prompt_data.json)
    prompt_data["resource"] = resource
    prompt_data["vague_resource"] = vague_info
    patient = Patient(vague_info, resource, str(directory), prompt_data)

    # Assign department (extract from **...**)
    office = match_star_strict(patient.assign_office())

    # Generate chief complaint
    patient_question = patient.generate_patient_question()
    main_complaint = match_star_strict(patient_question)
    print("Patient question:", main_complaint)

    return SessionContext(
        directory=directory,
        resource=resource,
        vague_info=vague_info,
        prompt_data=prompt_data,
        patient=patient,
        office=office,
        main_complaint=main_complaint,
    )


# ====== Full dialogue flow ======
def flow(sheet_name: str = "病程记录_首次病程", row_number: int = 6, col_number: int = 1):
    ctx = init_session(sheet_name, row_number, col_number, output_dir="exp1")

    # Initialize doctor and ask the first question
    doctor = Doctor(ctx.patient, ctx.office, ctx.main_complaint, str(ctx.directory), ctx.prompt_data)
    resp = doctor.doctor_qus(ctx.main_complaint, 0, 0, 0, 0)
    try:
        doctor_question = match_star_strict(resp)
    except Exception:
        doctor_question = resp

    # Patient's first answer
    patient_answer, score, rel, faith, human = ctx.patient.patient_ans(doctor_question)

    max_turn = 10
    cnt = 0
    auto = True
    random_crisis_num = random.randrange(int(max_turn / 2), max_turn)

    # Turn records (experiment directory + top-level convenience file)
    exp_csv = ctx.directory / "question_record.csv"
    top_csv = Path("question_record.csv")
    for p in (exp_csv, top_csv):
        if not p.exists():
            ensure_parent(p)
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "row", "question", "answer", "token_count_doctor", "token_count_patient",
                    "resource", "doctor_time", "patient_time", "question_cnt", "answer_cnt"
                ])

    while cnt < max_turn:
        cnt += 1

        # Introduce a "crisis event" at a random turn
        if cnt == random_crisis_num:
            patient_crisis = ctx.patient.crisis_begin()
            doctor_crisis_ans = doctor.doctor_crisis_answer(ctx.office, patient_crisis)
            patient_ans_after_crisis = ctx.patient.patient_crisis_ans(doctor_crisis_ans)

            crisis_file = ctx.directory / "crisis.txt"
            crisis_txt = (
                f"Turn: **{cnt}** Patient emergency: **{patient_crisis}**"
                f"Doctor response to emergency: **{doctor_crisis_ans}**"
                f"Patient reaction to doctor response: **{patient_ans_after_crisis}**"
            )
            crisis_file.write_text(crisis_txt, encoding="utf-8")

        start_time = time.time()

        if auto:
            # Doctor asks a question
            next_q = doctor.doctor_qus(patient_answer, score, rel, faith, human)
            if next_q == "skip":
                continue
            if next_q == "conclusion":
                print("Enough information obtained, stopping early.")
                break
            try:
                doctor_question = match_star_strict(next_q)
            except Exception:
                doctor_question = next_q
        else:
            doctor_question = input("Enter question: ")

        token_count_doctor = get_token_count()
        middle_time = time.time()

        # Patient answers
        patient_answer, score, rel, faith, human = ctx.patient.patient_ans(doctor_question)
        token_count_patient = get_token_count()
        end_time = time.time()

        doctor_time = middle_time - start_time
        patient_time = end_time - start_time

        # Write to both CSVs (experiment dir and top-level)
        row = [
            row_number,
            doctor_question.replace("\n", ""),
            patient_answer.replace("\n", ""),
            token_count_doctor,
            token_count_patient,
            ctx.resource,
            doctor_time,
            patient_time,
            count_chinese_characters(doctor_question),
            count_chinese_characters(patient_answer),
        ]
        for p in (exp_csv, top_csv):
            with p.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)

    # Conclusion
    conclusion = doctor.conclusion()
    (ctx.directory / "conclusion.txt").write_text(conclusion, encoding="utf-8")

    # Time cost (measured from the last turn)
    time_cost = time.time() - start_time
    (ctx.directory / "time_cost.txt").write_text(str(time_cost), encoding="utf-8")

    # Move token count files
    source_folder = Path("./make_task/token_count")
    destination_folder = ctx.directory / "token_count"
    destination_folder.mkdir(parents=True, exist_ok=True)
    if source_folder.exists():
        for file_path in source_folder.glob("*.txt"):
            shutil.move(str(file_path), str(destination_folder))
            print(f"File {file_path.name} moved to {destination_folder}")


# ====== Quick-start entry point ======
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="PatientAgent — single consultation simulation"
    )
    parser.add_argument(
        "--row", type=int, default=2,
        help="Row number in the Excel sheet (default: 2)"
    )
    parser.add_argument(
        "--sheet", type=str, default="病程记录_首次病程",
        help="Excel sheet name (default: 病程记录_首次病程)"
    )
    parser.add_argument(
        "--col", type=int, default=1,
        help="Column number in the Excel sheet (default: 1)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  PatientAgent — Single Consultation")
    print(f"  Sheet: {args.sheet}  Row: {args.row}  Col: {args.col}")
    print("=" * 60)
    flow(sheet_name=args.sheet, row_number=args.row, col_number=args.col)
