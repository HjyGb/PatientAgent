"""Memory stream: periodically summarize doctor-patient dialogue."""

from pathlib import Path

from Simulated.simulated_patient.api_call import llm_api
from utils import ensure_parent


# Path definitions
MEMORY_FILE = Path("memory_warehouse.txt")
SUMMARY_PROMPT_FILE = Path("Prompt") / "summary_memory.txt"

# Auto-initialize files if missing
MEMORY_FILE.touch(exist_ok=True)
SUMMARY_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
if not SUMMARY_PROMPT_FILE.exists():
    SUMMARY_PROMPT_FILE.write_text("Please summarize the following dialogue: {chatstream}", encoding="utf-8")


def summary(patient_question: str, doctor_answer: str):
    """Periodically call to summarize doctor-patient dialogue memory via LLM."""
    memory_stream = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
    memory_stream += f"Doctor's question: {patient_question}\nPatient's answer: {doctor_answer}\n"

    prompt_template = SUMMARY_PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt_template.format(chatstream=memory_stream)

    messages = [{"role": "user", "content": prompt}]
    memory_summary = llm_api(messages)

    MEMORY_FILE.write_text(memory_summary, encoding="utf-8")
    print("Memory summary updated.")


def memory_store(patient_question: str, doctor_answer: str, turn: int):
    """Record doctor-patient dialogue each turn. Auto-summarize every 10 turns."""
    if turn % 10 == 0:
        summary(patient_question, doctor_answer)
    else:
        chat_pair = f"Doctor's question: {patient_question}\nPatient's answer: {doctor_answer}\n"
        with MEMORY_FILE.open("a", encoding="utf-8") as f:
            f.write(chat_pair)
        print(f"Appended to memory file (turn {turn}).")
