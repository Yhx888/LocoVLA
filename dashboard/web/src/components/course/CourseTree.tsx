import { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion, type Variants } from 'framer-motion';
import { BookOpen, CheckCircle2, Circle, CircleDot, ChevronDown } from 'lucide-react';
import type { StageSummary } from '../../api/types';

interface CourseTreeProps {
  stages: StageSummary[];
  currentChapterId?: string;
  onSelectChapter: (id: string) => void;
}

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

/* 展开：高度先滑出、内容稍后渐显；折叠：内容先淡出、高度再收起 */
const contentVariants: Variants = {
  hidden: {
    height: 0,
    opacity: 0,
    transition: {
      height: { duration: 0.22, ease: [0.4, 0, 1, 1] },
      opacity: { duration: 0.12, ease: 'easeIn' },
    },
  },
  show: {
    height: 'auto',
    opacity: 1,
    transition: {
      height: { duration: 0.32, ease: EASE_OUT_EXPO },
      opacity: { duration: 0.2, delay: 0.05 },
    },
  },
};

export default function CourseTree({ stages, currentChapterId, onSelectChapter }: CourseTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(stages.map((s) => [s.id, true])),
  );
  const reduce = useReducedMotion();

  const toggle = (id: string) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const statusIcon = (ch: { status: string; completed: boolean; reading_complete: boolean }) => {
    if (ch.completed && ch.reading_complete) return <CheckCircle2 size={16} className="text-green-600 shrink-0" />;
    if (ch.completed) return <CircleDot size={16} className="text-blue-500 shrink-0" />;
    if (ch.reading_complete) return <CircleDot size={16} className="text-emerald-400 shrink-0" />;
    if (ch.status === 'ready') return <BookOpen size={16} className="text-blue-500 shrink-0" />;
    return <Circle size={16} className="text-gray-400 shrink-0" />;
  };

  return (
    <nav className="w-full text-sm">
      {stages.map((stage) => {
        const isOpen = expanded[stage.id] ?? true;
        return (
          <div key={stage.id} className="mb-1">
            <button
              onClick={() => toggle(stage.id)}
              className="flex items-center gap-1.5 w-full px-3 py-2 text-left font-semibold text-gray-700 hover:bg-gray-100 rounded transition-colors"
            >
              {/* 箭头随展开状态旋转：收起时转成右向 */}
              <motion.span
                animate={{ rotate: isOpen ? 0 : -90 }}
                transition={reduce ? { duration: 0 } : { duration: 0.28, ease: EASE_OUT_EXPO }}
                style={{ display: 'inline-flex' }}
              >
                <ChevronDown size={16} />
              </motion.span>
              <span className="truncate">{stage.title}</span>
              <span className="ml-auto text-xs text-gray-400 tabular-nums">
                {stage.completed}/{stage.total}
              </span>
            </button>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  key="content"
                  variants={contentVariants}
                  initial="hidden"
                  animate="show"
                  exit="hidden"
                  /* 外层裁切高度，防止收起时内容溢出 */
                  className="overflow-hidden"
                >
                  <div className="ml-2 border-l border-gray-200 pl-2">
                    {stage.chapters?.map((ch) => {
                      const isActive = ch.id === currentChapterId;
                      return (
                        <button
                          key={ch.id}
                          onClick={() => onSelectChapter(ch.id)}
                          className={`flex items-center gap-2 w-full px-2 py-1.5 rounded text-left transition-colors ${
                            isActive ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-50 text-gray-600'
                          }`}
                        >
                          {statusIcon(ch)}
                          <span className="truncate flex-1">{ch.title}</span>
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
      <div className="mt-3 pt-2 border-t border-gray-200 px-1 text-xs text-gray-400 space-y-1">
        <span className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-green-600" />全部完成</span>
        <span className="flex items-center gap-1.5"><CircleDot size={12} className="text-blue-500" />已完成实验</span>
        <span className="flex items-center gap-1.5"><CircleDot size={12} className="text-emerald-400" />已读完</span>
        <span className="flex items-center gap-1.5"><BookOpen size={12} className="text-blue-500" />可开始</span>
      </div>
    </nav>
  );
}
