"""Agent evolution: store and retrieve similar Q&A pairs for few-shot learning."""

import csv
import json
from pathlib import Path

import numpy as np

from Simulated.simulated_patient.api_call import llm_api, get_text_embedding
from utils import read_prompt


# ====== CSV encoding helper ======
# The original CSV files may be GBK-encoded (created on Chinese Windows).
# Try UTF-8 first, fall back to GBK.

_CSV_ENCODINGS = ["utf-8", "gbk"]


def _open_csv(path: Path, mode: str):
    """Open a CSV file, trying UTF-8 then GBK encoding for read modes."""
    if "r" in mode:
        # Read the whole file to verify encoding before returning the handle
        raw = path.read_bytes()
        for enc in _CSV_ENCODINGS:
            try:
                raw.decode(enc)
                return open(str(path), mode, newline="", encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise UnicodeDecodeError(f"Cannot decode {path} with any known encoding")
    # Write: always use UTF-8
    return open(str(path), mode, newline="", encoding="utf-8")


# ====== CSV I/O ======

def write_to_csv(
    directory,
    embedding_res,
    question,
    rag_info,
    answer,
    requirements,
    write_header=False,
):
    directory = Path(directory)
    embedding_res_str = ",".join(map(str, embedding_res))
    data_to_write = [embedding_res_str, question, rag_info, answer, requirements]

    if directory.is_file() and not write_header:
        with _open_csv(directory, "r") as file:
            reader = csv.reader(file)
            _ = next(reader, None)
            for row in reader:
                if row and row[0] == embedding_res_str:
                    return
    else:
        with _open_csv(directory, "w") as file:
            writer = csv.writer(file)
            writer.writerow(["qus_embedding", "question", "rag_info", "answer", "requirements"])

    with _open_csv(directory, "a") as file:
        writer = csv.writer(file)
        writer.writerow(data_to_write)


def write_csv(directory, qus_1, emb_1, emb_2, ans_1, rag_1, qus_2, ans_2, rag_2, write_header=False):
    directory = Path(directory)
    embedding_res_str1 = ",".join(map(str, emb_1))
    embedding_res_str2 = ",".join(map(str, emb_2))
    data_to_write = [qus_1, embedding_res_str1, rag_1, ans_1, embedding_res_str2, qus_2, ans_2, rag_2]

    if directory.is_file() and not write_header:
        with _open_csv(directory, "r") as file:
            reader = csv.reader(file)
            _ = next(reader, None)
            for row in reader:
                if row and row[0] == embedding_res_str1:
                    return
    else:
        with _open_csv(directory, "w") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["question1", "qus_embedding", "rag_info1", "answer1", "qus2_embedding", "question2", "answer2", "rag_info2"]
            )

    with _open_csv(directory, "a") as file:
        writer = csv.writer(file)
        writer.writerow(data_to_write)


# ====== Embedding read helpers ======

def read_qus_embedding_from_csv(directory):
    directory = Path(directory)
    qus_embedding_list = []
    with _open_csv(directory, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            v = row.get("qus_embedding")
            if v:
                qus_embedding_list.append(v)
    return qus_embedding_list


def read_qus_embedding_doctor(directory):
    directory = Path(directory)
    qus1_embedding_list, qus2_embedding_list = [], []
    with _open_csv(directory, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            v1 = row.get("qus_embedding")
            if v1:
                qus1_embedding_list.append(v1)
            v2 = row.get("qus2_embedding")
            if v2:
                qus2_embedding_list.append(v2)
    return qus1_embedding_list, qus2_embedding_list


# ====== Similarity ======

def get_cosine_similarity(embeddingi, embeddingj):
    embeddingi = np.array(embeddingi)
    embeddingj = np.array(embeddingj)
    if embeddingi.shape != embeddingj.shape:
        return 0.0  # dimension mismatch (e.g. old 1536d vs new 1024d), skip
    denom = np.linalg.norm(embeddingi) * np.linalg.norm(embeddingj)
    if denom == 0:
        return 0.0
    return embeddingi.dot(embeddingj) / denom


# ====== Quality check ======

def quality_check(question, rag_info, answer):
    prompt_data = read_prompt()
    prompt = prompt_data["quality_check_evolve"]
    prompt = prompt.format(question=question, infomation=rag_info, answer=answer)
    messages = [{"role": "user", "content": prompt}]
    return llm_api(messages)


# ====== Store Q&A for evolution ======

def store_patient_qa(directory, question, rag_info, answer, requirements):
    embedding_res = get_text_embedding(question)
    qus_embedding_list = read_qus_embedding_from_csv(directory)
    evolve_flag = True
    for stored_qus_embedding in qus_embedding_list:
        stored_qus_embedding = [float(item.strip()) for item in stored_qus_embedding.split(",")]
        if get_cosine_similarity(stored_qus_embedding, embedding_res) > 0.95:
            print("Similar Q&A already exists, skipping evolution.")
            evolve_flag = False
            break
    if evolve_flag:
        write_to_csv(directory, embedding_res, question, rag_info, answer, requirements)


def store_doctor_qa(directory, record):
    qus_1, ans_1, rag_1, qus_2, ans_2, rag_2 = record
    qus_1_emb = get_text_embedding(qus_1)
    qus_2_emb = get_text_embedding(qus_2)
    qus1_embedding_list, qus2_embedding_list = read_qus_embedding_doctor(directory)
    evolve_flag = True
    for stored_qus1_embedding, stored_qus2_embedding in zip(qus1_embedding_list, qus2_embedding_list):
        stored_qus1_embedding = [float(item.strip()) for item in stored_qus1_embedding.split(",")]
        stored_qus2_embedding = [float(item.strip()) for item in stored_qus2_embedding.split(",")]
        if get_cosine_similarity(stored_qus1_embedding, qus_1_emb) > 0.8 and get_cosine_similarity(
            stored_qus2_embedding, qus_2_emb
        ) > 0.8:
            print("Similar Q&A already exists, skipping evolution.")
            evolve_flag = False
            break
    if evolve_flag:
        write_csv(directory, qus_1, qus_1_emb, qus_2_emb, ans_1, rag_1, qus_2, ans_2, rag_2)
        print(f"Stored {qus_1} + {qus_2}")


# ====== Retrieval for few-shot ======

def get_most_related_qus(rank_dic):
    sorted_items = sorted(rank_dic.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_items) > 2:
        return [item[0] for item in sorted_items[:2]]
    elif 0 < len(sorted_items) <= 2:
        return [item[0] for item in sorted_items[:1]]
    else:
        return []


def get_evolve_info(related_qus_list, directory):
    directory = Path(directory)
    matched_rows_data = []
    with _open_csv(directory, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["qus_embedding"] in related_qus_list:
                matched_row = {header: row[header] for header in reader.fieldnames}
                matched_rows_data.append(matched_row)
    return matched_rows_data


def get_consistency(directory, qus_embedding):
    qus_embedding_list = read_qus_embedding_from_csv(directory)
    rank_dic = {}
    for stored_embedding_str in qus_embedding_list:
        stored_embedding_list = [float(item.strip()) for item in stored_embedding_str.split(",")]
        task_question_alignment = get_cosine_similarity(stored_embedding_list, qus_embedding)
        if task_question_alignment > 0.9:
            rank_dic[stored_embedding_str] = task_question_alignment
    return get_most_related_qus(rank_dic)


def get_consistency_doctor(directory, qus_embedding, ans_embedding):
    qus1_embedding_list, qus2_embedding_list = read_qus_embedding_doctor(directory)
    rank_dic = {}
    for qus_emb, ans_emb in zip(qus1_embedding_list, qus2_embedding_list):
        qus1_emb_list = [float(item.strip()) for item in qus_emb.split(",")]
        qus2_emb_list = [float(item.strip()) for item in ans_emb.split(",")]
        task_question_alignment = get_cosine_similarity(qus1_emb_list, qus_embedding)
        if task_question_alignment > 0.25:
            rank_dic[qus_emb] = task_question_alignment
    return get_most_related_qus(rank_dic)


# ====== Agent evolution entry points ======

def agent_evolving_patient(directory, question):
    qus_embedding = get_text_embedding(question)
    related_qus_list = get_consistency(directory, qus_embedding)
    if related_qus_list:
        return get_evolve_info(related_qus_list, directory)
    else:
        return {}


def agent_evolving_doctor(directory, record):
    qus_embedding = get_text_embedding(record[0])
    ans_embedding = get_text_embedding(record[1])
    related_qus_list = get_consistency_doctor(directory, qus_embedding, ans_embedding)
    if related_qus_list:
        return get_evolve_info(related_qus_list, directory)
    else:
        return {}
