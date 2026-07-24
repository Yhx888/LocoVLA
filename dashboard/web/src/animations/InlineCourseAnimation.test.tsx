import { act, fireEvent, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InlineCourseAnimation from './InlineCourseAnimation';
import MarkdownView from '../components/course/MarkdownView';
import { RunCoordinatorProvider } from '../run/RunCoordinator';
import { connectRunEvents, createRun, getRun } from '../api/client';

vi.mock('../api/client', () => ({
  createRun: vi.fn(),
  connectRunEvents: vi.fn(() => () => {}),
  getRun: vi.fn(),
  listRuns: vi.fn().mockResolvedValue([]),
  cancelRun: vi.fn(),
}));

class IntersectionObserverMock {
  constructor(private callback: IntersectionObserverCallback) {}
  observe(element: Element) {
    this.callback([{ isIntersecting: true, target: element } as IntersectionObserverEntry], this as never);
  }
  disconnect() {}
  unobserve() {}
  takeRecords() { return []; }
  root = null;
  rootMargin = '';
  thresholds = [];
}

describe('正文课程动画', () => {
  beforeEach(() => {
    vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('参数滑块会改变可观察的数值和几何', () => {
    const { getByRole, getByTestId } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-parameter" /></RunCoordinatorProvider>,
    );
    const slider = getByRole('slider');
    const output = getByTestId('animation-output');
    const geometry = getByTestId('parameter-geometry');
    const before = output.getAttribute('data-value');
    const geometryBefore = geometry.getAttribute('transform');
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!;
      setter.call(slider, '9');
      slider.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(output.getAttribute('data-value')).not.toBe(before);
    expect(output.textContent).toContain('9');
    expect(geometry.getAttribute('transform')).not.toBe(geometryBefore);
  });

  it('减少动态效果时直接显示最终静态帧', () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const { getByTestId } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-intuition" /></RunCoordinatorProvider>,
    );
    expect(getByTestId('inline-animation')).toHaveAttribute('data-motion', 'reduced');
    expect(getByTestId('inline-animation')).toHaveAttribute('data-playing', 'false');
  });

  it('运行时切换减少动态效果会立即暂停并显示静态帧', () => {
    let onChange: ((event: MediaQueryListEvent) => void) | null = null;
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: (_type: string, handler: (event: MediaQueryListEvent) => void) => { onChange = handler; },
      removeEventListener: vi.fn(),
    }));
    const { getByTestId } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-intuition" /></RunCoordinatorProvider>,
    );
    act(() => onChange?.({ matches: true } as MediaQueryListEvent));
    expect(getByTestId('inline-animation')).toHaveAttribute('data-motion', 'reduced');
    expect(getByTestId('inline-animation')).toHaveAttribute('data-playing', 'false');
  });

  it('正文和大屏实例不会产生重复锚点或 SVG marker ID', () => {
    const { container } = render(
      <RunCoordinatorProvider>
        <InlineCourseAnimation animationId="12-intuition" />
        <InlineCourseAnimation animationId="12-intuition" large />
      </RunCoordinatorProvider>,
    );
    expect(container.querySelectorAll('#upkie-animation-12-intuition')).toHaveLength(1);
    const markerIds = Array.from(container.querySelectorAll('marker')).map((marker) => marker.id);
    expect(new Set(markerIds).size).toBe(markerIds.length);
  });

  it('机制场景在画布内展示当前章节语义', () => {
    const { getByTestId } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="25-intuition" /></RunCoordinatorProvider>,
    );
    expect(getByTestId('mechanism-scene')).toHaveTextContent(/Gymnasium/);
  });

  it.each([
    ['00-core', '岗位毕业项目'],
    ['43-core', 'FAULT'],
    ['47-core', '47题面试'],
  ])('非密集章节不会丢弃后段核心节点：%s', (animationId, expected) => {
    const { getByTestId, getByText } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId={animationId} /></RunCoordinatorProvider>,
    );
    expect(getByTestId('mechanism-scene')).toBeInTheDocument();
    expect(getByText(expected, { exact: true })).toBeInTheDocument();
  });

  it('减少动态效果静态帧与正常播放完成后的终帧一致', () => {
    vi.useFakeTimers();
    const normal = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-intuition" /></RunCoordinatorProvider>,
    );
    const initialX = normal.getByTestId('motion-token').getAttribute('cx');
    act(() => vi.advanceTimersByTime(3600));
    const completedX = normal.getByTestId('motion-token').getAttribute('cx');
    expect(completedX).not.toBe(initialX);
    normal.unmount();

    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const reduced = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-intuition" /></RunCoordinatorProvider>,
    );
    expect(reduced.getByTestId('motion-token').getAttribute('cx')).toBe(completedX);
  });

  it('正确与故障对比在画布内使用当前章节诊断语义', () => {
    const { getByTestId } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="32-comparison" /></RunCoordinatorProvider>,
    );
    expect(getByTestId('comparison-scene')).toHaveTextContent(/分层任务架构/);
  });

  it('证据缺失时显示生成命令和运行入口', () => {
    const { getByRole, getByText } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-evidence" /></RunCoordinatorProvider>,
    );
    act(() => {
      getByRole('img').dispatchEvent(new Event('error', { bubbles: true }));
    });
    expect(getByText(/course_checkpoint.py --chapter 12/)).toBeInTheDocument();
    expect(getByRole('button', { name: '生成证据' })).toBeInTheDocument();
  });

  it('证据生成成功后会重新请求真实产物', async () => {
    vi.mocked(createRun).mockResolvedValue({
      id: 'evidence-run', chapter_id: '12', preset_id: 'animation-evidence', status: 'queued',
      created_at: '', finished_at: '', exit_code: null, error_category: null,
    });
    vi.mocked(getRun).mockResolvedValue({
      id: 'evidence-run', chapter_id: '12', preset_id: 'animation-evidence', status: 'succeeded',
      created_at: '', finished_at: '', exit_code: 0, error_category: null, last_event_sequence: 1,
    });
    vi.mocked(connectRunEvents).mockImplementation((_id, _after, onEvent) => {
      queueMicrotask(() => onEvent({
        run_id: 'evidence-run', sequence: 1, timestamp: '', kind: 'status', stream: '',
        text: 'done', status: 'succeeded',
      }));
      return () => {};
    });
    const { getByRole } = render(
      <RunCoordinatorProvider><InlineCourseAnimation animationId="12-evidence" /></RunCoordinatorProvider>,
    );
    const image = getByRole('img') as HTMLImageElement;
    const originalSrc = image.src;
    fireEvent.error(image);
    fireEvent.click(getByRole('button', { name: '生成证据' }));
    await waitFor(() => expect(getByRole('img')).not.toHaveAttribute('src', originalSrc));
  });

  it('Markdown 标记在正文位置渲染对应动画', () => {
    const { getByTestId, getByText } = render(
      <RunCoordinatorProvider>
        <MarkdownView chapterId="12" content={'前文\n\n<!-- upkie-animation:12-intuition -->\n\n后文'} />
      </RunCoordinatorProvider>,
    );
    expect(getByTestId('inline-animation')).toBeInTheDocument();
    expect(getByText('直觉机制：反馈控制闭环')).toBeInTheDocument();
  });
});
