import { act, fireEvent, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import QaAnswerBox from './QaAnswerBox';
import { getAiStatus, gradeAnswer } from '../../api/client';

vi.mock('../../api/client', () => ({
  getAiStatus: vi.fn(),
  gradeAnswer: vi.fn(),
  AI_CONFIG_UPDATED_EVENT: 'ai-config-updated',
}));

const PROPS = {
  qaId: '00-q1',
  question: '本关最关键的假设是什么？',
  answer: '参考答案：环境已正确配置。',
  chapterId: '00',
};

describe('QaAnswerBox 答题区与折叠参考答案', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.mocked(getAiStatus).mockResolvedValue({ configured: true, model: 'm' } as never);
  });

  it('答题区直接可见，参考答案默认折叠', async () => {
    const { getByRole, queryByText } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    expect(getByRole('textbox')).toBeInTheDocument();
    expect(getByRole('button', { name: /AI 评分/ })).toBeInTheDocument();
    expect(getByRole('button', { name: /参考答案/ })).toBeInTheDocument();
    expect(queryByText('参考答案：环境已正确配置。')).not.toBeInTheDocument();
  });

  it('点击参考答案条展开答案，再次点击收起', async () => {
    const { getByRole, getByText, queryByText } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    const toggle = getByRole('button', { name: /参考答案/ });
    fireEvent.click(toggle);
    expect(getByText('参考答案：环境已正确配置。')).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(queryByText('参考答案：环境已正确配置。')).not.toBeInTheDocument();
  });

  it('AI 未配置时评分按钮禁用并显示提示', async () => {
    vi.mocked(getAiStatus).mockResolvedValue({ configured: false, model: '' } as never);
    const { getByRole, getByText } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    fireEvent.change(getByRole('textbox'), { target: { value: '我的答案' } });

    expect(getByRole('button', { name: /AI 评分/ })).toBeDisabled();
    expect(getByText(/AI 未配置/)).toBeInTheDocument();
  });

  it('答案为空时评分按钮禁用，填写后启用', async () => {
    const { getByRole } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    const gradeBtn = getByRole('button', { name: /AI 评分/ });
    expect(gradeBtn).toBeDisabled();

    fireEvent.change(getByRole('textbox'), { target: { value: '环境配置好了' } });
    expect(gradeBtn).toBeEnabled();
  });

  it('评分成功后展示分数点评并自动展开参考答案', async () => {
    vi.mocked(gradeAnswer).mockResolvedValue({
      score: 7,
      comment: '接近参考答案',
      gaps: ['缺少失效信号'],
    } as never);
    const { getByRole, getByText } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    fireEvent.change(getByRole('textbox'), { target: { value: '环境配置好了' } });
    await act(async () => {
      fireEvent.click(getByRole('button', { name: /AI 评分/ }));
    });

    expect(gradeAnswer).toHaveBeenCalledWith({
      chapter_id: '00',
      question_id: '00-q1',
      question: PROPS.question,
      reference_answer: PROPS.answer,
      user_answer: '环境配置好了',
    });
    expect(getByText('得分 7 / 10')).toBeInTheDocument();
    expect(getByText('接近参考答案')).toBeInTheDocument();
    expect(getByText('缺少失效信号')).toBeInTheDocument();
    // 评分完成后自动展开标准答案
    expect(getByText('参考答案：环境已正确配置。')).toBeInTheDocument();
  });

  it('评分失败时显示错误信息且不展开参考答案', async () => {
    vi.mocked(gradeAnswer).mockRejectedValue(new Error('AI 助教未配置'));
    const { getByRole, getByText, queryByText } = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});

    fireEvent.change(getByRole('textbox'), { target: { value: '环境配置好了' } });
    await act(async () => {
      fireEvent.click(getByRole('button', { name: /AI 评分/ }));
    });

    expect(getByText('AI 助教未配置')).toBeInTheDocument();
    expect(queryByText('参考答案：环境已正确配置。')).not.toBeInTheDocument();
  });

  it('用户答案暂存 sessionStorage，重新挂载后恢复', async () => {
    const first = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});
    fireEvent.change(first.getByRole('textbox'), { target: { value: '暂存的答案' } });
    first.unmount();

    const second = render(<QaAnswerBox {...PROPS} />);
    await act(async () => {});
    expect(second.getByRole('textbox')).toHaveValue('暂存的答案');
  });
});
