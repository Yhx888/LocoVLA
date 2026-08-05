import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import { Send, Settings2, Sparkles } from 'lucide-react';
import { AI_CONFIG_UPDATED_EVENT, getAiStatus, streamExplain } from '../../api/client';
import type { AiChatMessage } from '../../api/types';
import AiConfigForm from './AiConfigForm';

export interface ExplainRequest {
  text: string;
  context: string;
  nonce: number;
}

interface AiAssistantPanelProps {
  chapterId: string;
  chapterTitle: string;
  explainRequest: ExplainRequest | null;
}

function truncate(text: string, limit: number): string {
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

export default function AiAssistantPanel({ chapterId, chapterTitle, explainRequest }: AiAssistantPanelProps) {
  const [messages, setMessages] = useState<AiChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const messagesRef = useRef<AiChatMessage[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const handledNonceRef = useRef<number | null>(null);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      getAiStatus()
        .then((status) => { if (!cancelled) setAiConfigured(status.configured); })
        .catch(() => { if (!cancelled) setAiConfigured(false); });
    };
    refresh();
    // 配置面板保存后广播事件，其他入口据此刷新状态
    window.addEventListener(AI_CONFIG_UPDATED_EVENT, refresh);
    return () => {
      cancelled = true;
      window.removeEventListener(AI_CONFIG_UPDATED_EVENT, refresh);
    };
  }, []);

  // 切换章节时清空会话并中断进行中的请求
  useEffect(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    setStreaming(false);
  }, [chapterId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const runRequest = useCallback(async (
    displayUser: string,
    body: { selected_text?: string; context?: string; question?: string },
  ) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const history = messagesRef.current.filter((m) => m.content.trim());
    setError(null);
    setStreaming(true);
    setMessages((prev) => [...prev, { role: 'user', content: displayUser }, { role: 'assistant', content: '' }]);
    try {
      await streamExplain(
        {
          chapter_id: chapterId,
          chapter_title: chapterTitle,
          history,
          ...body,
        },
        (delta) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + delta };
            return next;
          });
        },
        controller.signal,
      );
    } catch (requestError) {
      if (!controller.signal.aborted) {
        setError(requestError instanceof Error ? requestError.message : 'AI 请求失败');
      }
    } finally {
      if (abortRef.current === controller) {
        setStreaming(false);
      }
    }
  }, [chapterId, chapterTitle]);

  // 收到圈选解释请求时自动发起对话
  useEffect(() => {
    if (!explainRequest || explainRequest.nonce === handledNonceRef.current) return;
    handledNonceRef.current = explainRequest.nonce;
    runRequest(
      `请解释：「${truncate(explainRequest.text, 120)}」`,
      { selected_text: explainRequest.text, context: explainRequest.context },
    );
  }, [explainRequest, runRequest]);

  const handleAsk = useCallback(() => {
    const question = input.trim();
    if (!question || streaming) return;
    setInput('');
    runRequest(question, { question });
  }, [input, streaming, runRequest]);

  if (showConfig) {
    return (
      <AiConfigForm
        onSaved={() => setShowConfig(false)}
        onCancel={() => setShowConfig(false)}
      />
    );
  }

  if (aiConfigured === false) {
    return (
      <div className="ai-panel-empty">
        <Sparkles size={18} />
        <p>AI 助教未配置</p>
        <p className="ai-panel-empty-hint">
          点击下方按钮直接填写 API key、地址与模型即可启用，无需改文件或重启服务。
        </p>
        <button type="button" className="ai-config-open" onClick={() => setShowConfig(true)}>
          <Settings2 size={14} />
          配置 AI 助教
        </button>
      </div>
    );
  }

  return (
    <div className="ai-panel">
      <div className="ai-panel-toolbar">
        <button
          type="button"
          className="ai-config-open-mini"
          title="修改 AI 配置"
          aria-label="修改 AI 配置"
          onClick={() => setShowConfig(true)}
        >
          <Settings2 size={13} />
        </button>
      </div>
      <div ref={scrollRef} className="ai-panel-messages">
        {messages.length === 0 && (
          <div className="ai-panel-empty">
            <Sparkles size={18} />
            <p>圈选教程中的文字点「AI 解释」，或直接在下方提问。</p>
          </div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={`ai-message ai-message-${message.role}`}>
            {message.role === 'assistant' ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw]}
              >
                {message.content || (streaming && index === messages.length - 1 ? '思考中...' : '')}
              </ReactMarkdown>
            ) : (
              <p>{message.content}</p>
            )}
          </div>
        ))}
        {error && <p className="ai-panel-error">{error}</p>}
      </div>
      <div className="ai-panel-input">
        <textarea
          value={input}
          rows={2}
          placeholder="向 AI 助教提问，Enter 发送，Shift+Enter 换行"
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleAsk();
            }
          }}
        />
        <button
          type="button"
          disabled={streaming || !input.trim()}
          aria-label="发送提问"
          onClick={handleAsk}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
