import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, CheckCircle2, Circle, CircleDot, ChevronDown, ChevronRight } from 'lucide-react';
import type { StageSummary } from '../../api/types';

interface CourseTreeProps {
  stages: StageSummary[];
  currentChapterId?: string;
  onSelectChapter: (id: string) => void;
}

export default function CourseTree({ stages, currentChapterId, onSelectChapter }: CourseTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(stages.map((s) => [s.id, true])),
  );

  const toggle = (id: string) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const statusIcon = (ch: { status: string; completed: boolean; reading_complete: boolean }) => {
    if (ch.completed) return <CheckCircle2 size={16} className="text-green-600 shrink-0" />;
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
              {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span className="truncate">{stage.title}</span>
              <span className="ml-auto text-xs text-gray-400 tabular-nums">
                {stage.completed}/{stage.total}
              </span>
            </button>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  key="content"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
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
        <span className="flex items-center gap-1.5"><CircleDot size={12} className="text-emerald-400" />已读完</span>
        <span className="flex items-center gap-1.5"><BookOpen size={12} className="text-blue-500" />可开始</span>
      </div>
    </nav>
  );
}
