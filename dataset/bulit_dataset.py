"""Dataset builder: convert Excel patient data to JSON."""

import json
from pathlib import Path

import pandas as pd


def load_sheets(excel_path: Path, sheets):
    """Safely read specified sheets (skip missing ones), return {sheet_name: DataFrame}."""
    existing = {}
    for name in sheets:
        try:
            df = pd.read_excel(excel_path, sheet_name=name)
            existing[name] = df
        except Exception as e:
            print(f"Skipped sheet {name}: {e}")
    return existing


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert NaN to None for JSON serialization."""
    return df.where(pd.notnull(df), None)


def deduplicate_records(records):
    """Deduplicate records by content (order-insensitive), return unique list."""
    seen = set()
    unique = []
    for rec in records:
        key = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(rec)
    return unique


def build_patient_dict(excel_path: Path, sheets):
    """Aggregate cross-sheet data by Patient-SN, deduplicate and remove Patient-SN field."""
    sheet_map = load_sheets(excel_path, sheets)
    patient_map = {}

    for sheet_name, df in sheet_map.items():
        df = normalize_df(df)
        if "Patient-SN" not in df.columns:
            print(f"Sheet {sheet_name} is missing column 'Patient-SN', skipped.")
            continue

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            patient_id = row_dict.get("Patient-SN")
            if patient_id is None:
                continue

            # Remove Patient-SN field, keep only other info
            record = {k: v for k, v in row_dict.items() if k != "Patient-SN"}

            patient_map.setdefault(patient_id, []).append(record)

    # Deduplicate records for each patient
    for pid, records in patient_map.items():
        patient_map[pid] = deduplicate_records(records)

    return patient_map


def main():
    excel_file = Path("../dataset/patient_text.xlsx")
    output_json = Path("patient_data.json")

    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file.resolve()}")

    sheets = ["患者基本信息", "检查_MRI检查", "病程记录_首次病程", "病理_全部病理", "专科检查_专科检查"]

    patient_dict = build_patient_dict(excel_file, sheets)

    output_json.write_text(
        json.dumps(patient_dict, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    print(f"JSON file generated: {output_json.resolve()}")


if __name__ == "__main__":
    main()
