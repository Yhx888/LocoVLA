import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  cancelRun,
  connectRunEvents,
  createRun,
  getRun,
  listRuns,
} from '../api/client';
import type { RunEvent, RunRecord, RunStatus } from '../api/types';

const TERMINAL = new Set<RunStatus>([
  'succeeded', 'failed', 'cancelled', 'interrupted',
]);

export interface RunSnapshot {
  ownerId: string;
  runId: string | null;
  status: RunStatus | 'idle';
  logs: RunEvent[];
  error: string | null;
  exitCode: number | null;
  errorCategory: string | null;
}

interface StartOptions {
  appendLogs?: boolean;
}

interface RunCoordinatorValue {
  activeOwnerId: string | null;
  tasks: Record<string, RunSnapshot>;
  startRun: (
    ownerId: string,
    chapterId: string,
    presetId: string,
    command: string,
    options?: StartOptions,
  ) => Promise<RunStatus>;
  cancelTask: (ownerId: string) => Promise<void>;
  resetTask: (ownerId: string) => void;
}

interface Monitor {
  stop: () => void;
  refresh: () => Promise<void>;
}

const RunCoordinatorContext = createContext<RunCoordinatorValue | null>(null);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function RunCoordinatorProvider({ children }: { children: ReactNode }) {
  const [activeOwnerId, setActiveOwnerId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Record<string, RunSnapshot>>({});
  const activeOwnerRef = useRef<string | null>(null);
  const tasksRef = useRef<Record<string, RunSnapshot>>({});
  const monitorsRef = useRef(new Map<string, Monitor>());

  const replaceTasks = useCallback((updater: (current: Record<string, RunSnapshot>) => Record<string, RunSnapshot>) => {
    setTasks((current) => {
      const next = updater(current);
      tasksRef.current = next;
      return next;
    });
  }, []);

  const updateTask = useCallback((ownerId: string, update: Partial<RunSnapshot>) => {
    replaceTasks((current) => {
      const previous = current[ownerId] ?? {
        ownerId,
        runId: null,
        status: 'idle',
        logs: [],
        error: null,
        exitCode: null,
        errorCategory: null,
      } satisfies RunSnapshot;
      return {
        ...current,
        [ownerId]: {
          ...previous,
          ownerId,
        ...update,
        },
      };
    });
  }, [replaceTasks]);

  const releaseOwner = useCallback((ownerId: string) => {
    monitorsRef.current.get(ownerId)?.stop();
    monitorsRef.current.delete(ownerId);
    if (activeOwnerRef.current === ownerId) {
      activeOwnerRef.current = null;
      setActiveOwnerId(null);
    }
  }, []);

  const monitorRun = useCallback((ownerId: string, run: RunRecord) => (
    new Promise<RunStatus>((resolve) => {
      let lastSequence = 0;
      let closed = false;
      let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
      let pollTimer: ReturnType<typeof setInterval> | null = null;
      let disconnect: (() => void) | null = null;
      let connected = false;

      const stop = () => {
        closed = true;
        connected = false;
        disconnect?.();
        disconnect = null;
        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (pollTimer) clearInterval(pollTimer);
      };

      const finish = (status: RunStatus, record?: RunRecord) => {
        if (closed) return;
        updateTask(ownerId, {
          status,
          exitCode: record?.exit_code ?? null,
          errorCategory: record?.error_category ?? null,
        });
        releaseOwner(ownerId);
        resolve(status);
      };

      const scheduleReconnect = () => {
        if (closed || reconnectTimer !== null) return;
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connect();
        }, 300);
      };

      const checkStatus = async (afterDisconnect: boolean) => {
        if (closed) return;
        try {
          const current = await getRun(run.id);
          if (closed) return;
          if (TERMINAL.has(current.status)) {
            if (lastSequence < current.last_event_sequence) {
              if (afterDisconnect || !connected) scheduleReconnect();
              return;
            }
            finish(current.status, current);
            return;
          }
        } catch (error) {
          if (closed) return;
          updateTask(ownerId, { error: errorMessage(error) });
        }
        if (afterDisconnect) scheduleReconnect();
      };

      const recover = () => checkStatus(true);
      const refresh = () => checkStatus(false);

      function connect() {
        if (closed) return;
        disconnect?.();
        disconnect = null;
        connected = true;
        disconnect = connectRunEvents(
          run.id,
          lastSequence,
          (event) => {
            if (event.sequence <= lastSequence) return;
            lastSequence = event.sequence;
            replaceTasks((current) => {
              const snapshot = current[ownerId];
              if (!snapshot) return current;
              return {
                ...current,
                [ownerId]: {
                  ...snapshot,
                  status: (event.status as RunStatus | null) ?? snapshot.status,
                  logs: [...snapshot.logs, event],
                },
              };
            });
            if (event.status && TERMINAL.has(event.status as RunStatus)) {
              void refresh();
            }
          },
          () => {
            if (closed) return;
            connected = false;
            disconnect = null;
            void recover();
          },
        );
      }

      monitorsRef.current.set(ownerId, { stop, refresh });
      connect();
      pollTimer = setInterval(() => void refresh(), 1000);
    })
  ), [releaseOwner, replaceTasks, updateTask]);

  const startRun = useCallback(async (
    ownerId: string,
    chapterId: string,
    presetId: string,
    command: string,
    options: StartOptions = {},
  ): Promise<RunStatus> => {
    if (activeOwnerRef.current !== null) {
      updateTask(ownerId, { error: '当前有任务正在运行，请等待其结束。' });
      return 'failed';
    }

    activeOwnerRef.current = ownerId;
    setActiveOwnerId(ownerId);
    const previousLogs = options.appendLogs ? tasksRef.current[ownerId]?.logs ?? [] : [];
    updateTask(ownerId, {
      runId: null,
      status: 'queued',
      logs: previousLogs,
      error: null,
      exitCode: null,
      errorCategory: null,
    });

    try {
      const run = await createRun(chapterId, presetId, command);
      updateTask(ownerId, { runId: run.id, status: run.status });
      return await monitorRun(ownerId, run);
    } catch (error) {
      const activeRunId = typeof error === 'object' && error !== null
        && 'status' in error && error.status === 409
        && 'activeRunId' in error && typeof error.activeRunId === 'string'
        ? error.activeRunId
        : null;
      if (activeRunId) {
        try {
          const activeRun = await getRun(activeRunId);
          updateTask(ownerId, {
            runId: activeRun.id,
            status: activeRun.status,
            error: null,
          });
          return await monitorRun(ownerId, activeRun);
        } catch (recoveryError) {
          error = recoveryError;
        }
      }
      const message = errorMessage(error);
      updateTask(ownerId, {
        status: 'failed',
        error: message,
        exitCode: null,
        errorCategory: 'request_error',
        logs: [
          ...previousLogs,
          {
            run_id: '',
            sequence: -1,
            timestamp: new Date().toISOString(),
            kind: 'stderr',
            stream: 'stderr',
            text: message,
            status: 'failed',
          },
        ],
      });
      releaseOwner(ownerId);
      return 'failed';
    }
  }, [monitorRun, releaseOwner, updateTask]);

  const cancelTask = useCallback(async (ownerId: string) => {
    const runId = tasksRef.current[ownerId]?.runId;
    if (!runId) return;
    try {
      await cancelRun(runId);
      await monitorsRef.current.get(ownerId)?.refresh();
    } catch (error) {
      updateTask(ownerId, { error: errorMessage(error) });
    }
  }, [updateTask]);

  const resetTask = useCallback((ownerId: string) => {
    if (activeOwnerRef.current === ownerId) return;
    replaceTasks((current) => {
      const next = { ...current };
      delete next[ownerId];
      return next;
    });
  }, [replaceTasks]);

  useEffect(() => {
    let disposed = false;
    listRuns().then((runs) => {
      if (disposed || activeOwnerRef.current !== null) return;
      const active = runs.find((run) => run.status === 'queued' || run.status === 'running');
      if (!active) return;
      const ownerId = `restored:${active.id}`;
      activeOwnerRef.current = ownerId;
      setActiveOwnerId(ownerId);
      updateTask(ownerId, {
        runId: active.id,
        status: active.status,
        logs: [],
        error: null,
        exitCode: null,
        errorCategory: null,
      });
      void monitorRun(ownerId, active);
    }).catch(() => {});
    return () => {
      disposed = true;
      for (const monitor of monitorsRef.current.values()) monitor.stop();
      monitorsRef.current.clear();
    };
  }, [monitorRun, updateTask]);

  return (
    <RunCoordinatorContext.Provider value={{
      activeOwnerId,
      tasks,
      startRun,
      cancelTask,
      resetTask,
    }}>
      {children}
    </RunCoordinatorContext.Provider>
  );
}

export function useRunCoordinator(): RunCoordinatorValue {
  const context = useContext(RunCoordinatorContext);
  if (!context) throw new Error('useRunCoordinator 必须在 RunCoordinatorProvider 中使用');
  return context;
}
