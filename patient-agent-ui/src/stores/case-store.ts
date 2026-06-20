import { create } from 'zustand';
import { useChatStore } from './chat-store';
import { useRecordStore } from './record-store';

interface CaseState {
  sessionId: string | null;
  caseId: number | null;
  department: string;
  chiefComplaint: string;
  isLoading: boolean;
  error: string | null;

  loadCase: (caseId: number) => Promise<void>;
  resetCase: () => void;
}

export const useCaseStore = create<CaseState>((set) => ({
  sessionId: null,
  caseId: null,
  department: '',
  chiefComplaint: '',
  isLoading: false,
  error: null,

  loadCase: async (caseId: number) => {
    set({ isLoading: true, error: null });
    try {
      // Clear previous session data before loading new case
      useChatStore.getState().clearChat();
      useRecordStore.getState().clearRecord();

      const { api } = await import('../lib/api-client');
      const result = await api.loadCase(caseId);
      set({
        sessionId: result.session_id,
        caseId: result.case_id,
        department: result.department,
        chiefComplaint: result.chief_complaint,
        isLoading: false,
      });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
      throw err;
    }
  },

  resetCase: () =>
    set({ sessionId: null, caseId: null, department: '', chiefComplaint: '', error: null }),
}));
