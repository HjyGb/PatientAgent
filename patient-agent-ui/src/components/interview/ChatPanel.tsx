import { useState, useRef, useEffect, useCallback } from 'react';
import { useChatStore } from '../../stores/chat-store';
import { useCaseStore } from '../../stores/case-store';
import { toast } from '../../stores/toast-store';
import { api } from '../../lib/api-client';

export default function ChatPanel() {
  const { messages, isLoading, turn, maxTurns, sessionActive, addMessage, appendToken, finalizeMessage, setLoading } =
    useChatStore();
  const sessionId = useCaseStore((s) => s.sessionId);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sendingRef = useRef(false); // debounce guard

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input after loading completes
  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus();
    }
  }, [isLoading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading || !sessionId || sendingRef.current) return;

    // Debounce guard: prevent double-send within 300ms
    sendingRef.current = true;
    setTimeout(() => { sendingRef.current = false; }, 300);

    setInput('');
    setLoading(true);

    // Add doctor message
    addMessage({ role: 'doctor', content: text });

    // Add placeholder patient message for streaming
    const msgId = addMessage({ role: 'patient', content: '', streaming: true });

    try {
      // Use SSE streaming
      const url = api.streamUrl(sessionId, text);
      const eventSource = new EventSource(url);

      let resolved = false;
      const resolve = () => {
        if (!resolved) {
          resolved = true;
          setLoading(false);
          eventSource.close();
          sendingRef.current = false;
        }
      };

      eventSource.addEventListener('patient_token', (e) => {
        appendToken(msgId, e.data);
      });

      eventSource.addEventListener('patient_complete', (e) => {
        const data = JSON.parse(e.data);
        finalizeMessage(msgId, data.answer, data.scores);
        // Update turn in store
        useChatStore.setState((s) => ({ turn: data.turn || s.turn + 1 }));
        resolve();
      });

      eventSource.addEventListener('error', (e: any) => {
        const msg = e.data ? JSON.parse(e.data).message : '回答生成失败';
        finalizeMessage(msgId, `（${msg}，请重试）`);
        toast.error(msg);
        resolve();
      });

      eventSource.onerror = () => {
        finalizeMessage(msgId, '（连接中断，请重试）');
        toast.error('连接中断，请检查网络');
        resolve();
      };
    } catch {
      finalizeMessage(msgId, '（请求失败）');
      toast.error('请求失败，请稍后再试');
      setLoading(false);
      sendingRef.current = false;
    }
  }, [input, isLoading, sessionId, addMessage, appendToken, finalizeMessage, setLoading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isMaxTurns = turn >= maxTurns;

  return (
    <div className="flex flex-col bg-white border-r border-[var(--color-border)]">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <ChatBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Loading Indicator */}
      {isLoading && (
        <div className="px-4 py-2 text-center">
          <span className="inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
            病人正在思考回答...
          </span>
        </div>
      )}

      {/* Input Area */}
      {sessionActive && !isMaxTurns ? (
        <div className="border-t border-[var(--color-border)] p-4">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请输入您的问诊问题..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 border border-[var(--color-border)] rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent
                         text-sm disabled:bg-gray-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className={`px-6 py-2.5 rounded-lg font-medium text-sm transition-all ${
                input.trim() && !isLoading
                  ? 'bg-[var(--color-primary)] text-white hover:opacity-90'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              发送
            </button>
          </div>
        </div>
      ) : isMaxTurns ? (
        <div className="border-t border-[var(--color-border)] p-4">
          <div className="bg-amber-50 text-amber-700 text-sm px-4 py-3 rounded-lg text-center">
            已达最大问诊轮次 ({maxTurns})，请在右侧提交诊断
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** Single chat message bubble. */
function ChatBubble({ message }: { message: any }) {
  const isDoctor = message.role === 'doctor';
  const isPatient = message.role === 'patient';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="text-center text-xs text-[var(--color-text-secondary)] py-2">
        {message.content}
      </div>
    );
  }

  return (
    <div className={`flex ${isDoctor ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%]`}>
        <div className="flex items-end gap-2">
          {isPatient && (
            <span className="text-lg shrink-0">🤒</span>
          )}
          <div
            className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
              isDoctor
                ? 'bg-[var(--color-primary)] text-white rounded-br-md'
                : 'bg-gray-100 text-[var(--color-text)] rounded-bl-md'
            }`}
          >
            {message.content}
            {message.streaming && (
              <span className="inline-block w-1 h-4 bg-current ml-0.5 animate-pulse align-middle" />
            )}
            {/* Scores badge for patient messages */}
            {message.scores && !message.streaming && (
              <div className="flex gap-2 mt-1.5 pt-1.5 border-t border-white/20">
                {['overall', 'relevance', 'faithfulness', 'robustness'].map((dim) => (
                  <span key={dim} className="text-[10px] opacity-80">
                    {dim === 'overall' ? '综合' : dim === 'relevance' ? '相关' : dim === 'faithfulness' ? '忠实' : '自然'}
                    :{message.scores[dim]}
                  </span>
                ))}
              </div>
            )}
          </div>
          {isDoctor && (
            <span className="text-lg shrink-0">👨‍⚕️</span>
          )}
        </div>
      </div>
    </div>
  );
}
