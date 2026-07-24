import { act, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { connectRunEvents } from '../../api/client';
import ResultsView from './ResultsView';

vi.mock('../../api/client', () => ({
  artifactUrl: vi.fn((path: string) => `/api/artifacts/${path}`),
  connectRunEvents: vi.fn(),
}));

describe('ResultsView', () => {
  it('只显示当前章节的运行记录', () => {
    const runs = [
      {
        id: 'run-00', chapter_id: '00', preset_id: 'script', status: 'succeeded',
        created_at: '', finished_at: '', exit_code: 0, error_category: null,
      },
      {
        id: 'run-01', chapter_id: '01', preset_id: 'script', status: 'failed',
        created_at: '', finished_at: '', exit_code: 1, error_category: 'command_failed',
      },
    ] as const;

    const { queryByText, getByText } = render(
      <ResultsView chapterId="00" artifacts={[]} runs={[...runs]} />,
    );

    expect(getByText('成功')).toBeInTheDocument();
    expect(queryByText('失败')).not.toBeInTheDocument();
  });

  it('显示排队与中断状态', () => {
    const runs = [
      { id: 'queued', chapter_id: '12', preset_id: 'script', status: 'queued', created_at: '', finished_at: '', exit_code: null, error_category: null },
      { id: 'interrupted', chapter_id: '12', preset_id: 'script', status: 'interrupted', created_at: '', finished_at: '', exit_code: null, error_category: 'server_restart' },
    ] as const;
    const { getByText } = render(<ResultsView chapterId="12" artifacts={[]} runs={[...runs]} />);
    expect(getByText('排队中')).toBeInTheDocument();
    expect(getByText('已中断')).toBeInTheDocument();
  });

  it('展开失败记录后显示错误类别、退出码和尾日志', async () => {
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, onEvent) => {
      onEvent({
        run_id: 'failed', sequence: 1, timestamp: '', kind: 'stderr',
        stream: 'stderr', text: '最后一行错误', status: null,
      });
      onEvent({
        run_id: 'failed', sequence: 2, timestamp: '', kind: 'status',
        stream: '', text: '任务失败', status: 'failed',
      });
      return () => {};
    });
    const runs = [{
      id: 'failed', chapter_id: '12', preset_id: 'script', status: 'failed',
      created_at: '', finished_at: '', exit_code: 2, error_category: 'command_failed',
    }] as const;

    const { getByRole, getByText } = render(
      <ResultsView chapterId="12" artifacts={[]} runs={[...runs]} />,
    );
    await act(async () => getByRole('button', { name: '查看详情' }).click());

    expect(getByText('错误类别：command_failed')).toBeInTheDocument();
    expect(getByText('退出码：2')).toBeInTheDocument();
    expect(getByText('最后一行错误')).toBeInTheDocument();
    expect(getByText('任务失败')).toBeInTheDocument();
  });

  it('为终态记录提供重跑入口', () => {
    const onRerun = vi.fn();
    const runs = [{
      id: 'failed', chapter_id: '12', preset_id: 'script', status: 'failed',
      created_at: '', finished_at: '', exit_code: 1, error_category: 'command_failed',
    }] as const;
    const { getByRole } = render(
      <ResultsView chapterId="12" artifacts={[]} runs={[...runs]} onRerun={onRerun} />,
    );

    getByRole('button', { name: '重跑' }).click();

    expect(onRerun).toHaveBeenCalledWith(runs[0]);
  });
});
