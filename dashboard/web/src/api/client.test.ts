import { afterEach, describe, expect, it, vi } from 'vitest';
import { connectRunEvents, createRun } from './client';

class WebSocketMock {
  static instances: WebSocketMock[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    WebSocketMock.instances.push(this);
  }

  close() {
    this.onclose?.({} as CloseEvent);
  }
}

describe('API 客户端运行契约', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    WebSocketMock.instances = [];
  });

  it('保留 409 响应中的 active_run_id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: { message: '已有任务在运行中', active_run_id: 'busy-run' },
    }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    })));

    await expect(createRun('03', 'script', 'python scripts/demo.py')).rejects.toMatchObject({
      message: 'HTTP 409: 已有任务在运行中',
      status: 409,
      activeRunId: 'busy-run',
    });
  });

  it('主动关闭连接时不触发断线恢复', () => {
    vi.stubGlobal('WebSocket', WebSocketMock);
    const onDisconnect = vi.fn();
    const close = connectRunEvents('run-1', 0, () => {}, onDisconnect);

    close();

    expect(onDisconnect).not.toHaveBeenCalled();
  });

  it('同一次错误和关闭只通知一次断线', () => {
    vi.stubGlobal('WebSocket', WebSocketMock);
    const onDisconnect = vi.fn();
    connectRunEvents('run-1', 0, () => {}, onDisconnect);
    const socket = WebSocketMock.instances[0];

    socket.onerror?.({} as Event);
    socket.onclose?.({} as CloseEvent);

    expect(onDisconnect).toHaveBeenCalledTimes(1);
  });
});
