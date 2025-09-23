"""获取数据库中所有电影的详细信息"""

from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from src.operators.url_scrapers.movie_details_scraper import movie_details_scraper
from src.operators.html_parsers.movie_details_parser import parser
from src.logger import logger
from tqdm import tqdm


def get_movie_details() -> int:
    """获取数据库中所有电影的详细信息

    Returns:
        int: 成功获取详情的电影数量
    """
    logger.info("开始获取电影详细信息...")

    success_count = 0
    failure_count = 0

    try:
        # 获取数据库中所有电影
        with DBOperator(db_connector) as db_ops:
            # 只获取既没有导演也没有国家信息的电影（新增的电影）
            movies_without_details = db_ops.get_movies_without_details()

            if not movies_without_details:
                logger.info("没有需要补充详情的电影（所有电影都有详细信息）")
                return 0

            logger.info(
                f"找到 {len(movies_without_details)} 部需要补充详情的电影，开始获取详情..."
            )

            # 使用进度条显示处理进度
            progress_bar = tqdm(
                movies_without_details, desc="获取电影详情", unit="部", ncols=80
            )

            for movie in progress_bar:
                movie_id = int(movie.id)  # type: ignore
                # 更新进度条描述
                progress_bar.set_description(f"获取电影详情: {movie.title[:20]}...")

                try:
                    # 抓取电影详情
                    success, json_content = movie_details_scraper.scrape_movie_details(
                        movie_id
                    )

                    if not success or not json_content:
                        logger.warning(
                            f"获取电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    # 解析电影详情
                    movie_details = parser.parse_movie_details(json_content)

                    if not movie_details:
                        logger.warning(
                            f"解析电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    # 验证ID和标题是否一致
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
                        # 标题不匹配时，使用数据库中的标题
                        movie_details["title"] = movie.title

                    # 更新电影详情到数据库
                    if db_ops.save_movie(movie_details):
                        logger.info(f"成功更新电影详情: {movie.title} (ID: {movie_id})")
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

            # 进度条完成后的总结
            progress_bar.set_description("电影详情获取完成")
            progress_bar.close()

    except Exception as e:
        logger.error(f"获取电影详情过程中发生异常: {e}")
        return success_count

    # 打印统计信息
    logger.info("电影详情获取完成:")
    logger.info(f"  成功: {success_count} 部")
    logger.info(f"  失败: {failure_count} 部")
    logger.info(f"  总计: {success_count + failure_count} 部")

    return success_count


if __name__ == "__main__":
    import logging

    logger.setLevel(logging.DEBUG)
    get_movie_details()
