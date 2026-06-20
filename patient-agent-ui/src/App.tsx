import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import InitPage from './pages/InitPage';
import InterviewPage from './pages/InterviewPage';
import ToastContainer from './components/ui/ToastContainer';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/init" element={<InitPage />} />
          <Route path="/interview" element={<InterviewPage />} />
          <Route path="*" element={<Navigate to="/init" replace />} />
        </Routes>
      </BrowserRouter>
      <ToastContainer />
    </QueryClientProvider>
  );
}
