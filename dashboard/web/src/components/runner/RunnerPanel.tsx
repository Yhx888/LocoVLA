import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Play, Square, CheckCircle2, Code2 } from 'lucide-react';
import type { CheckpointDto, RunStatus } from '../../api/types';
import { resetExperiment } from '../../api/client';
import { useRunCoordinator } from '../../run/RunCoordinator';

interface RunnerPanelProps {
  chapterId: string;
  checkpoints: CheckpointDto[];
  experimentAccepted?: boolean;
  onExperimentComplete: () => void;
  customCommands?: { label: string; command: string }[];
}

export default function RunnerPanel({ chapterId, checkpoints, experimentAccepted, onExperimentComplete, customCommands }: RunnerPanelProps) {
  const [activeCheckpoint, setActiveCheckpoint] = useState<string | null>(null);
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);
  // 记住最近一次展示过的任务，运行结束后保持结果不收起（含在正文代码块里发起的运行）
  const [stickyOwnerId, setStickyOwnerId] = useState<string | null>(null);
  const { activeOwnerId, tasks, startRun: startCoordinatedRun, cancelTask, resetTask } = useRunCoordinator();
  useEffect(() => {
    if (activeOwnerId) setStickyOwnerId(activeOwnerId);
  }, [activeOwnerId]);
  const visibleOwnerId = activeOwnerId ?? stickyOwnerId ?? selectedOwnerId;
  const snapshot = visibleOwnerId ? tasks[visibleOwnerId] : undefined;
  const status = snapshot?.status ?? 'idle';
  const logs = snapshot?.logs ?? [];
  const running = status === 'queued' || status === 'running';
  const globallyBusy = activeOwnerId !== null;
  const uniqueCheckpoints = useMemo(
    () => {
      const seen = new Set<string>();
      return checkpoints.filter((cp) => {
        if (seen.has(cp.id)) return false;
        seen.add(cp.id);
        return true;
      });
    },
    [checkpoints],
  );

  const [completedChecks, setCompletedChecks] = useState<Set<string>>(new Set());
  // 后端"实验验收通过"视为该章全部 checkpoint 已完成（刷新后仍保持完成态）
  const isCheckpointDone = (checkpointId: string) =>
    completedChecks.has(checkpointId) || experimentAccepted === true;
  const logEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    logEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [logs]);

  const startRun = useCallback(async (checkpointId: string, command: string) => {
    if (globallyBusy) return;
    const ownerId = `checkpoint:${chapterId}:${checkpointId}`;
    setSelectedOwnerId(ownerId);
    setActiveCheckpoint(checkpointId);
    const result: RunStatus = await startCoordinatedRun(ownerId, chapterId, 'custom', command);
    setActiveCheckpoint(null);
    onExperimentComplete();
    if (result === 'succeeded') {
      setCompletedChecks((prev) => new Set(prev).add(checkpointId));
    }
  }, [chapterId, globallyBusy, onExperimentComplete, startCoordinatedRun]);

  const handleCancel = useCallback(async () => {
    if (visibleOwnerId) await cancelTask(visibleOwnerId);
  }, [cancelTask, visibleOwnerId]);

  const handleReset = useCallback(async () => {
    // 后端有验收通过记录时先删除，避免刷新后状态回弹
    if (experimentAccepted) {
      try {
        await resetExperiment(chapterId);
      } catch {
        // 后端删除失败不阻塞本地重置，用户仍可重新实验
      }
    }
    if (selectedOwnerId) resetTask(selectedOwnerId);
    setActiveCheckpoint(null);
    setSelectedOwnerId(null);
    setStickyOwnerId(null);
    setCompletedChecks(new Set());
    // 通知父组件刷新章节数据与左侧树（experiment_accepted 回 false）
    onExperimentComplete();
  }, [experimentAccepted, chapterId, onExperimentComplete, resetTask, selectedOwnerId]);

  const hasCheckpoints = uniqueCheckpoints && uniqueCheckpoints.length > 0;
  const hasCustomCommands = customCommands && customCommands.length > 0;
  if (!hasCheckpoints && !hasCustomCommands) return null;

  return (
    <>
      {customCommands && customCommands.length > 0 && (
        <div className="mb-3 space-y-2">
          {customCommands.map((cmd, idx) => (
            <div key={idx} className="checkpoint-card border-purple-300 bg-purple-50/30">
              <div className="checkpoint-header">
                <span className="checkpoint-label">
                  <Code2 size={12} className="inline mr-1 text-purple-500" />
                  {cmd.label}
                </span>
                <button
                  className={`run-btn ${activeCheckpoint === `custom-${idx}` ? 'running' : ''}`}
                  onClick={() => startRun(`custom-${idx}`, cmd.command)}
                  disabled={globallyBusy}
                >
                  <Play size={12} /> {globallyBusy ? '当前任务占用中' : '运行'}
                </button>
              </div>
              <div className="checkpoint-cmd">$ {cmd.command}</div>
            </div>
          ))}
        </div>
      )}

      {(completedChecks.size > 0 || experimentAccepted === true) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            onClick={handleReset}
            className="text-xs px-2 py-1 text-gray-500 hover:bg-gray-100 rounded transition-colors"
            title="重置实验完成状态，恢复未运行"
          >
            重置实验状态
          </button>
        </div>
      )}

      {uniqueCheckpoints.map((cp) => (
        <div key={cp.id} className={`checkpoint-card ${isCheckpointDone(cp.id) ? 'border-green-300' : ''}`}>
          <div className="checkpoint-header">
            <span className="checkpoint-label">
              {cp.id === 'automatic_acceptance' ? '自动验收' : cp.id.replace(/_/g, ' ')}
            </span>
            <button
              className={`run-btn ${activeCheckpoint === cp.id ? 'running' : ''} ${isCheckpointDone(cp.id) ? 'done' : ''}`}
              onClick={() => startRun(cp.id, cp.command)}
              disabled={globallyBusy}
            >
              {activeCheckpoint === cp.id && running ? (
                <>运行中</>
              ) : isCheckpointDone(cp.id) ? (
                <>已完成 <CheckCircle2 size={12} /></>
              ) : (
                <><Play size={12} /> {globallyBusy ? '当前任务占用中' : status === 'failed' ? '重跑' : '运行'}</>
              )}
            </button>
          </div>
          <div className="checkpoint-cmd">$ {cp.command}</div>
          {cp.acceptance && (
            <div className="checkpoint-acceptance">{cp.acceptance}</div>
          )}
        </div>
      ))}

      {status !== 'idle' && (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs font-medium ${
              status === 'succeeded' ? 'text-green-600' :
              status === 'failed' ? 'text-red-600' :
              status === 'cancelled' || status === 'interrupted' ? 'text-orange-500' :
              'text-blue-600'
            }`}>
              {running ? '运行中...' :
               status === 'succeeded' ? '完成' :
               status === 'failed' ? '失败' :
               status === 'cancelled' ? '已取消' :
               status === 'interrupted' ? '服务中断' : ''}
            </span>
            <div className="flex gap-2">
              {running && (
                <button onClick={handleCancel} className="text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded transition-colors">
                  <Square size={12} className="inline mr-1" />取消
                </button>
              )}
              {(status === 'succeeded' || status === 'failed' || status === 'cancelled' || status === 'interrupted') && (
                <button onClick={handleReset} className="text-xs px-2 py-1 text-gray-500 hover:bg-gray-100 rounded transition-colors">
                  重置
                </button>
              )}
            </div>
          </div>

          <div className="log-area">
            {logs.length === 0 && running && (
              <p className="log-line log-status">等待输出...</p>
            )}
            {logs.map((ev, i) => (
              <p key={i} className={`log-line log-${ev.kind}`}>
                {ev.text}
              </p>
            ))}
            {snapshot?.error && <p className="log-line log-stderr">{snapshot.error}</p>}
            {snapshot?.errorCategory && (
              <p className="log-line log-stderr">错误类别：{snapshot.errorCategory}</p>
            )}
            {snapshot?.exitCode !== null && snapshot?.exitCode !== undefined && (
              <p className="log-line log-status">退出码：{snapshot.exitCode}</p>
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </>
  );
}
