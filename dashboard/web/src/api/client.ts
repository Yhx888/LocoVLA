import type { ChapterDto, CourseSummary, ProgressRecord, RunRecord, RunEvent, ArtifactDto, HealthDto } from './types';

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
