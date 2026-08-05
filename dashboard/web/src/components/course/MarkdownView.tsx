import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';
import type { Components } from 'react-markdown';
import { RotateCcw } from 'lucide-react';
import { useRunCoordinator } from '../../run/RunCoordinator';
import InlineCourseAnimation from '../../animations/InlineCourseAnimation';
import QaAnswerBox from './QaAnswerBox';
import { extractQuestionBefore, parseMarkdownSegments } from './markdownSegments';

interface MarkdownViewProps {
  content: string;
  chapterId?: string;
  onExperimentComplete?: () => void;
}

function RunnableCodeBlock({ commands, chapterId, lang, children, onExperimentComplete }: {
  commands: string[];
  chapterId?: string;
  lang: string;
  children: React.ReactNode;
  onExperimentComplete?: () => void;
}) {
  const [currentCommand, setCurrentCommand] = useState(0);
  const instanceId = useId();
  const logContainerRef = useRef<HTMLDivElement>(null);
  const { activeOwnerId, tasks, startRun, resetTask } = useRunCoordinator();
  const ownerId = useMemo(
    () => `code:${chapterId ?? 'unknown'}:${instanceId}`,
    [chapterId, instanceId],
  );
  const snapshot = tasks[ownerId];
  const runState = snapshot?.status ?? 'idle';
  const logs = snapshot?.logs ?? [];
  const isRunning = runState === 'queued' || runState === 'running';
  const occupiedByOther = activeOwnerId !== null && activeOwnerId !== ownerId;

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleRun = useCallback(async () => {
    if (!chapterId || isRunning || occupiedByOther) return;

    try {
      for (let index = 0; index < commands.length; index += 1) {
        setCurrentCommand(index);
        const result = await startRun(ownerId, chapterId, 'script', commands[index], {
          appendLogs: index > 0,
        });
        if (result !== 'succeeded') return;
      }
    } finally {
      // 内联代码块运行结束（无论成功或失败）后，通知父组件刷新运行记录
      onExperimentComplete?.();
    }
  }, [chapterId, commands, isRunning, occupiedByOther, ownerId, startRun, onExperimentComplete]);

  const isBatch = commands.length > 1;
  const buttonLabel = occupiedByOther
    ? '当前任务占用中'
    : isRunning
    ? `运行中（${currentCommand + 1}/${commands.length}）`
    : runState === 'succeeded'
      ? '已完成'
      : runState === 'failed'
        ? '运行失败，重试'
        : isBatch ? `运行全部（${commands.length}）` : '运行';

  return (
    <section className="lesson-code-block lesson-code-block-runnable">
      <div className="lesson-code-block-header">
        <span>{lang || 'text'}</span>
      </div>
      <pre className="lesson-code-block-source">
        <code className={lang ? `language-${lang}` : undefined}>{children}</code>
      </pre>
      <div className="lesson-code-block-actions">
        <span>{isBatch ? `共 ${commands.length} 个实验，按顺序运行` : '运行此实验'}</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={handleRun} disabled={isRunning || occupiedByOther}>
            {buttonLabel}
          </button>
          {(runState === 'succeeded' || runState === 'failed') && (
            <button
              type="button"
              onClick={() => resetTask(ownerId)}
              disabled={isRunning || occupiedByOther}
              title="重置实验状态，恢复未运行"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'transparent' }}
            >
              <RotateCcw size={12} />
              重置
            </button>
          )}
        </div>
      </div>
      {snapshot && runState !== 'idle' && (
        <div ref={logContainerRef} className="lesson-code-block-log" aria-live="polite">
          {logs.length === 0 && isRunning
            ? <p>等待输出...</p>
            : logs.map((event, index) => <p key={`${event.sequence}-${index}`}>{event.text}</p>)}
          {snapshot.error && <p className="log-error">{snapshot.error}</p>}
          {snapshot.errorCategory && <p className="log-error">错误类别：{snapshot.errorCategory}</p>}
          {snapshot.exitCode !== null && <p>退出码：{snapshot.exitCode}</p>}
        </div>
      )}
    </section>
  );
}

function CodeBlock({ lang, children }: { lang: string; children: React.ReactNode }) {
  return (
    <section className="lesson-code-block">
      <div className="lesson-code-block-header">
        <span>{lang || 'text'}</span>
      </div>
      <pre className="lesson-code-block-source">
        <code className={lang ? `language-${lang}` : undefined}>{children}</code>
      </pre>
    </section>
  );
}

function extractRunnableCommands(text: string): string[] | null {
  const commands = text.trim().split('\n').map((line) => line.trim()).filter(Boolean);
  return commands.length > 0 && commands.every((command) => /^python(?:3)?\s+scripts\/.+\.py(?:\s|$)/.test(command))
    ? commands
    : null;
}

export default function MarkdownView({ content, chapterId, onExperimentComplete }: MarkdownViewProps) {
  const segments = useMemo(() => parseMarkdownSegments(content), [content]);
  // components 必须用 useMemo 稳定引用：react-markdown v9 会把这里的渲染函数当作
  // 元素类型，如果每次渲染都重建，运行结束后父组件刷新章节会触发 RunnableCodeBlock
  // 被卸载重建（useId 重新生成、ownerId 变化），运行结果框因此消失。
  const components: Components = useMemo(() => ({
    pre({ children }) {
      return <>{children}</>;
    },
    code({ className, children, ...props }) {
      const isInline = !className;
      if (isInline) {
        return (
          <code className="lesson-inline-code" {...props}>
            {children}
          </code>
        );
      }

      const lang = className?.replace('language-', '') || '';
      const commands = extractRunnableCommands(String(children));
      if (commands) {
        return <RunnableCodeBlock commands={commands} chapterId={chapterId} lang={lang} onExperimentComplete={onExperimentComplete}>{children}</RunnableCodeBlock>;
      }
      return <CodeBlock lang={lang}>{children}</CodeBlock>;
    },
    table({ children }) {
      return <div className="overflow-x-auto my-4"><table className="w-full border-collapse text-sm">{children}</table></div>;
    },
    th({ children }) {
      return <th className="border border-gray-300 px-3 py-2 bg-gray-50 font-semibold text-left">{children}</th>;
    },
    td({ children }) {
      return <td className="border border-gray-300 px-3 py-2">{children}</td>;
    },
    img({ src, alt }) {
      return <img src={src} alt={alt} className="max-w-full h-auto rounded-lg my-2" loading="lazy" />;
    },
    a({ href, children }) {
      return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline hover:text-blue-800">{children}</a>;
    },
  }), [chapterId, onExperimentComplete]);

  return (
    <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-a:text-blue-600 prose-pre:bg-transparent prose-pre:p-0">
      {segments.map((segment, index) => {
        if (segment.type === 'animation') {
          return <InlineCourseAnimation key={`animation-${segment.id}-${index}`} animationId={segment.id} />;
        }
        if (segment.type === 'qa') {
          const previous = segments[index - 1];
          const question = previous && previous.type === 'markdown'
            ? extractQuestionBefore(previous.content)
            : '';
          return (
            <QaAnswerBox
              key={`qa-${segment.id}`}
              qaId={segment.id}
              question={question}
              answer={segment.answer}
              chapterId={chapterId}
            />
          );
        }
        return (
          <ReactMarkdown
            key={`markdown-${index}`}
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex, rehypeRaw]}
            components={components}
          >
            {segment.content}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
