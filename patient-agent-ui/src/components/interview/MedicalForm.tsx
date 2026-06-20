import { useState, useEffect } from 'react';
import { useRecordStore } from '../../stores/record-store';
import { useChatStore } from '../../stores/chat-store';
import { toast } from '../../stores/toast-store';
import { api } from '../../lib/api-client';
import { useCaseStore } from '../../stores/case-store';

export default function MedicalForm() {
  const { diagnosisDraft, saveDraft, setEvaluation } = useRecordStore();
  const { sessionActive } = useChatStore();
  const sessionId = useCaseStore((s) => s.sessionId);

  const [chiefComplaint, setChiefComplaint] = useState(diagnosisDraft?.chiefComplaint || '');
  const [presentIllness, setPresentIllness] = useState(diagnosisDraft?.presentIllness || '');
  const [diagnosis, setDiagnosis] = useState(diagnosisDraft?.diagnosis || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when session changes (new case loaded)
  useEffect(() => {
    setChiefComplaint('');
    setPresentIllness('');
    setDiagnosis('');
  }, [sessionId]);

  // Auto-save draft (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (chiefComplaint || presentIllness || diagnosis) {
        saveDraft({ chiefComplaint, presentIllness, diagnosis });
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [chiefComplaint, presentIllness, diagnosis]);

  const canSubmit = chiefComplaint.trim() && diagnosis.trim();

  const handleSubmit = async () => {
    if (!canSubmit || !sessionId) return;
    setIsSubmitting(true);
    try {
      await api.submitDiagnosis(sessionId, {
        primary_diagnosis: diagnosis,
        evidence: presentIllness + '\n主诉：' + chiefComplaint,
      });
      // Fetch evaluation
      const evalResult = await api.getEvaluation(sessionId);
      setEvaluation(evalResult);
    } catch (err: any) {
      toast.error('提交失败：' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white border-r border-[var(--color-border)] flex flex-col">
      {/* Form Header */}
      <div className="px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">📋 病历记录</h2>
      </div>

      {/* Form Fields */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Chief Complaint */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
            主诉 <span className="text-red-400">*</span>
          </label>
          <textarea
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            placeholder="如：右下后牙疼痛3天"
            rows={2}
            disabled={!sessionActive}
            className="w-full px-3 py-2 border border-[var(--color-border)] rounded-lg text-sm
                       focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                       resize-none disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>

        {/* Present Illness */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
            现病史 <span className="text-red-400">*</span>
          </label>
          <textarea
            value={presentIllness}
            onChange={(e) => setPresentIllness(e.target.value)}
            placeholder="请根据问诊内容填写现病史..."
            rows={6}
            disabled={!sessionActive}
            className="w-full px-3 py-2 border border-[var(--color-border)] rounded-lg text-sm
                       focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                       resize-none disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>

        {/* Diagnosis */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
            诊断结果 <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={diagnosis}
            onChange={(e) => setDiagnosis(e.target.value)}
            placeholder="如：36牙慢性根尖周炎"
            disabled={!sessionActive}
            className="w-full px-3 py-2 border border-[var(--color-border)] rounded-lg text-sm
                       focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                       disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>
      </div>

      {/* Submit Button */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit || isSubmitting || !sessionActive}
          className={`w-full py-2.5 rounded-lg font-medium text-sm transition-all ${
            canSubmit && !isSubmitting && sessionActive
              ? 'bg-[var(--color-primary)] text-white hover:opacity-90 active:scale-[0.98]'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isSubmitting ? '正在评估...' : '提交诊断'}
        </button>
        <p className="text-[10px] text-[var(--color-text-secondary)] text-center mt-2">
          主诉和诊断结果不能为空 · 草稿自动保存
        </p>
      </div>
    </div>
  );
}
