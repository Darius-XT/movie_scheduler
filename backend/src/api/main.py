"""FastAPI 后端服务"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import queue

from src.core.info_update_manager.info_update_manager import info_update_manager
from src.core.movie_selector.movie_selector import movie_selector
from src.core.show_for_selected_movie_fetcher.show_for_selected_movie_fetcher import (
    show_for_selected_movie_fetcher,
)
from src.config_manager.config_manager import config_manager

app = FastAPI(title="Movie Scheduler API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Pydantic 模型 =====
class UpdateCinemaRequest(BaseModel):
    city_id: int


class UpdateMovieRequest(BaseModel):
    city_id: int
    force_update_all: bool = False


class SelectMovieRequest(BaseModel):
    year_threshold: Optional[int] = None


class FetchShowsRequest(BaseModel):
    movie_ids: List[int]
    use_async: bool = True


# ===== API 端点 =====
@app.get("/")
async def root():
    """根路径"""
    return {"message": "Movie Scheduler API"}


@app.get("/api/cities")
async def get_cities() -> Dict[str, Any]:
    """获取所有可用的城市列表"""
    city_mapping = config_manager.city_mapping or {}
    cities = [{"name": name, "id": city_id} for name, city_id in city_mapping.items()]
    return {"cities": cities}


@app.post("/api/update/cinema")
async def update_cinema(request: UpdateCinemaRequest) -> Dict[str, Any]:
    """更新影院信息"""
    try:
        result = await asyncio.to_thread(
            info_update_manager.update_cinema_info, city_id=request.city_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/update/movie")
async def update_movie(request: UpdateMovieRequest) -> Dict[str, Any]:
    """更新电影信息"""
    try:
        result = await asyncio.to_thread(
            info_update_manager.update_movie_info,
            city_id=request.city_id,
            force_update_all=request.force_update_all,
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/movies/select")
async def select_movies(request: SelectMovieRequest) -> Dict[str, Any]:
    """筛选电影"""
    try:
        movies = await asyncio.to_thread(
            movie_selector.select_movie, year_threshold=request.year_threshold
        )
        return {"success": True, "data": {"movies": movies, "count": len(movies)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/shows/fetch")
async def fetch_shows(request: FetchShowsRequest) -> Dict[str, Any]:
    """获取选中电影的场次信息"""
    try:
        shows = await asyncio.to_thread(
            show_for_selected_movie_fetcher.fetch_shows_for_selected_movies,
            movie_ids=request.movie_ids,
            use_async=request.use_async,
        )
        return {"success": True, "data": {"shows": shows, "count": len(shows)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/shows/fetch-stream")
async def fetch_shows_stream(movie_ids: str, use_async: bool = True):
    """使用 SSE 流式获取场次信息并实时推送进度"""

    # 解析电影 ID 列表（格式：1,2,3）
    movie_id_list = [int(id.strip()) for id in movie_ids.split(",") if id.strip()]

    async def generate():
        progress_queue = queue.Queue()

        def progress_callback(progress_data):
            """进度回调函数，将进度信息放入队列"""
            progress_queue.put(progress_data)

        # 在后台线程中执行获取操作
        async def fetch_task():
            try:
                result = await asyncio.to_thread(
                    show_for_selected_movie_fetcher.fetch_shows_for_selected_movies,
                    movie_ids=movie_id_list,
                    progress_callback=progress_callback,
                    use_async=use_async,
                )
                # 发送完成信号
                progress_queue.put({"type": "complete", "data": result})
            except Exception as e:
                # 发送错误信号
                progress_queue.put({"type": "error", "error": str(e)})

        # 启动后台任务
        task = asyncio.create_task(fetch_task())

        try:
            # 持续从队列中读取进度并发送
            while True:
                await asyncio.sleep(0.1)  # 避免过于频繁

                # 尝试获取所有可用的进度更新
                updates = []
                try:
                    while not progress_queue.empty():
                        update = progress_queue.get_nowait()
                        updates.append(update)
                except queue.Empty:
                    pass

                # 发送所有更新
                for update in updates:
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"

                    # 如果是完成或错误，结束流
                    if update.get("type") in ["complete", "error"]:
                        return

                # 检查任务是否异常结束
                if task.done():
                    try:
                        task.result()
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
                    return

        except asyncio.CancelledError:
            task.cancel()
            raise

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
