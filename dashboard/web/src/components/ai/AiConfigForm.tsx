import { useEffect, useState } from 'react';
import { KeyRound, Loader2 } from 'lucide-react';
import { getAiStatus, saveAiConfig } from '../../api/client';
import type { AiStatusDto } from '../../api/types';

interface AiConfigFormProps {
  /** 保存成功后回调（状态已刷新），供上层收起表单。 */
  onSaved?: (status: AiStatusDto) => void;
  /** 取消/关闭表单回调。 */
  onCancel?: () => void;
}

const DEFAULT_BASE_URL = 'https://api.deepseek.com/v1';
const DEFAULT_MODEL = 'deepseek-chat';

/**
 * AI 助教配置表单：直接在前端填写 API key / base_url / model，
 * 提交后由后端写入 configs/course/ai.local.json，无需改文件或重启。
 */
export default function AiConfigForm({ onSaved, onCancel }: AiConfigFormProps) {
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [hasKey, setHasKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 打开表单时用当前生效配置预填 base_url / model（api_key 出于安全不回填）
  useEffect(() => {
    let cancelled = false;
    getAiStatus()
      .then((status) => {
        if (cancelled) return;
        setBaseUrl(status.base_url || DEFAULT_BASE_URL);
        setModel(status.model || DEFAULT_MODEL);
        setHasKey(Boolean(status.has_key));
      })
      .catch(() => {
        if (cancelled) return;
        setBaseUrl(DEFAULT_BASE_URL);
        setModel(DEFAULT_MODEL);
      });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async () => {
    if (saving) return;
    if (!baseUrl.trim() || !model.trim()) {
      setError('请填写 API 地址与模型名');
      return;
    }
    if (!hasKey && !apiKey.trim()) {
      setError('请填写 API key');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const status = await saveAiConfig({
        api_key: apiKey.trim(),
        base_url: baseUrl.trim(),
        model: model.trim(),
        enabled: true,
      });
      onSaved?.(status);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'AI 配置保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ai-config-form">
      <div className="ai-config-header">
        <KeyRound size={16} />
        <span>配置 AI 助教</span>
      </div>
      <p className="ai-config-desc">
        填写任意 OpenAI 兼容服务（DeepSeek、OpenAI、通义等）的密钥即可启用圈选解释、追问与答题评分。
        配置保存在服务器本地文件，不会提交到仓库。
      </p>

      <label className="ai-config-field">
        <span>API key{hasKey ? '（已配置，留空则保留原值）' : ''}</span>
        <input
          type="password"
          value={apiKey}
          autoComplete="off"
          placeholder={hasKey ? '••••••（已保存）' : 'sk-...'}
          onChange={(event) => setApiKey(event.target.value)}
        />
      </label>

      <label className="ai-config-field">
        <span>API 地址（base_url）</span>
        <input
          type="text"
          value={baseUrl}
          placeholder={DEFAULT_BASE_URL}
          onChange={(event) => setBaseUrl(event.target.value)}
        />
      </label>

      <label className="ai-config-field">
        <span>模型名（model）</span>
        <input
          type="text"
          value={model}
          placeholder={DEFAULT_MODEL}
          onChange={(event) => setModel(event.target.value)}
        />
      </label>

      {error && <p className="ai-config-error">{error}</p>}

      <div className="ai-config-actions">
        {onCancel && (
          <button type="button" className="ai-config-cancel" disabled={saving} onClick={onCancel}>
            取消
          </button>
        )}
        <button type="button" className="ai-config-save" disabled={saving} onClick={handleSubmit}>
          {saving ? <Loader2 size={14} className="ai-config-spin" /> : null}
          {saving ? '保存中...' : '保存并启用'}
        </button>
      </div>
    </div>
  );
}
