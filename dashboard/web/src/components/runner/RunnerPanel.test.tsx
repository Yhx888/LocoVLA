import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { RunEvent, RunStatus } from '../../api/types';
import { connectRunEvents, createRun, getRun } from '../../api/client';
import { RunCoordinatorProvider } from '../../run/RunCoordinator';
import RunnerPanel from './RunnerPanel';

vi.mock('../../api/client', () => ({
  cancelRun: vi.fn(),
  connectRunEvents: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  listRuns: vi.fn().mockResolvedValue([]),
}));

describe('RunnerPanel 终态刷新', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each<RunStatus>(['failed', 'cancelled'])('%s 后也刷新章节结果', async (status) => {
    let listener: ((event: RunEvent) => void) | undefined;
    const onExperimentComplete = vi.fn();
    vi.mocked(createRun).mockResolvedValue({ id: `${status}-run`, status: 'queued' } as never);
    vi.mocked(getRun).mockResolvedValue({
      id: `${status}-run`, status, last_event_sequence: 1,
      exit_code: status === 'failed' ? 1 : null,
      error_category: status === 'failed' ? 'command_failed' : 'user_cancelled',
    } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, onEvent) => {
      listener = onEvent;
      return () => {};
    });

    const { getByRole } = render(
      <RunCoordinatorProvider>
        <RunnerPanel
          chapterId="03"
          checkpoints={[{ id: 'automatic_acceptance', command: 'python scripts/course_checkpoint.py --chapter 03', acceptance: '通过' }]}
          onExperimentComplete={onExperimentComplete}
        />
      </RunCoordinatorProvider>,
    );
    await act(async () => getByRole('button', { name: '运行' }).click());
    await vi.waitFor(() => expect(listener).toBeDefined());
    await act(async () => listener?.({
      run_id: `${status}-run`, sequence: 1, timestamp: '', kind: 'status',
      stream: '', text: `任务${status}`, status,
    }));

    await vi.waitFor(() => expect(onExperimentComplete).toHaveBeenCalledTimes(1));
  });
});
