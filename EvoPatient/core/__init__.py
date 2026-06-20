"""PatientAgent core package — shared agent logic for all entry points.

Re-exports the key classes and functions so consumers can do:
    from core import Patient, Doctor, SessionContext, init_session
"""

from core.patient_agent import Patient
from core.doctor_agent import Doctor
from core.doctor_recruit import Recruit
from core.vagueness import get_vague_patient_info
from core.overall_assessment import overall_assessment_patient, overall_assessment_doctor
from core.agent_evolve import (
    store_patient_qa,
    store_doctor_qa,
    agent_evolving_patient,
    agent_evolving_doctor,
)
from core.rag.rag import rag_patient, clear_vector_cache
