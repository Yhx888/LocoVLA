// 注："取消"按钮始终设 reading_complete=false，不 toggle
import { useState, useEffect, useCallback } from 'react';
import { CheckCircle2, Circle, BookOpen, FlaskConical, RotateCcw } from 'lucide-react';
import { resetExperiment, updateProgress } from '../../api/client';
import type { SelfCheckItem } from '../../api/types';

interface ProgressPanelProps {
  chapterId: string;
  readingPercent: number;
  readingComplete: boolean;
  selfCheckIds: string[];
  selfCheckItems: SelfCheckItem[];
  experimentAccepted: boolean;
  completed: boolean;
  onProgressUpdate: () => void;
}

export default function ProgressPanel({
  chapterId,
  readingPercent,
  readingComplete,
  selfCheckIds,
  selfCheckItems,
  experimentAccepted,
  completed,
  onProgressUpdate,
}: ProgressPanelProps) {
  const [items, setItems] = useState<SelfCheckItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [markedReading, setMarkedReading] = useState(readingComplete);
  const [currentReadingPercent, setCurrentReadingPercent] = useState(readingPercent);

  useEffect(() => {
    setMarkedReading(readingComplete);
    setCurrentReadingPercent(readingPercent);
  }, [readingComplete, readingPercent, chapterId]);

  useEffect(() => {
    const merged = selfCheckItems.map((def) => ({
      ...def,
      checked: selfCheckIds.includes(def.id),
    }));
    setItems(merged);
  }, [selfCheckItems, selfCheckIds, chapterId]);

  const handleToggleSelfCheck = useCallback((id: string) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, checked: !item.checked } : item)),
    );
  }, []);

  const handleSaveSelfCheck = useCallback(async () => {
    setSaving(true);
    try {
      await updateProgress(chapterId, {
        reading_percent: currentReadingPercent,
        reading_complete: markedReading,
        self_check_ids: items.filter((i) => i.checked).map((i) => i.id),
      });
      onProgressUpdate();
    } finally {
      setSaving(false);
    }
  }, [chapterId, currentReadingPercent, markedReading, items, onProgressUpdate]);

  const handleMarkReading = useCallback(async () => {
    const newValue = !markedReading;
    const newPercent = newValue ? 100 : currentReadingPercent;
    setMarkedReading(newValue);
    setCurrentReadingPercent(newPercent);
    try {
      await updateProgress(chapterId, {
        reading_percent: newPercent,
        reading_complete: newValue,
        self_check_ids: items.filter((i) => i.checked).map((i) => i.id),
      });
      onProgressUpdate();
    } catch {
      setMarkedReading(!newValue);
      setCurrentReadingPercent(currentReadingPercent);
    }
  }, [chapterId, markedReading, currentReadingPercent, items, onProgressUpdate]);

  const handleCancelReading = useCallback(async () => {
    const prevMarked = markedReading;
    setMarkedReading(false);
    try {
      await updateProgress(chapterId, {
        reading_percent: currentReadingPercent,
        reading_complete: false,
        self_check_ids: items.filter((i) => i.checked).map((i) => i.id),
      });
      onProgressUpdate();
    } catch {
      setMarkedReading(prevMarked);
    }
  }, [chapterId, currentReadingPercent, items, onProgressUpdate, markedReading]);

  const [resetting, setResetting] = useState(false);
  const handleResetExperiment = useCallback(async () => {
    setResetting(true);
    try {
      await resetExperiment(chapterId);
      onProgressUpdate();
    } finally {
      setResetting(false);
    }
  }, [chapterId, onProgressUpdate]);

  return (
    <div className="space-y-6">
      <div>
        <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <BookOpen size={16} />
          阅读进度
        </h4>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${currentReadingPercent}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{currentReadingPercent}%</span>
          <div className="flex items-center gap-1">
            <button
              onClick={handleMarkReading}
              className={`flex items-center gap-1 px-2 py-1 rounded transition-colors ${
                markedReading
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {markedReading ? <CheckCircle2 size={14} /> : <Circle size={14} />}
              {markedReading ? '已读完' : '标记为已读完'}
            </button>
            {markedReading && (
              <button
                onClick={handleCancelReading}
                className="flex items-center gap-1 px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
              >
                <Circle size={14} />
                取消
              </button>
            )}
          </div>
        </div>
      </div>

      <div>
        <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <CheckCircle2 size={16} />
          自检清单
        </h4>
        {items.length === 0 ? (
          <p className="text-xs text-gray-400">暂无自检项</p>
        ) : (
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.id} className="flex items-start gap-2">
                <button
                  onClick={() => handleToggleSelfCheck(item.id)}
                  className={`mt-0.5 shrink-0 ${item.checked ? 'text-green-500' : 'text-gray-300'}`}
                >
                  {item.checked ? <CheckCircle2 size={16} /> : <Circle size={16} />}
                </button>
                <span className={`text-sm ${item.checked ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                  {item.text}
                </span>
              </li>
            ))}
          </ul>
        )}
        {items.length > 0 && (
          <button
            onClick={handleSaveSelfCheck}
            disabled={saving}
            className="mt-2 text-xs px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {saving ? '保存中...' : '保存进度'}
          </button>
        )}
      </div>

      <div>
        <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <FlaskConical size={16} />
          实验状态
        </h4>
        <div className="flex items-center gap-2">
          {experimentAccepted ? (
            <>
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 size={14} />
                实验验收已通过
              </span>
              <button
                type="button"
                onClick={handleResetExperiment}
                disabled={resetting}
                className="flex items-center gap-1 px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 transition-colors text-xs"
                title="重置实验验收状态"
              >
                <RotateCcw size={12} />
                {resetting ? '重置中...' : '重置'}
              </button>
            </>
          ) : (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <Circle size={14} />
              待运行正式实验
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
