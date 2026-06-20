import { useRecordStore } from '../../stores/record-store';
import EvaluateModal from '../evaluation/EvaluateModal';

export default function EvaluatePanel() {
  const { evaluation, showEvaluationModal, setShowEvaluationModal } = useRecordStore();

  return (
    <div className="bg-white flex flex-col">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">📊 评估结果</h2>
      </div>

      {/* Empty State */}
      {!evaluation ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <div className="text-4xl mb-3">📝</div>
            <p className="text-sm text-[var(--color-text-secondary)]">
              提交诊断后
              <br />
              将展示专业评估结果
            </p>
          </div>
        </div>
      ) : (
        /* Score Summary */
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <ScoreCard
            label="总评"
            score={evaluation.overall_score}
            maxScore={5}
          />
          <ScoreCard
            label="问诊质量"
            score={evaluation.consultation_quality}
            maxScore={5}
          />
          <ScoreCard
            label="诊断准确性"
            score={evaluation.diagnosis_accuracy}
            maxScore={5}
          />
          <button
            onClick={() => setShowEvaluationModal(true)}
            className="w-full py-2 rounded-lg border border-[var(--color-primary)] text-[var(--color-primary)] text-sm font-medium hover:bg-[var(--color-primary-light)] transition-colors"
          >
            查看详细评估
          </button>
        </div>
      )}

      {/* Evaluation Modal */}
      {showEvaluationModal && evaluation && <EvaluateModal />}
    </div>
  );
}

function ScoreCard({ label, score, maxScore }: { label: string; score: number; maxScore: number }) {
  const pct = (score / maxScore) * 100;
  const color =
    pct >= 80 ? 'text-green-600' : pct >= 60 ? 'text-amber-600' : 'text-red-600';
  const bg =
    pct >= 80 ? 'bg-green-100' : pct >= 60 ? 'bg-amber-100' : 'bg-red-100';

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-[var(--color-text-secondary)]">{label}</span>
        <span className={`text-lg font-bold ${color}`}>{score.toFixed(1)}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${bg}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
