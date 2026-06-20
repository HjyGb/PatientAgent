import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCaseStore } from '../stores/case-store';
import { useChatStore } from '../stores/chat-store';
import LeftSidebar from '../components/interview/LeftSidebar';
import ChatPanel from '../components/interview/ChatPanel';
import MedicalForm from '../components/interview/MedicalForm';
import EvaluatePanel from '../components/interview/EvaluatePanel';

export default function InterviewPage() {
  const navigate = useNavigate();
  const { sessionId, caseId, department, chiefComplaint } = useCaseStore();
  const { startSession, sessionActive } = useChatStore();

  // Redirect if no session
  useEffect(() => {
    if (!sessionId || !caseId) {
      navigate('/init', { replace: true });
      return;
    }
    if (!sessionActive) {
      startSession(chiefComplaint);
    }
  }, [sessionId, caseId]);

  if (!sessionId) return null;

  return (
    <div className="h-screen flex flex-col bg-[var(--color-bg)]">
      {/* Top Header Bar */}
      <header className="h-14 bg-white border-b border-[var(--color-border)] flex items-center px-6 shrink-0">
        <h1 className="text-lg font-bold text-[var(--color-primary)] mr-6">
          🏥 标准化病人模拟系统
        </h1>
        <div className="flex items-center gap-4 text-sm text-[var(--color-text-secondary)]">
          <span>病例 #{caseId}</span>
          <span>|</span>
          <span>{department}</span>
          <span>|</span>
          <TurnCounter />
        </div>
        <button
          onClick={() => navigate('/init')}
          className="ml-auto text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          ← 返回首页
        </button>
      </header>

      {/* 4-Column Grid Body */}
      <div className="flex-1 grid gap-0 overflow-hidden" style={{
        gridTemplateColumns: '1fr 3fr 2fr 2fr',
      }}>
        {/* Col 1: Left Sidebar */}
        <LeftSidebar />

        {/* Col 2: Chat Panel */}
        <ChatPanel />

        {/* Col 3: Medical Form */}
        <MedicalForm />

        {/* Col 4: Evaluation */}
        <EvaluatePanel />
      </div>
    </div>
  );
}

function TurnCounter() {
  const { turn, maxTurns } = useChatStore();
  return <span>轮次 {turn}/{maxTurns}</span>;
}
