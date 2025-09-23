from src.services.get_movie_list import get_movie_list
from src.services.get_movie_details import get_movie_details
from src.logger import logger
import logging


def main():
    # 设置城市与日志级别
    logger.setLevel(logging.INFO)

    try:
        # 第一步：获取电影列表
        logger.info("=== 第一步：获取电影列表 ===")
        list_stats = get_movie_list()

        # 第二步：获取电影详情
        logger.info("=== 第二步：获取电影详情 ===")
        details_count = get_movie_details()

        # 显示最终统计
        logger.info("=== 最终统计 ===")
        logger.info(
            f"电影列表更新: 新增{list_stats['added']}部, 删除{list_stats['removed']}部"
        )
        logger.info(f"电影详情更新: 成功获取{details_count}部新增电影的详细信息")
        logger.info(f"数据库中总电影数: {list_stats['total']}部")

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()
