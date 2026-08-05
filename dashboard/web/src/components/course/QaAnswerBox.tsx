import { useCallback, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import { ChevronDown, ChevronRight, MessageSquareText, Sparkles } from 'lucide-react';
import { getAiStatus, gradeAnswer, AI_CONFIG_UPDATED_EVENT } from '../../api/client';
import type { AiGradeResult } from '../../api/types';

interface QaAnswerBoxProps {
  qaId: string;
  question: string;
  answer: string;
  chapterId?: string;
}

// 用户答案与评分结果只暂存 sessionStorage，不进入后端进度存储
const answerKey = (qaId: string) => `upkie-qa-answer:${qaId}`;
const gradeKey = (qaId: string) => `upkie-qa-grade:${qaId}`;

function loadStoredGrade(qaId: string): AiGradeResult | null {
  try {
    const raw = sessionStorage.getItem(gradeKey(qaId));
    return raw ? (JSON.parse(raw) as AiGradeResult) : null;
  } catch {
    return null;
  }
}

export default function QaAnswerBox({ qaId, question, answer, chapterId }: QaAnswerBoxProps) {
  const [userAnswer, setUserAnswer] = useState(() => sessionStorage.getItem(answerKey(qaId)) ?? '');
  const [gradeResult, setGradeResult] = useState<AiGradeResult | null>(() => loadStoredGrade(qaId));
  const [revealed, setRevealed] = useState(() => loadStoredGrade(qaId) !== null);
  const [grading, setGrading] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      getAiStatus()
        .then((status) => { if (!cancelled) setAiConfigured(status.configured); })
        .catch(() => { if (!cancelled) setAiConfigured(false); });
    };
    refresh();
    // AI 助教面板保存配置后广播事件，评分按钮同步启用
    window.addEventListener(AI_CONFIG_UPDATED_EVENT, refresh);
    return () => {
      cancelled = true;
      window.removeEventListener(AI_CONFIG_UPDATED_EVENT, refresh);
    };
  }, []);

  const handleAnswerChange = useCallback((value: string) => {
    setUserAnswer(value);
    try {
      sessionStorage.setItem(answerKey(qaId), value);
    } catch {}
  }, [qaId]);

  const handleGrade = useCallback(async () => {
    if (grading || !userAnswer.trim()) return;
    setGrading(true);
    setGradeError(null);
    try {
      const result = await gradeAnswer({
        chapter_id: chapterId ?? '',
        question_id: qaId,
        question,
        reference_answer: answer,
        user_answer: userAnswer,
      });
      setGradeResult(result);
      // 评分完成后自动展开标准答案，形成「作答 → 评分 → 对照」闭环
      setRevealed(true);
      try {
        sessionStorage.setItem(gradeKey(qaId), JSON.stringify(result));
      } catch {}
    } catch (error) {
      setGradeError(error instanceof Error ? error.message : 'AI 评分失败');
    } finally {
      setGrading(false);
    }
  }, [grading, userAnswer, chapterId, qaId, question, answer]);

  return (
    <section className="qa-answer-box">
      <div className="qa-attempt">
        <label htmlFor={`qa-input-${qaId}`}>我的答案</label>
        <div className="qa-attempt-row">
          <textarea
            id={`qa-input-${qaId}`}
            value={userAnswer}
            rows={3}
            placeholder="先用自己的话写下答案，再让 AI 评分或对照参考答案"
            onChange={(event) => handleAnswerChange(event.target.value)}
          />
          <button
            type="button"
            className="qa-grade-btn"
            disabled={!aiConfigured || grading || !userAnswer.trim()}
            title={aiConfigured === false ? 'AI 未配置，无法评分' : undefined}
            onClick={handleGrade}
          >
            <Sparkles size={13} />
            {grading ? '评分中...' : 'AI 评分'}
          </button>
        </div>
        {aiConfigured === false && (
          <span className="qa-ai-hint">AI 未配置（在右侧「AI 助教」面板填写配置即可启用）</span>
        )}
        {gradeError && <p className="qa-grade-error">{gradeError}</p>}
        {gradeResult && (
          <div className="qa-grade-result">
            <div className="qa-grade-score">得分 {gradeResult.score} / 10</div>
            {gradeResult.comment && <p>{gradeResult.comment}</p>}
            {gradeResult.gaps.length > 0 && (
              <ul>
                {gradeResult.gaps.map((gap, index) => <li key={index}>{gap}</li>)}
              </ul>
            )}
          </div>
        )}
      </div>
      <button
        type="button"
        className={`qa-answer-toggle ${revealed ? 'open' : ''}`}
        onClick={() => setRevealed((v) => !v)}
      >
        <MessageSquareText size={15} />
        <span>参考答案</span>
        <span className="qa-answer-hint">{revealed ? '点击收起' : '建议先作答再展开对照'}</span>
        <span className="qa-answer-chevron">{revealed ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
      </button>
      {revealed && (
        <div className="qa-reference">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex, rehypeRaw]}
          >
            {answer}
          </ReactMarkdown>
        </div>
      )}
    </section>
  );
}
