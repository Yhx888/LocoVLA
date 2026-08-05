import type {
  ChapterDto, CourseSummary, ProgressRecord, RunRecord, RunEvent, ArtifactDto, HealthDto,
  AiStatusDto, AiConfigRequest, AiExplainRequest, AiGradeRequest, AiGradeResult,
} from './types';

const BASE = '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly activeRunId: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, init);
  if (!resp.ok) {
    let detail = resp.statusText;
    let activeRunId: string | null = null;
    try {
      const body = await resp.json();
      detail = typeof body.detail === 'string'
        ? body.detail
        : body.detail?.message ?? JSON.stringify(body.detail);
      activeRunId = typeof body.detail?.active_run_id === 'string'
        ? body.detail.active_run_id
        : null;
    } catch {}
    throw new ApiError(`HTTP ${resp.status}: ${detail}`, resp.status, activeRunId);
  }
  return resp.json();
}

export async function getHealth(): Promise<HealthDto> {
  return fetchJSON('/health');
}

export async function getCourseSummary(): Promise<CourseSummary> {
  return fetchJSON('/course');
}

export async function getChapter(id: string): Promise<ChapterDto> {
  return fetchJSON(`/chapters/${id}`);
}

/** 删除章节实验验收结果（后端删除验收结果文件并清缓存）。 */
export async function resetExperiment(chapterId: string): Promise<{ deleted: string[] }> {
  return fetchJSON(`/experiments/${encodeURIComponent(chapterId)}`, { method: 'DELETE' });
}

export async function updateProgress(chapterId: string, record: ProgressRecord): Promise<void> {
  await fetch(`${BASE}/progress/${chapterId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
}

export async function createRun(chapterId: string, presetId: string, command?: string): Promise<RunRecord> {
  const body: Record<string, string> = { chapter_id: chapterId, preset_id: presetId };
  if (command) body.command = command;
  return fetchJSON('/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function listRuns(chapterId?: string): Promise<RunRecord[]> {
  const query = chapterId ? `?chapter_id=${encodeURIComponent(chapterId)}` : '';
  return fetchJSON(`/runs${query}`);
}

export async function getRun(runId: string): Promise<RunRecord & { last_event_sequence: number }> {
  return fetchJSON(`/runs/${runId}`);
}

export async function cancelRun(runId: string): Promise<void> {
  await fetchJSON(`/runs/${runId}/cancel`, { method: 'POST' });
}

export function connectRunEvents(
  runId: string,
  after: number,
  onEvent: (event: RunEvent) => void,
  onDisconnect?: () => void,
): () => void {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/api/runs/${runId}/events?after=${after}`;
  const ws = new WebSocket(wsUrl);
  let intentionalClose = false;
  let disconnectNotified = false;

  const notifyDisconnect = () => {
    if (intentionalClose || disconnectNotified) return;
    disconnectNotified = true;
    onDisconnect?.();
  };

  ws.onmessage = (msg) => {
    try {
      const event: RunEvent = JSON.parse(msg.data);
      onEvent(event);
    } catch {
      // 忽略解析错误
    }
  };
  ws.onerror = notifyDisconnect;
  ws.onclose = notifyDisconnect;

  return () => {
    intentionalClose = true;
    ws.onerror = null;
    ws.onclose = null;
    ws.close();
  };
}

export function artifactUrl(path: string): string {
  return `${BASE}/artifacts/${path}`;
}

// ── AI 助教 ──

let aiStatusCache: Promise<AiStatusDto> | null = null;

/** 查询 AI 服务可用状态（模块级缓存，失败不缓存）。 */
export function getAiStatus(): Promise<AiStatusDto> {
  if (!aiStatusCache) {
    aiStatusCache = fetchJSON<AiStatusDto>('/ai/status').catch((error) => {
      aiStatusCache = null;
      throw error;
    });
  }
  return aiStatusCache;
}

/** AI 配置更新后广播事件名，供各处入口重新拉取状态。 */
export const AI_CONFIG_UPDATED_EVENT = 'ai-config-updated';

/**
 * 提交 AI 配置到后端（写入 ai.local.json），成功后清空状态缓存并广播事件，
 * 让页面上所有 AI 入口（助教面板、答题评分）同步刷新。
 */
export async function saveAiConfig(body: AiConfigRequest): Promise<AiStatusDto> {
  const status = await fetchJSON<AiStatusDto>('/ai/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  aiStatusCache = Promise.resolve(status);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(AI_CONFIG_UPDATED_EVENT));
  }
  return status;
}

export async function gradeAnswer(body: AiGradeRequest): Promise<AiGradeResult> {
  return fetchJSON('/ai/grade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/** 流式请求 AI 解释，逐段回调增量文本；遇后端错误事件时抛 ApiError。 */
export async function streamExplain(
  body: AiExplainRequest,
  onDelta: (delta: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${BASE}/ai/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const errorBody = await resp.json();
      detail = typeof errorBody.detail === 'string' ? errorBody.detail : JSON.stringify(errorBody.detail);
    } catch {}
    throw new ApiError(`HTTP ${resp.status}: ${detail}`, resp.status);
  }
  if (!resp.body) {
    throw new ApiError('浏览器不支持流式响应', 0);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const handleEvent = (raw: string) => {
    const line = raw.trim();
    if (!line.startsWith('data:')) return;
    const payload = line.slice(5).trim();
    if (payload === '[DONE]') return;
    let parsed: { delta?: string; error?: string };
    try {
      parsed = JSON.parse(payload);
    } catch {
      return;
    }
    if (parsed.error) throw new ApiError(parsed.error, 502);
    if (parsed.delta) onDelta(parsed.delta);
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let separator = buffer.indexOf('\n\n');
    while (separator !== -1) {
      handleEvent(buffer.slice(0, separator));
      buffer = buffer.slice(separator + 2);
      separator = buffer.indexOf('\n\n');
    }
  }
  if (buffer.trim()) handleEvent(buffer);
}

