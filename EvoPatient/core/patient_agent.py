"""Patient agent: simulates a patient's behavior in medical dialogue."""

import random
import re
from pathlib import Path

from core.api_call import llm_api, llm_api_stream
from core.agent_evolve import store_patient_qa, agent_evolving_patient
from core.rag.rag import rag_patient
from utils import match_star, match_star_strict, read_prompt


def question_detect(doctor_question: str) -> bool:
    """Return True if the question is too generic; False if it is specific enough to answer."""
    prompt_data = read_prompt()
    prompt = prompt_data["question_general_detect"]
    prompt = prompt.format(question=doctor_question)
    messages = [{"role": "user", "content": prompt}]
    res = llm_api(messages)
    return not ("yes" in res.lower())


def match_requirements(context: str) -> str:
    """Match **...** across lines, return first match; empty string if none."""
    pattern = r"\*\*(.*)\*\*"
    matches = re.findall(pattern, context, flags=re.DOTALL)
    return matches[0] if matches else ""


class Patient:
    def __init__(self, vague_info: str = "", resource: str = "", folder_path: str = "", prompt_data=None):
        self.profile = ""
        self.vague_info = vague_info
        self.resource = resource
        self.directory = Path(folder_path) if folder_path else Path(".")
        self.prompt_data = prompt_data or {}
        self.crisis = ""

        # Ensure the directory for recording dialogue exists
        self.directory.mkdir(parents=True, exist_ok=True)

    def generate_patient_question(self) -> str:
        prompt_tpl = self.prompt_data["patient_question_generator"]
        random_profile_num = random.randint(0, 100)
        profile_path = Path("profile") / "profile_pool" / f"{random_profile_num}.txt"
        self.profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""

        prompt = prompt_tpl.format(profile=self.profile, information=self.vague_info)
        messages = [{"role": "user", "content": prompt}]
        return llm_api(messages)

    def assign_office(self) -> str:
        prompt = self.prompt_data["assign_doctor_office"] + self.prompt_data["vague_resource"]
        messages = [{"role": "user", "content": prompt}]
        office = llm_api(messages)
        print("Department:", office)
        return office

    def patient_ans(self, question: str):
        # Optionally enable generic question detection:
        # not_general_flag = question_detect(question)
        not_general_flag = True

        # Safe default return values
        score = rel = faith = human = 0
        ans = ""

        if not_general_flag:
            prompt_tpl = self.prompt_data["patient_answer_generator"]

            useful_info = rag_patient(
                question,
                self.resource,
                size=120,
                overlap=40,
                top_k=2,
            )

            # Evolution example retrieval (similar Q&A few-shot)
            patient_evolve_csv = Path("dataset") / "patient_evolve.csv"
            patient_evolve_csv.parent.mkdir(parents=True, exist_ok=True)

            patient_evolve_info = agent_evolving_patient(str(patient_evolve_csv), question)
            attention_requirements = ""
            few_shot_example = ""

            if patient_evolve_info:
                lines = []
                for idx, info_dic in enumerate(patient_evolve_info, start=1):
                    doctor_qus = info_dic["question"]
                    patient_answer = info_dic["answer"]
                    rag_info = info_dic["rag_info"]
                    attention_requirements = info_dic.get("requirements", attention_requirements)
                    lines.append(f"{idx}\nQuestion: {doctor_qus}\nMedical info: {rag_info}\nPatient answer: {patient_answer}\n")
                few_shot_example = "".join(lines)
            else:
                few_shot_example = "No examples available."

            if attention_requirements:
                prompt_tpl = (
                    "You are a response generator that mimics the tone of a patient "
                    "without professional medical knowledge.\n"
                    "This patient's role-play requirements: {profile}\n---------\n"
                    "Now a doctor is asking you a question, please answer according to the following requirements: "
                    + attention_requirements
                    + "\nQuestion: {question}.\nMedical information: {information}.\nExample: {example}"
                )

            prompt = prompt_tpl.format(
                profile=self.profile,
                example=few_shot_example,
                question=question,
                information=useful_info,
            )

            messages = [{"role": "user", "content": prompt}]
            ans = llm_api(messages)

            # Quality assessment (store and extract dynamic requirements if score >= threshold)
            score, rel, faith, human = overall_assessment_patient(question, useful_info, ans, self.profile)

            if score >= 3:
                dyn_req_tpl = self.prompt_data["dynamic_requirements"]
                dyn_prompt = dyn_req_tpl.format(question=question)
                dyn_msg = [{"role": "user", "content": dyn_prompt}]

                # Robustly extract **...** requirements (retry up to 3 times)
                for _ in range(3):
                    requirements_raw = llm_api(dyn_msg)
                    requirements = match_requirements(requirements_raw)
                    if requirements:
                        store_patient_qa(str(patient_evolve_csv), question, useful_info, ans, requirements)
                        break
        else:
            ans = "Doctor, this question is too vague, or I don't quite understand. Please ask something more specific. I can't understand medical terms, but I'm willing to do examinations."

        # Append dialogue to file
        dq_path = self.directory / "doctor_question.txt"
        with dq_path.open("a", encoding="utf-8") as f:
            f.write("--- dialog ---\n")
            f.write(f"doctor question: {question}\n")
            f.write(f"patient answer: {ans}\n")

        return ans, score, rel, faith, human

    def patient_ans_stream(self, question: str):
        """Streaming version of patient_ans.

        Yields tokens as they arrive from the LLM. The StopIteration value
        is a tuple: (full_answer, score, rel, faith, human).

        Usage:
            gen = patient.patient_ans_stream(question)
            for token in gen:
                send_to_client(token)
            # After loop, full result is in gen's StopIteration.value
        """
        not_general_flag = True
        score = rel = faith = human = 0
        ans = ""

        if not_general_flag:
            prompt_tpl = self.prompt_data["patient_answer_generator"]

            useful_info = rag_patient(question, self.resource, size=120, overlap=40, top_k=2)

            patient_evolve_csv = Path("dataset") / "patient_evolve.csv"
            patient_evolve_csv.parent.mkdir(parents=True, exist_ok=True)
            patient_evolve_info = agent_evolving_patient(str(patient_evolve_csv), question)

            attention_requirements = ""
            few_shot_example = ""
            if patient_evolve_info:
                lines = []
                for idx, info_dic in enumerate(patient_evolve_info, start=1):
                    doctor_qus = info_dic["question"]
                    patient_answer = info_dic["answer"]
                    rag_info = info_dic["rag_info"]
                    attention_requirements = info_dic.get("requirements", attention_requirements)
                    lines.append(
                        f"{idx}\nQuestion: {doctor_qus}\nMedical info: {rag_info}\nPatient answer: {patient_answer}\n"
                    )
                few_shot_example = "".join(lines)
            else:
                few_shot_example = "No examples available."

            if attention_requirements:
                prompt_tpl = (
                    "You are a response generator that mimics the tone of a patient "
                    "without professional medical knowledge.\n"
                    "This patient's role-play requirements: {profile}\n---------\n"
                    "Now a doctor is asking you a question, please answer according to the following requirements: "
                    + attention_requirements
                    + "\nQuestion: {question}.\nMedical information: {information}.\nExample: {example}"
                )

            prompt = prompt_tpl.format(
                profile=self.profile,
                example=few_shot_example,
                question=question,
                information=useful_info,
            )
            messages = [{"role": "user", "content": prompt}]

            # Use the streaming LLM call
            gen = llm_api_stream(messages)
            ans = ""
            for token in gen:
                ans += token
                yield token
            # After exhaustion, ans holds the full text from StopIteration.value

            # Quality assessment (non-streaming, runs after stream completes)
            score, rel, faith, human = overall_assessment_patient(question, useful_info, ans, self.profile)

            # Evolution storage (if high quality)
            if score >= 3:
                dyn_req_tpl = self.prompt_data["dynamic_requirements"]
                dyn_prompt = dyn_req_tpl.format(question=question)
                dyn_msg = [{"role": "user", "content": dyn_prompt}]
                for _ in range(3):
                    requirements_raw = llm_api(dyn_msg)
                    requirements = match_requirements(requirements_raw)
                    if requirements:
                        store_patient_qa(str(patient_evolve_csv), question, useful_info, ans, requirements)
                        break

            # Append dialogue to file
            dq_path = self.directory / "doctor_question.txt"
            with dq_path.open("a", encoding="utf-8") as f:
                f.write("--- dialog ---\n")
                f.write(f"doctor question: {question}\n")
                f.write(f"patient answer: {ans}\n")

            return ans, score, rel, faith, human
        else:
            # Generic question fallback
            fallback = "Doctor, this question is too vague, or I don't quite understand. Please ask something more specific."
            for char in fallback:
                yield char
            return fallback, 0, 0, 0, 0

    def patient_crisis_ans(self, doctor_ans: str) -> str:
        prompt = self.prompt_data["patient_crisis_answer"].format(
            profile=self.profile, information=self.resource, crisis=self.crisis, doctor_answer=doctor_ans
        )
        messages = [{"role": "user", "content": prompt}]
        return llm_api(messages)

    def crisis_begin(self) -> str:
        prompt_tpl = self.prompt_data["patient_crisis_generator"]
        resource = self.prompt_data["resource"]
        prompt = prompt_tpl.format(information=resource)

        messages = [{"role": "user", "content": prompt}]
        patient_crisis = llm_api(messages)
        self.crisis = patient_crisis
        return patient_crisis


# Lazy import to avoid circular dependency
def overall_assessment_patient(question, useful_info, ans, profile):
    from core.overall_assessment import overall_assessment_patient as _assess
    return _assess(question, useful_info, ans, profile)
