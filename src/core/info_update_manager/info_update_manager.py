"""信息更新器（整合所有信息更新功能）"""

from typing import Dict, Any, Callable, Optional
from src.core.info_update_manager.all_movie_info_updater.all_movie_info_updater import (
    AllMovieInfoUpdater,
)
from src.core.info_update_manager.all_cinema_info_updater.all_cinema_info_updater import (
    AllCinemaInfoUpdater,
)


class InfoUpdateManager:
    def __init__(self):
        self.movie_info_updater = AllMovieInfoUpdater()
        self.cinema_info_updater = AllCinemaInfoUpdater()

    def update_movie_info(
        self,
        city_id: int = 10,
        force_update_all: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """仅更新电影信息

        Args:
            city_id (int): 城市ID。
                默认为 10（上海）。
                示例值: 1, 10
            force_update_all (bool): 是否强制完全更新。
                如果为 True，会先删除 movies 表中的所有数据，然后重新抓取和保存。
                默认为 False，使用增量更新（只添加新电影，删除下架电影）。
                示例值: False, True
            progress_callback (callable, 可选): 进度回调函数。
                回调函数接收一个参数: (message: str)
                - message: 进度消息，如 "正在抓取电影列表" 或 "正在补充详细信息 (5/10)"

        Returns:
            Dict[str, Any]: 电影信息更新统计，包含以下字段：
                - base_info (Dict[str, int]): 基础信息更新统计
                    - added (int): 新增电影数量，例如: 5
                    - removed (int): 删除电影数量，例如: 2
                    - total (int): 当前数据库中的电影总数，例如: 150
                - extra_info (Dict[str, int]): 额外信息更新统计
                    - updated_count (int): 成功更新详情的电影数量，例如: 10
                - error (str, 可选): 如果发生异常，包含错误信息

            示例返回值:
                {
                    "base_info": {
                        "added": 5,
                        "removed": 2,
                        "total": 150
                    },
                    "extra_info": {
                        "updated_count": 10
                    }
                }
        """
        return self.movie_info_updater.update_all_movie_info(
            city_id, force_update_all, progress_callback
        )

    def update_cinema_info(
        self,
        city_id: int = 10,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """仅更新影院信息

        Args:
            city_id (int): 影院所在城市的ID。
                默认为 10。
                示例值: 1, 10
            progress_callback (callable, 可选): 进度回调函数。
                回调函数接收一个参数: (message: str)
                - message: 进度消息，如 "正在更新城市 10 的影院信息: 第 2 页"

        Returns:
            Dict[str, Any]: 影院信息更新统计，包含以下字段：
                - success_count (int): 成功保存的影院数量，例如: 25
                - failure_count (int): 保存失败的影院数量，例如: 0

            示例返回值:
                {
                    "success_count": 25,
                    "failure_count": 0
                }
        """
        success_count, failure_count = self.cinema_info_updater.update_all_cinema_info(
            city_id=city_id, progress_callback=progress_callback
        )
        return {
            "success_count": success_count,
            "failure_count": failure_count,
        }


info_update_manager = InfoUpdateManager()
