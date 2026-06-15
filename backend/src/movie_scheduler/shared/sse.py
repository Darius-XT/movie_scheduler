"""SSE 流式编排:统一封装 progress / complete / error 帧。

将 cinema / movie / show 三处的 (progress_callback → asyncio.Queue → 文本帧)
样板抽到一个帮手, 业务层只需要提供:
    - run: 真正执行任务的协程工厂, 入参是 push_progress
    - map_error: 异常 → 用户可读消息的映射
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable


async def stream_with_progress(
    run: Callable[[Callable[[dict[str, object]], None]], Awaitable[dict[str, object]]],
    map_error: Callable[[Exception], str],
) -> AsyncIterator[str]:
    """运行 run, 把进度事件与完成 / 错误结果序列化为 SSE 文本帧。

    run 接收一个线程安全的 push_progress 回调, 应在每个进度节点调用它推送
    `{"type": "progress", ...}` 形态以外的字段(stage / message 等);返回 dict
    会被包成 `{"type": "complete", "data": <返回值>}`。
    """
    event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def push_progress(payload: dict[str, object]) -> None:
        merged: dict[str, object] = {"type": "progress", **payload}
        loop.call_soon_threadsafe(event_queue.put_nowait, merged)

    async def run_with_capture() -> None:
        try:
            data = await run(push_progress)
            complete_event: dict[str, object] = {"type": "complete", "data": data}
            loop.call_soon_threadsafe(event_queue.put_nowait, complete_event)
        except Exception as error:
            error_event: dict[str, object] = {"type": "error", "error": map_error(error)}
            loop.call_soon_threadsafe(event_queue.put_nowait, error_event)
        finally:
            loop.call_soon_threadsafe(event_queue.put_nowait, None)

    task = asyncio.create_task(run_with_capture())
    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    finally:
        if not task.done():
            task.cancel()


__all__ = ["stream_with_progress"]
