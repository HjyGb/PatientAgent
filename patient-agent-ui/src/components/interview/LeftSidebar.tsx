import { useQuery } from '@tanstack/react-query';
import { useCaseStore } from '../../stores/case-store';
import { api } from '../../lib/api-client';

export default function LeftSidebar() {
  const { caseId, department } = useCaseStore();

  // Fetch session history from API
  const { data: historyData, isLoading } = useQuery({
    queryKey: ['session-history'],
    queryFn: () => api.getSessionHistory(1, 10),
    refetchInterval: false,
  });

  const sessions = historyData?.items || [];

  return (
    <aside className="bg-white border-r border-[var(--color-border)] flex flex-col overflow-hidden">
      {/* Patient Avatar Card */}
      <div className="p-4 border-b border-[var(--color-border)]">
        <div className="flex flex-col items-center">
          <div className="w-20 h-20 rounded-full bg-[var(--color-primary-light)] flex items-center justify-center text-3xl mb-3">
            🤒
          </div>
          <p className="text-sm font-medium text-[var(--color-text)]">标准化病人</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            {department} · 病例 #{caseId}
          </p>
        </div>
      </div>

      {/* History Records */}
      <div className="flex-1 overflow-y-auto p-3">
        <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide mb-3">
          历史问诊记录
        </p>

        {isLoading ? (
          <div className="text-xs text-[var(--color-text-secondary)] text-center py-4">
            加载中...
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-xs text-[var(--color-text-secondary)] text-center py-8">
            暂无历史记录
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((s: any) => (
              <div
                key={s.session_id}
                className="bg-gray-50 rounded-lg p-3 text-xs hover:bg-gray-100 transition-colors cursor-default"
              >
                <div className="font-medium text-[var(--color-text)] truncate">
                  {s.chief_complaint || `病例 #${s.case_id}`}
                </div>
                <div className="flex items-center justify-between mt-1 text-[var(--color-text-secondary)]">
                  <span>{s.department}</span>
                  <StatusBadge status={s.status} />
                </div>
                <div className="text-[10px] text-[var(--color-text-secondary)] mt-1">
                  {s.turn_count}/{s.max_turns || 12} 轮 · {formatDate(s.created_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-700',
    ended: 'bg-gray-100 text-gray-500',
    diagnosed: 'bg-blue-100 text-blue-700',
    evaluated: 'bg-purple-100 text-purple-700',
  };
  const labels: Record<string, string> = {
    active: '进行中',
    ended: '已结束',
    diagnosed: '已诊断',
    evaluated: '已评估',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${colors[status] || 'bg-gray-100'}`}>
      {labels[status] || status}
    </span>
  );
}

function formatDate(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  } catch {
    return iso.slice(0, 10);
  }
}
