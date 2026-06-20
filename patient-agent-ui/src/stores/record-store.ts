import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface DiagnosisDraft {
  chiefComplaint: string;
  presentIllness: string;
  diagnosis: string;
}

interface EvaluationDetail {
  evaluation_id: string;
  overall_score: number;
  consultation_quality: number;
  diagnosis_accuracy: number;
  consultation_dimensions: Record<string, { score: number; max_score: number; reason: string }>;
  diagnosis_dimensions: Record<string, { score: number; max_score: number; reason: string }>;
  teacher_comment: string;
  standard_diagnosis: string;
  history_summary: Record<string, string>;
}

interface RecordState {
  diagnosisDraft: DiagnosisDraft | null;
  evaluation: EvaluationDetail | null;
  showEvaluationModal: boolean;

  saveDraft: (draft: DiagnosisDraft) => void;
  setEvaluation: (evaluation: EvaluationDetail) => void;
  setShowEvaluationModal: (show: boolean) => void;
  clearRecord: () => void;
}

export const useRecordStore = create<RecordState>()(
  persist(
    (set) => ({
      diagnosisDraft: null,
      evaluation: null,
      showEvaluationModal: false,

      saveDraft: (draft) => set({ diagnosisDraft: draft }),
      setEvaluation: (evaluation) => set({ evaluation, showEvaluationModal: true }),
      setShowEvaluationModal: (show) => set({ showEvaluationModal: show }),
      clearRecord: () =>
        set({ diagnosisDraft: null, evaluation: null, showEvaluationModal: false }),
    }),
    {
      name: 'patient-agent-record',
      partialize: (state) => ({ diagnosisDraft: state.diagnosisDraft }),
    }
  )
);
