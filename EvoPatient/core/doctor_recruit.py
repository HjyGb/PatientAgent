"""Recursive doctor recruitment controller."""

import re
from typing import List, Dict, Any, Optional

from core.api_call import llm_api
from utils import match_star, split_string


class Recruit:
    """Recursive doctor recruitment controller.

    - llm_api is provided by the external api_call module; no keys are stored here.
    - Layer keys are normalized to int to avoid str/int comparison issues.
    """

    def __init__(
        self,
        parent_patient: Any,
        office: str = "",
        doctor: Optional[Any] = None,
        main_complaint: Optional[str] = None,
        directory: Optional[str] = None,
        prompt_data: Optional[Dict[str, Any]] = None,
    ):
        self.parent = parent_patient
        self.patient = parent_patient  # Alias for downstream compatibility
        self.prompt_data = prompt_data or {}
        self.office = office or ""
        self.doctor = doctor  # Doctor class or factory
        self.sub_doctor: List[Any] = []

        # Runtime context
        self.main_complaint = main_complaint or ""
        self.summary = ""
        self.dialog_history = ""
        self.dialog_turn = 0
        self.directory = directory or "."

        # Layer -> department list; use int as layer key
        self.doctor_office: Dict[int, List[str]] = {1: [self.office]}
        self.available_office: List[str] = []

    def chat(self):
        pass

    def discussion(self, doctor_list: List[str]):
        pass

    def report(self):
        pass

    def bus(self):
        """Dispatch discussion by current max layer (placeholder)."""
        if not self.doctor_office:
            return
        max_layer = max(self.doctor_office.keys())
        sub_doctor_list = self.doctor_office.get(max_layer, [])
        self.discussion(sub_doctor_list)

    def star(self):
        pass

    def ring(self):
        pass

    def tree(self):
        pass

    def recruit(self, layer: int, office: str):
        """Recruitment logic:
        - Query recommended sub-departments via prompt (returned as ##...##).
        - If result is not empty, add to layer mapping and recurse.
        - After completion, instantiate doctor and run first round of questioning.
        """
        while True:
            prompt_tpl = self.prompt_data.get("recruit", "")
            prompt = prompt_tpl.format(
                office, self.main_complaint, self.summary, self.dialog_history, self.dialog_turn
            )
            messages = [{"role": "user", "content": prompt}]
            res = llm_api(messages)

            # Parse department string from ##...##, may contain multiple comma-separated values
            parsed = match_star(res, "#")
            new_offices = split_string(parsed) if parsed else []

            if not new_offices or (len(new_offices) == 1 and new_offices[0] == "NO"):
                break

            # Record to layer structure
            self.doctor_office.setdefault(layer, [])
            for off in new_offices:
                if off and off not in self.doctor_office[layer]:
                    self.doctor_office[layer].append(off)

            # Recursively explore next layer
            for sub_off in new_offices:
                self.recruit(layer + 1, sub_off)

            # Break out of while to avoid infinite loop; adjust if repeated recruitment is needed
            break

        # Instantiate and run first round of questioning (requires external doctor class/factory)
        if not self.doctor:
            return

        new_office = office or (new_offices[0] if new_offices else self.office)
        new_doctor = self.doctor(
            self.patient,
            new_office,
            main_complaint=self.main_complaint,
            directory=self.directory,
            prompt_data=self.prompt_data,
        )

        # First round: doctor asks, patient answers
        doctor_question = new_doctor.doctor_qus(new_doctor.main_complaint, 0, 0, 0, 0)
        patient_answer = self.patient.patient_ans(doctor_question)
        # patient.patient_ans may return tuple or str; handle both
        if isinstance(patient_answer, (list, tuple)):
            new_doctor.new_patient_answer = patient_answer[0]
        else:
            new_doctor.new_patient_answer = patient_answer

        self.sub_doctor.append(new_doctor)
        print(f"Recruited {new_office} doctor")
