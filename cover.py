"""Cover generation flow — generates a medical cover page and embeds the chief complaint."""

import csv
import json
import os
import re
from pathlib import Path

# Load .env BEFORE any project imports that may check env vars at module level
from dotenv import load_dotenv
load_dotenv()

from Simulated.simulated_patient.api_call import llm_api
from Simulated.simulated_patient.agent_evolve import get_text_embedding
from simulateflow import init_session
from utils import ensure_parent


# ====== Cover flow ======
def cover(sheet_name: str = "病程记录_首次病程", row_number: int = 6, col_number: int = 1):
    ctx = init_session(sheet_name, row_number, col_number, output_dir="pool")

    # Generate cover
    prompt = ctx.prompt_data["cover"].format(ctx.office, ctx.resource)
    messages = [{"role": "user", "content": prompt}]
    response = llm_api(messages)
    print(response)

    # Extract possible multiple matches from cover
    matched = re.findall(r"\*\*(.*?)\*\*", response, flags=re.DOTALL)

    # Embed chief complaint and write to pool CSV
    emb = get_text_embedding(ctx.main_complaint)

    pool_csv = Path("dataset/pool.csv")
    ensure_parent(pool_csv)
    new_file = not pool_csv.exists()
    with pool_csv.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["main_complaint", "embedding_main_complaint", "question"])
        writer.writerow([
            ctx.main_complaint,
            json.dumps(emb, ensure_ascii=False),
            json.dumps(matched, ensure_ascii=False),
        ])


def cache() -> int:
    """Read/initialize the row number from case_cache.txt."""
    cache_path = Path("./make_task/case_cache.txt")
    ensure_parent(cache_path)
    if not cache_path.exists():
        cache_path.write_text("0", encoding="utf-8")
        return 0
    txt = cache_path.read_text(encoding="utf-8").strip()
    return int(txt) if txt.isdigit() else 0


def write_cache(value: int):
    cache_path = Path("./make_task/case_cache.txt")
    ensure_parent(cache_path)
    cache_path.write_text(str(value), encoding="utf-8")


if __name__ == "__main__":
    col_number = 1
    sheet_name = "病程记录_首次病程"

    row_number = cache()
    while row_number <= 1300:
        row_number += 1
        cover(sheet_name, row_number, col_number)
        write_cache(row_number)
