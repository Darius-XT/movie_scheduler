"""更新电影详情"""

from typing import Callable, Optional
from src.db.db_operate_manager import db_operate_manager
from src.core.info_update_manager.all_movie_info_updater.all_movie_extra_info_updater.json_with_single_movie_extra_info_scraper import (
    JsonWithSingleMovieExtraInfoScraper,
)
from src.core.info_update_manager.all_movie_info_updater.all_movie_extra_info_updater.json_with_single_movie_extra_info_parser import (
    JsonWithSingleMovieExtraInfoParser,
)
from src.utils.logger import logger


class AllMovieExtraInfoUpdater:
    def __init__(self):
        self.scraper = JsonWithSingleMovieExtraInfoScraper()
        self.parser = JsonWithSingleMovieExtraInfoParser()

    # * 注意: 由于 M 站返回的发行日期格式不固定, 有时可以提取到日期列表, 有时只有一个日期, 有时甚至只有年份, 固统一仅提取年份, 并且在各版本列表中仅保留第一个
    def update_all_movie_extra_info(
        self,
        force_update_all: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """更新所有电影的额外信息（导演、国家、语言、时长、简介等）

        Args:
            force_update_all (bool): 是否强制更新所有电影。
                如果为 True，将更新所有电影（不判断是否缺少详细信息）。
                如果为 False（默认），只更新缺少详细信息的电影。
                示例值: False, True
            progress_callback (callable, 可选): 进度回调函数。
                回调函数接收一个参数: (message: str)
                - message: 进度消息，如 "正在补充详细信息 (5/10)"

        Returns:
            int: 成功更新详情的电影数量。
                例如: 10 表示成功更新了10部电影的详细信息。
                如果所有电影都已包含详细信息且 force_update_all=False，返回 0。
        """
        if force_update_all:
            logger.info("开始强制更新所有电影的详细信息...")
        else:
            logger.info("开始获取电影详细信息...")

        success_count = 0
        failure_count = 0

        try:
            if force_update_all:
                movies_to_update = db_operate_manager.get_all_movies()
                if not movies_to_update:
                    logger.info("数据库中没有电影")
                    return 0
                logger.info(f"找到 {len(movies_to_update)} 部电影，开始强制更新详情...")
            else:
                movies_to_update = db_operate_manager.get_movies_without_details()
                if not movies_to_update:
                    logger.info("没有需要补充详情的电影（所有电影都有详细信息）")
                    return 0
                logger.info(
                    f"找到 {len(movies_to_update)} 部需要补充详情的电影，开始获取详情..."
                )

            total_movies = len(movies_to_update)
            for idx, movie in enumerate(movies_to_update, 1):
                movie_id = int(movie.id)  # type: ignore
                logger.debug(f"正在获取电影详情: {movie.title} (ID: {movie_id})")

                # 更新进度
                if progress_callback:
                    progress_callback(f"正在补充详细信息 ({idx}/{total_movies})")

                try:
                    success, json_content = (
                        self.scraper.scrape_json_with_single_movie_extra_info(movie_id)
                    )

                    if not success or not json_content:
                        logger.warning(
                            f"获取电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    movie_details = self.parser.parse_json_with_single_movie_extra_info(
                        json_content
                    )

                    if not movie_details:
                        logger.warning(
                            f"解析电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    if movie_details.get("id") != movie_id:
                        logger.error(
                            f"电影ID不匹配: 数据库ID={movie_id}, 解析ID={movie_details.get('id')}"
                        )
                        failure_count += 1
                        continue

                    if movie_details.get("title") != movie.title:
                        logger.warning(
                            f"电影标题不匹配: 数据库标题='{movie.title}', 解析标题='{movie_details.get('title')}'"
                        )
                        movie_details["title"] = movie.title

                    if db_operate_manager.save_movie(movie_details):
                        logger.debug(
                            f"成功更新电影详情: {movie.title} (ID: {movie_id})"
                        )
                        success_count += 1
                    else:
                        logger.error(
                            f"保存电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1

                except Exception as e:
                    logger.error(
                        f"处理电影 {movie.title} (ID: {movie_id}) 时发生异常: {e}"
                    )
                    failure_count += 1
                    continue

        except Exception as e:
            logger.error(f"获取电影详情过程中发生异常: {e}")
            return success_count

        logger.info(
            "额外电影信息更新统计: 成功: %d 部, 失败: %d 部, 总计: %d 部",
            success_count,
            failure_count,
            success_count + failure_count,
        )

        return success_count


all_movie_extra_info_updater = AllMovieExtraInfoUpdater()

if __name__ == "__main__":
    success_count = all_movie_extra_info_updater.update_all_movie_extra_info(
        force_update_all=True
    )
    print(f"成功更新 {success_count} 部电影详情")
