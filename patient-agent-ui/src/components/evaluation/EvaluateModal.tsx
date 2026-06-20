import { useRecordStore } from '../../stores/record-store';

export default function EvaluateModal() {
  const { evaluation, setShowEvaluationModal } = useRecordStore();
  if (!evaluation) return null;

  const dims = evaluation.diagnosis_dimensions || {};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={() => setShowEvaluationModal(false)}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto m-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-lg font-bold text-[var(--color-text)]">📊 诊断评估报告</h2>
          <button
            onClick={() => setShowEvaluationModal(false)}
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)] text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Total Score */}
          <div className="text-center">
            <div className="text-5xl font-bold text-[var(--color-primary)]">
              {evaluation.overall_score?.toFixed(1)}
            </div>
            <div className="text-sm text-[var(--color-text-secondary)] mt-1">综合评分 / 5.0</div>
          </div>

          {/* Dimension Scores */}
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">评分维度</h3>
            <div className="space-y-3">
              {Object.entries(dims).map(([key, dim]: [string, any]) => (
                <div key={key} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-[var(--color-text)]">{key}</span>
                    <span className="text-sm font-bold text-[var(--color-primary)]">
                      {dim.score}/{dim.max_score}
                    </span>
                  </div>
                  {dim.reason && (
                    <p className="text-xs text-[var(--color-text-secondary)]">{dim.reason}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Teacher Comment */}
          {evaluation.teacher_comment && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text)] mb-2">教师评语</h3>
              <div className="bg-blue-50 border-l-4 border-[var(--color-primary)] rounded-r-lg p-4">
                <p className="text-sm text-[var(--color-text)] leading-relaxed">
                  {evaluation.teacher_comment}
                </p>
              </div>
            </div>
          )}

          {/* Standard Diagnosis */}
          {evaluation.standard_diagnosis && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text)] mb-2">标准诊断参考</h3>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-800 leading-relaxed whitespace-pre-wrap">
                  {evaluation.standard_diagnosis}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
