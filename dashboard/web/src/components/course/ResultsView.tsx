import { useEffect, useState } from 'react';
import { FileText, ExternalLink, CheckCircle2, XCircle, Clock, RotateCw, Loader2, TriangleAlert, ChevronDown, ChevronUp } from 'lucide-react';
import type { ArtifactDto, RunEvent, RunRecord } from '../../api/types';
import { artifactUrl, connectRunEvents } from '../../api/client';

interface ResultsViewProps {
  chapterId: string;
  artifacts: ArtifactDto[];
  runs: RunRecord[];
  onRerun?: (run: RunRecord) => void;
}

const statusBadge: Record<string, { icon: typeof CheckCircle2; label: string; className: string }> = {
  succeeded: { icon: CheckCircle2, label: '成功', className: 'bg-green-100 text-green-700' },
  failed: { icon: XCircle, label: '失败', className: 'bg-red-100 text-red-700' },
  running: { icon: Loader2, label: '运行中', className: 'bg-blue-100 text-blue-700' },
  queued: { icon: Clock, label: '排队中', className: 'bg-yellow-100 text-yellow-700' },
  cancelled: { icon: RotateCw, label: '已取消', className: 'bg-orange-100 text-orange-700' },
  interrupted: { icon: TriangleAlert, label: '已中断', className: 'bg-orange-100 text-orange-700' },
};

const terminalStatuses = new Set(['succeeded', 'failed', 'cancelled', 'interrupted']);

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function RunResultRow({ run, onRerun }: { run: RunRecord; onRerun?: (run: RunRecord) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const badge = statusBadge[run.status] ?? statusBadge.failed;
  const Icon = badge.icon;

  useEffect(() => {
    if (!expanded) return;
    setEvents([]);
    return connectRunEvents(run.id, 0, (event) => {
      setEvents((current) => current.some((item) => item.sequence === event.sequence)
        ? current
        : [...current, event].slice(-20));
    });
  }, [expanded, run.id]);

  return (
    <div className="bg-gray-50 rounded text-xs">
      <div className="flex flex-wrap items-center gap-3 px-3 py-2">
        <Icon size={14} className={badge.className.split(' ')[1]} />
        <span className="text-gray-600 font-mono shrink-0">{run.preset_id}</span>
        <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${badge.className}`}>
          {badge.label}
        </span>
        <span className="text-gray-400 ml-auto">
          {run.finished_at
            ? new Date(run.finished_at).toLocaleString('zh-CN', {
                month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
              })
            : run.created_at
              ? new Date(run.created_at).toLocaleString('zh-CN', {
                  month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
                })
              : '-'}
        </span>
        {run.exit_code !== null && <span className="text-gray-400 font-mono">exit {run.exit_code}</span>}
        <button type="button" className="run-history-action" onClick={() => setExpanded((value) => !value)}>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? '收起详情' : '查看详情'}
        </button>
        {onRerun && terminalStatuses.has(run.status) && (
          <button type="button" className="run-history-action" onClick={() => onRerun(run)}>
            <RotateCw size={12} />重跑
          </button>
        )}
      </div>
      {expanded && (
        <div className="run-history-details">
          {run.error_category && <p>错误类别：{run.error_category}</p>}
          {run.exit_code !== null && <p>退出码：{run.exit_code}</p>}
          <div className="run-history-tail" aria-live="polite">
            {events.length === 0
              ? <p className="text-gray-400">暂无日志</p>
              : events.map((event) => <p key={event.sequence} className={`log-${event.kind}`}>{event.text}</p>)}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResultsView({ chapterId, artifacts, runs, onRerun }: ResultsViewProps) {
  const chapterRuns = runs.filter((r) => r.chapter_id === chapterId);

  return (
    <div className="space-y-6">
      {/* 运行记录 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-2">运行记录</h4>
        {chapterRuns.length === 0 ? (
          <p className="text-xs text-gray-400">暂无运行记录</p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {chapterRuns.map((run) => <RunResultRow key={run.id} run={run} onRerun={onRerun} />)}
          </div>
        )}
      </div>

      {/* 产物列表 */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-2">产物</h4>
        {artifacts.length === 0 ? (
          <p className="text-xs text-gray-400">暂无产物</p>
        ) : (
          <ul className="space-y-1">
            {artifacts.map((art, i) => (
              <li key={i}>
                <a
                  href={art.url || artifactUrl(art.path)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 rounded text-sm hover:bg-gray-50 transition-colors group"
                >
                  <FileText size={14} className="text-gray-400 shrink-0" />
                  <span className="truncate flex-1 text-gray-700 group-hover:text-blue-600 transition-colors">
                    {art.path.split('/').pop()}
                  </span>
                  <span className="text-xs text-gray-400 tabular-nums">{formatSize(art.size)}</span>
                  {art.evidence_valid && (
                    <CheckCircle2 size={14} className="text-green-500 shrink-0" />
                  )}
                  <ExternalLink size={12} className="text-gray-300 group-hover:text-blue-500 shrink-0" />
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
