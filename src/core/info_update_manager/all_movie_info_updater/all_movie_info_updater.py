"""更新所有电影信息（整合基础信息和额外信息）"""

from typing import Dict, Any, Callable, Optional
from src.core.info_update_manager.all_movie_info_updater.all_movie_base_info_updater.all_movie_base_info_updater import (
    all_movie_base_info_updater,
)
from src.core.info_update_manager.all_movie_info_updater.all_movie_extra_info_updater.all_movie_extra_info_updater import (
    all_movie_extra_info_updater,
)
from src.utils.logger import logger


class AllMovieInfoUpdater:
    def __init__(self):
        self.base_info_updater = all_movie_base_info_updater
        self.extra_info_updater = all_movie_extra_info_updater

    def update_all_movie_info(
        self,
        city_id: int = 10,
        force_update_all: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """更新所有电影信息（包括基础信息和额外信息）

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
            Dict[str, Any]: 包含两个步骤的统计信息，结构如下：
                - base_info (Dict[str, int]): 基础信息更新统计
                    - added (int): 新增电影数量，例如: 5
                    - removed (int): 删除电影数量，例如: 2
                    - total (int): 当前数据库中的电影总数，例如: 150
                - extra_info (Dict[str, int]): 额外信息更新统计
                    - updated_count (int): 成功更新详情的电影数量，例如: 10
                - error (str, 可选): 如果发生异常，包含错误信息字符串

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

            异常情况示例:
                {
                    "error": "更新所有电影信息时发生异常: Connection timeout"
                }
        """
        logger.info(
            f"=== 开始更新所有电影信息（城市ID: {city_id}, 强制完全更新: {force_update_all}）==="
        )

        result: Dict[str, Any] = {}

        try:
            # 如果 force_update_all 为 True，先删除所有电影
            if force_update_all:
                from src.db.db_operate_manager import db_operate_manager

                logger.info("强制完全更新模式：正在删除所有现有电影数据...")
                if db_operate_manager.delete_all_movies():
                    logger.info("所有电影数据已删除，开始重新抓取...")
                else:
                    logger.warning("删除所有电影数据失败，但将继续执行更新操作")

            # 第一步：更新电影基础信息（电影列表）
            base_info_stats = self.base_info_updater.update_all_movie_base_info(
                city_id, progress_callback=progress_callback
            )
            result["base_info"] = base_info_stats

            # 第二步：更新电影额外信息（电影详情）
            extra_info_count = self.extra_info_updater.update_all_movie_extra_info(
                force_update_all=force_update_all, progress_callback=progress_callback
            )
            result["extra_info"] = {"updated_count": extra_info_count}

            logger.info("=== 所有电影信息更新完成 ===")
            return result

        except Exception as e:
            logger.error(f"更新所有电影信息时发生异常: {e}")
            result["error"] = str(e)
            return result


all_movie_info_updater = AllMovieInfoUpdater()
