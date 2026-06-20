import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'doctor' | 'patient' | 'system';
  content: string;
  streaming?: boolean;
  scores?: { overall: number; relevance: number; faithfulness: number; robustness: number } | null;
  confirmedInfo?: string[];
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  autoSend: boolean;
  turn: number;
  maxTurns: number;
  sessionActive: boolean;

  addMessage: (msg: Omit<ChatMessage, 'id'>) => string;
  appendToken: (id: string, token: string) => void;
  finalizeMessage: (id: string, content: string, scores?: any) => void;
  setLoading: (val: boolean) => void;
  setAutoSend: (val: boolean) => void;
  startSession: (chiefComplaint: string) => void;
  clearChat: () => void;
}

let _msgId = 0;
const nextId = () => `msg-${++_msgId}`;

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  autoSend: false,
  turn: 0,
  maxTurns: 12,
  sessionActive: false,

  addMessage: (msg) => {
    const id = nextId();
    set((s) => ({ messages: [...s.messages, { ...msg, id }] }));
    return id;
  },

  appendToken: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    })),

  finalizeMessage: (id, content, scores) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content, streaming: false, scores } : m
      ),
    })),

  setLoading: (val) => set({ isLoading: val }),
  setAutoSend: (val) => set({ autoSend: val }),

  startSession: (chiefComplaint) =>
    set({
      messages: [
        { id: nextId(), role: 'system', content: '🏥 问诊开始 — 请根据患者主诉进行问诊' },
        { id: nextId(), role: 'patient', content: chiefComplaint },
      ],
      turn: 0,
      sessionActive: true,
    }),

  clearChat: () =>
    set({
      messages: [],
      isLoading: false,
      turn: 0,
      sessionActive: false,
    }),
}));
