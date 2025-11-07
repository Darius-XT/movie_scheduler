"""更新所有电影信息（整合基础信息和额外信息）"""

from typing import Dict, Any
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

    def update_all_movie_info(self) -> Dict[str, Any]:
        """更新所有电影信息（包括基础信息和额外信息）

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
        logger.info("=== 开始更新所有电影信息 ===")

        result: Dict[str, Any] = {}

        try:
            # 第一步：更新电影基础信息（电影列表）
            logger.info("=== 第一步：更新电影基础信息 ===")
            base_info_stats = self.base_info_updater.update_all_movie_base_info()
            result["base_info"] = base_info_stats

            # 第二步：更新电影额外信息（电影详情）
            logger.info("=== 第二步：更新电影额外信息 ===")
            extra_info_count = self.extra_info_updater.update_all_movie_extra_info()
            result["extra_info"] = {"updated_count": extra_info_count}

            logger.info("=== 所有电影信息更新完成 ===")
            logger.info(
                f"基础信息: 新增 {base_info_stats.get('added', 0)} 部, "
                f"删除 {base_info_stats.get('removed', 0)} 部, "
                f"总计 {base_info_stats.get('total', 0)} 部"
            )
            logger.info(f"额外信息: 更新 {extra_info_count} 部电影详情")

            return result

        except Exception as e:
            logger.error(f"更新所有电影信息时发生异常: {e}")
            result["error"] = str(e)
            return result


all_movie_info_updater = AllMovieInfoUpdater()
