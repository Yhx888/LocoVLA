import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the API client
vi.mock('./api/client', () => ({
  getCourseSummary: vi.fn().mockResolvedValue({
    title: 'Upkie 运动控制课程',
    version: '0.3.0',
    total_chapters: 58,
    completed_chapters: 0,
    next_chapter: null,
    stages: [
      { id: '0', title: '数学与工具', project: '测试', total: 6, ready: 6, completed: 0 },
      { id: '1', title: '机器人仿真', project: '测试', total: 6, ready: 6, completed: 0 },
    ],
  }),
  getChapter: vi.fn(),
  updateProgress: vi.fn(),
  createRun: vi.fn(),
  listRuns: vi.fn().mockResolvedValue([]),
  getRun: vi.fn(),
  cancelRun: vi.fn(),
  connectRunEvents: vi.fn(() => () => {}),
  artifactUrl: vi.fn((p: string) => `/api/artifacts/${p}`),
  getHealth: vi.fn().mockResolvedValue({ status: 'ready' }),
}));

import App from './App';

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('innerWidth', 1440);
  });

  it('renders cockpit page at root', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    // 等待异步渲染完成
    await vi.waitFor(() => {
      expect(container.textContent).toContain('Upkie');
    }, { timeout: 5000 });
  });

  it('在移动端仍然渲染课程而不是阻断提示', async () => {
    vi.stubGlobal('innerWidth', 800);
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    await vi.waitFor(() => {
      expect(container.textContent).toContain('Upkie');
      expect(container.textContent).not.toContain('屏幕宽度不足');
    });
  });

  it('将后端 ready 映射为就绪', async () => {
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    await vi.waitFor(() => {
      expect(container.textContent).toContain('就绪');
    });
  });
});
