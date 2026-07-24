import { act, render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getChapter, getCourseSummary, listRuns } from '../api/client';
import { RunCoordinatorProvider } from '../run/RunCoordinator';
import ChapterPage from './ChapterPage';

vi.mock('../api/client', () => ({
  artifactUrl: vi.fn((path: string) => `/api/artifacts/${path}`),
  cancelRun: vi.fn(),
  connectRunEvents: vi.fn(() => () => {}),
  createRun: vi.fn(),
  getChapter: vi.fn(),
  getCourseSummary: vi.fn(),
  getRun: vi.fn(),
  listRuns: vi.fn(),
  updateProgress: vi.fn(),
}));

vi.mock('../components/course/ProgressPanel', () => ({ default: () => null }));

describe('ChapterPage 移动端运行面板', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('innerWidth', 390);
    vi.mocked(getChapter).mockResolvedValue({
      id: '03', stage: '0', stage_title: '数学与工具', title: '测试章节', task: '',
      status: 'ready', prerequisites: [], content: '正文', reading_percent: 0,
      reading_complete: false, self_check_ids: [], self_check_items: [],
      experiment_accepted: false, completed: false, presets: [], artifacts: [],
      checkpoints: [{
        id: 'automatic_acceptance',
        command: 'python scripts/course_checkpoint.py --chapter 03',
        acceptance: '通过',
      }],
    });
    vi.mocked(getCourseSummary).mockResolvedValue({
      title: 'Upkie', version: '0.3.0', total_chapters: 1, completed_chapters: 0,
      next_chapter: null,
      stages: [{
        id: '0', title: '数学与工具', project: '', total: 1, ready: 1, completed: 0,
        chapters: [{
          id: '03', title: '测试章节', status: 'ready', completed: false,
          reading_complete: false, reading_percent: 0,
        }],
      }],
    });
    vi.mocked(listRuns).mockResolvedValue([]);
  });

  it('可打开并关闭验收抽屉', async () => {
    let view!: ReturnType<typeof render>;
    await act(async () => {
      view = render(
        <MemoryRouter
          initialEntries={['/chapter/03']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <RunCoordinatorProvider>
            <Routes><Route path="/chapter/:id" element={<ChapterPage />} /></Routes>
          </RunCoordinatorProvider>
        </MemoryRouter>,
      );
    });
    const { container, getByRole } = view;
    await vi.waitFor(() => expect(getByRole('button', { name: '展开实验面板' })).toBeInTheDocument());

    await act(async () => getByRole('button', { name: '展开实验面板' }).click());

    expect(container.querySelector('.chapter-runner')).not.toHaveClass('collapsed');
    await act(async () => getByRole('button', { name: '收起实验面板' }).click());
    expect(container.querySelector('.chapter-runner')).toHaveClass('collapsed');
  });
});
