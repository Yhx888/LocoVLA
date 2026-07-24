import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MarkdownView from './MarkdownView';
import RunnerPanel from '../runner/RunnerPanel';
import { RunCoordinatorProvider } from '../../run/RunCoordinator';
import { connectRunEvents, createRun, getRun } from '../../api/client';

vi.mock('../../api/client', () => ({
  createRun: vi.fn(),
  connectRunEvents: vi.fn(),
  getRun: vi.fn(),
  listRuns: vi.fn().mockResolvedValue([]),
  cancelRun: vi.fn(),
}));

function renderWithCoordinator(ui: React.ReactNode) {
  return render(<RunCoordinatorProvider>{ui}</RunCoordinatorProvider>);
}

describe('MarkdownView 代码块', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(connectRunEvents).mockReturnValue(() => {});
    vi.mocked(getRun).mockImplementation(async (id) => ({ id, status: 'succeeded' } as never));
  });

  it('将不可执行代码渲染为无运行按钮的阅读块', () => {
    const { getByText, queryByRole } = renderWithCoordinator(<MarkdownView content={'```python\nvalue = 1 + 1\n```'} chapterId="03" />);

    expect(queryByRole('button')).not.toBeInTheDocument();
    expect(getByText('python')).toBeInTheDocument();
    expect(getByText('value = 1 + 1')).toBeInTheDocument();
  });

  it('将单条脚本命令的唯一运行按钮放在代码下方', () => {
    const { container, getAllByRole, getByRole } = renderWithCoordinator(
      <MarkdownView content={'```powershell\npython scripts/course_checkpoint.py --chapter 03\n```'} chapterId="03" />,
    );

    const button = getByRole('button', { name: '运行' });
    const pre = container.querySelector('pre');
    expect(pre?.compareDocumentPosition(button)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(getAllByRole('button')).toHaveLength(1);
  });

  it('在前一条命令成功后才启动下一条命令', async () => {
    const eventListeners: Array<(event: { text: string; status: string | null }) => void> = [];
    vi.mocked(createRun)
      .mockResolvedValueOnce({ id: 'first' } as never)
      .mockResolvedValueOnce({ id: 'second' } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, listener) => {
      eventListeners.push(listener as never);
      return () => {};
    });

    const { getByRole } = renderWithCoordinator(
      <MarkdownView
        chapterId="03"
        content={'```powershell\npython scripts/run_foundation_lab.py --chapter 03 --seed 0\npython scripts/course_checkpoint.py --chapter 03\n```'}
      />,
    );

    await act(async () => {
      getByRole('button', { name: '运行全部（2）' }).click();
    });

    await vi.waitFor(() => expect(createRun).toHaveBeenCalledTimes(1));
    expect(createRun).toHaveBeenLastCalledWith('03', 'script', 'python scripts/run_foundation_lab.py --chapter 03 --seed 0');

    await act(async () => {
      eventListeners[0]({ text: '第一条完成', status: 'succeeded' });
      await Promise.resolve();
    });

    await vi.waitFor(() => expect(createRun).toHaveBeenCalledTimes(2));
    expect(createRun).toHaveBeenLastCalledWith('03', 'script', 'python scripts/course_checkpoint.py --chapter 03');
  });

  it('正文任务结束后立即释放右侧自动验收', async () => {
    const eventListeners: Array<(event: never) => void> = [];
    vi.mocked(createRun)
      .mockResolvedValueOnce({ id: 'code-run', status: 'queued' } as never)
      .mockResolvedValueOnce({ id: 'acceptance-run', status: 'queued' } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, listener) => {
      eventListeners.push(listener as never);
      return () => {};
    });

    const { container } = renderWithCoordinator(
      <>
        <MarkdownView
          chapterId="03"
          content={'```powershell\npython scripts/run_foundation_lab.py --chapter 03 --seed 0\n```'}
        />
        <RunnerPanel
          chapterId="03"
          checkpoints={[{
            id: 'automatic_acceptance',
            command: 'python scripts/course_checkpoint.py --chapter 03',
            acceptance: '通过',
          }]}
          onExperimentComplete={() => {}}
        />
      </>,
    );

    const codeBlock = container.querySelector('.lesson-code-block-runnable')!;
    const checkpoint = container.querySelector('.checkpoint-card')!;
    await act(async () => {
      (codeBlock.querySelector('button') as HTMLButtonElement).click();
    });

    await vi.waitFor(() => {
      expect(checkpoint.querySelector('button')).toBeDisabled();
    });

    await act(async () => {
      eventListeners[0]({
        run_id: 'code-run', sequence: 1, timestamp: '', kind: 'status',
        stream: '', text: '任务完成', status: 'succeeded',
      } as never);
    });

    await vi.waitFor(() => {
      expect(checkpoint.querySelector('button')).toBeEnabled();
    });
    await act(async () => {
      (checkpoint.querySelector('button') as HTMLButtonElement).click();
    });
    await vi.waitFor(() => expect(createRun).toHaveBeenCalledTimes(2));
  });

  it('WebSocket 断线后按序号补齐尾日志再释放任务', async () => {
    const connections: Array<{
      after: number;
      listener: (event: never) => void;
      disconnect?: () => void;
    }> = [];
    vi.mocked(createRun).mockResolvedValue({ id: 'reconnect-run', status: 'queued' } as never);
    vi.mocked(getRun).mockResolvedValue({
      id: 'reconnect-run', status: 'succeeded', last_event_sequence: 3, exit_code: 1,
      error_category: 'command_failed',
    } as never);
    vi.mocked(connectRunEvents).mockImplementation((_id, after, listener, disconnect) => {
      connections.push({ after, listener: listener as never, disconnect });
      return () => {};
    });

    const { container, getByText } = renderWithCoordinator(
      <>
        <MarkdownView chapterId="03" content={'```powershell\npython scripts/run_foundation_lab.py --chapter 03 --seed 0\n```'} />
        <RunnerPanel
          chapterId="03"
          checkpoints={[{ id: 'automatic_acceptance', command: 'python scripts/course_checkpoint.py --chapter 03', acceptance: '通过' }]}
          onExperimentComplete={() => {}}
        />
      </>,
    );

    await act(async () => {
      (container.querySelector('.lesson-code-block-runnable button') as HTMLButtonElement).click();
    });
    await vi.waitFor(() => expect(connections).toHaveLength(1));
    await act(async () => {
      connections[0].listener({
        run_id: 'reconnect-run', sequence: 1, timestamp: '', kind: 'stdout',
        stream: 'stdout', text: '开始', status: 'running',
      } as never);
      connections[0].disconnect?.();
    });

    await vi.waitFor(() => expect(connections).toHaveLength(2));
    expect(connections[1].after).toBe(1);
    await act(async () => {
      connections[1].listener({
        run_id: 'reconnect-run', sequence: 2, timestamp: '', kind: 'stderr',
        stream: 'stderr', text: '尾部错误', status: null,
      } as never);
      connections[1].listener({
        run_id: 'reconnect-run', sequence: 3, timestamp: '', kind: 'status',
        stream: '', text: '任务失败', status: 'failed',
      } as never);
    });

    await vi.waitFor(() => expect(getByText('尾部错误')).toBeInTheDocument());
    await vi.waitFor(() => {
      expect(container.querySelector('.checkpoint-card button')).toBeEnabled();
    });
  });
});
