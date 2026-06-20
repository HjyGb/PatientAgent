import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useCaseStore } from '../stores/case-store';
import { useAuthStore } from '../stores/auth-store';
import { api } from '../lib/api-client';

export default function InitPage() {
  const navigate = useNavigate();
  const { loadCase, isLoading, error } = useCaseStore();

  const [employeeId, setEmployeeId] = useState(() => localStorage.getItem('pa-employee-id') || '');
  const [department, setDepartment] = useState(() => localStorage.getItem('pa-department') || '急诊科');
  const [caseNumber, setCaseNumber] = useState(() => localStorage.getItem('pa-case-number') || '');

  // Fetch departments
  const { data: deptData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.getDepartments(),
  });
  const departments = deptData?.departments || ['急诊科', '内科', '外科'];

  // Fetch case list
  const { data: caseData } = useQuery({
    queryKey: ['cases', department],
    queryFn: () => api.listCases({ department, page: '1', page_size: '100' }),
  });
  const cases = caseData?.items || [];

  // Persist form to localStorage
  useEffect(() => { localStorage.setItem('pa-employee-id', employeeId); }, [employeeId]);
  useEffect(() => { localStorage.setItem('pa-department', department); }, [department]);
  useEffect(() => { localStorage.setItem('pa-case-number', caseNumber); }, [caseNumber]);

  const canLoad = employeeId.trim() && department && caseNumber.trim();

  const handleLoad = async () => {
    if (!canLoad) return;
    try {
      // Quick-login: get JWT token for this employee ID
      const { access_token, user } = await api.quickLogin(employeeId);
      useAuthStore.getState().login(access_token, user);

      await loadCase(Number(caseNumber));
      navigate('/interview');
    } catch (err: any) {
      // error is shown via store or toast
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] p-4">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-[var(--color-primary)] mb-2">
          🏥 标准化病人模拟系统
        </h1>
        <p className="text-[var(--color-text-secondary)]">Standardized Patient Simulation System</p>
      </div>

      {/* Form Card */}
      <div className="bg-white rounded-xl shadow-sm border border-[var(--color-border)] p-8 w-full max-w-md">
        <div className="space-y-5">
          {/* Employee ID */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
              工号 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              placeholder="请输入工号"
              className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                         text-sm"
            />
          </div>

          {/* Department */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
              科室
            </label>
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                         text-sm bg-white"
            >
              {departments.map((d: string) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Case Number */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
              病例编号 <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={caseNumber}
              onChange={(e) => setCaseNumber(e.target.value)}
              placeholder="请输入病例编号"
              className="w-full px-4 py-2.5 border border-[var(--color-border)] rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                         text-sm"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-2.5 rounded-lg">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleLoad}
            disabled={!canLoad || isLoading}
            className={`w-full py-3 rounded-lg font-medium text-sm transition-all ${
              canLoad && !isLoading
                ? 'bg-[var(--color-primary)] text-white hover:opacity-90 active:scale-[0.98]'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isLoading ? '正在生成...' : '加载病例并进入问诊'}
          </button>
        </div>
      </div>

      {/* Case Quick List */}
      <div className="mt-6 w-full max-w-md">
        <p className="text-xs text-[var(--color-text-secondary)] mb-2">可用病例列表</p>
        <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
          {cases.slice(0, 20).map((c: any) => (
            <button
              key={c.id}
              onClick={() => setCaseNumber(String(c.id))}
              className={`text-left px-3 py-2 rounded-lg text-xs border transition-all ${
                String(caseNumber) === String(c.id)
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-light)] text-[var(--color-primary)]'
                  : 'border-[var(--color-border)] hover:border-gray-300'
              }`}
            >
              <span className="font-medium">#{c.id}</span>{' '}
              <span className="text-[var(--color-text-secondary)]">{c.department}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
