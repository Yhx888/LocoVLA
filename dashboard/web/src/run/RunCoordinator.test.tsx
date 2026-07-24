import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { RunEvent, RunStatus } from '../api/types';
import {
  cancelRun,
  connectRunEvents,
  createRun,
  getRun,
} from '../api/client';
import { RunCoordinatorProvider, useRunCoordinator } from './RunCoordinator';

vi.mock('../api/client', () => ({
  cancelRun: vi.fn(),
  connectRunEvents: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  listRuns: vi.fn().mockResolvedValue([]),
}));

function Harness({ onSettled }: { onSettled: (status: RunStatus) => void }) {
  const coordinator = useRunCoordinator();
  const snapshot = coordinator.tasks.owner;
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          void coordinator.startRun('owner', '03', 'script', 'python scripts/demo.py').then(onSettled);
        }}
      >
        启动
      </button>
      <button type="button" onClick={() => void coordinator.cancelTask('owner')}>取消</button>
      <span data-testid="status">{snapshot?.status ?? 'idle'}</span>
      <span data-testid="run-id">{snapshot?.runId ?? ''}</span>
      <div>{snapshot?.logs.map((event) => event.text).join('|')}</div>
    </div>
  );
}

describe('RunCoordinator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    vi.mocked(connectRunEvents).mockReturnValue(() => {});
  });

  it('状态轮询不会重连仍然健康的 WebSocket', async () => {
    vi.useFakeTimers();
    vi.mocked(createRun).mockResolvedValue({ id: 'healthy', status: 'running' } as never);
    vi.mocked(getRun).mockResolvedValue({
      id: 'healthy', status: 'running', last_event_sequence: 0,
    } as never);

    const { getByRole } = render(
      <RunCoordinatorProvider><Harness onSettled={() => {}} /></RunCoordinatorProvider>,
    );
    await act(async () => getByRole('button', { name: '启动' }).click());
    await vi.waitFor(() => expect(connectRunEvents).toHaveBeenCalledTimes(1));

    await act(async () => vi.advanceTimersByTimeAsync(2500));

    expect(getRun).toHaveBeenCalled();
    expect(connectRunEvents).toHaveBeenCalledTimes(1);
  });

  it('取消后补齐终态事件并结算原 startRun Promise', async () => {
    let listener: ((event: RunEvent) => void) | undefined;
    const onSettled = vi.fn();
    vi.mocked(createRun).mockResolvedValue({ id: 'cancelled-run', status: 'queued' } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, onEvent) => {
      listener = onEvent;
      return () => {};
    });
    vi.mocked(cancelRun).mockResolvedValue(undefined);
    vi.mocked(getRun).mockResolvedValue({
      id: 'cancelled-run', status: 'cancelled', last_event_sequence: 2,
      exit_code: null, error_category: 'user_cancelled',
    } as never);

    const { getByRole, getByTestId, getByText } = render(
      <RunCoordinatorProvider><Harness onSettled={onSettled} /></RunCoordinatorProvider>,
    );
    await act(async () => getByRole('button', { name: '启动' }).click());
    await vi.waitFor(() => expect(listener).toBeDefined());
    act(() => listener?.({
      run_id: 'cancelled-run', sequence: 1, timestamp: '', kind: 'stdout',
      stream: 'stdout', text: '尾部输出', status: null,
    }));

    await act(async () => getByRole('button', { name: '取消' }).click());
    expect(onSettled).not.toHaveBeenCalled();
    await act(async () => listener?.({
      run_id: 'cancelled-run', sequence: 2, timestamp: '', kind: 'status',
      stream: '', text: '任务已取消', status: 'cancelled',
    }));

    await vi.waitFor(() => expect(onSettled).toHaveBeenCalledWith('cancelled'));
    expect(getByTestId('status')).toHaveTextContent('cancelled');
    expect(getByText('尾部输出|任务已取消')).toBeInTheDocument();
  });

  it('409 冲突时接管后端返回的活动任务', async () => {
    let listener: ((event: RunEvent) => void) | undefined;
    const onSettled = vi.fn();
    vi.mocked(createRun).mockRejectedValue(Object.assign(new Error('已有任务在运行中'), {
      status: 409,
      activeRunId: 'server-active',
    }));
    vi.mocked(getRun)
      .mockResolvedValueOnce({ id: 'server-active', status: 'running', last_event_sequence: 0 } as never)
      .mockResolvedValue({
        id: 'server-active', status: 'succeeded', last_event_sequence: 1,
        exit_code: 0, error_category: null,
      } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, onEvent) => {
      listener = onEvent;
      return () => {};
    });

    const { getByRole, getByTestId } = render(
      <RunCoordinatorProvider><Harness onSettled={onSettled} /></RunCoordinatorProvider>,
    );
    await act(async () => getByRole('button', { name: '启动' }).click());

    await vi.waitFor(() => expect(connectRunEvents).toHaveBeenCalledWith(
      'server-active', 0, expect.any(Function), expect.any(Function),
    ));
    expect(getByTestId('run-id')).toHaveTextContent('server-active');
    await act(async () => listener?.({
      run_id: 'server-active', sequence: 1, timestamp: '', kind: 'status',
      stream: '', text: '任务完成', status: 'succeeded',
    }));
    await vi.waitFor(() => expect(onSettled).toHaveBeenCalledWith('succeeded'));
  });
});
