# 主函数, 调用需要的业务逻辑

from src.services.update_data.update_movie.update_movie_item.update_movie_item import (
    update_movie_item,
)
from src.services.update_data.update_movie.update_movie_detail.update_movie_detail import (
    update_movie_detail,
)
from src.services.select_movie.select_movie import select_movie
from src.logger import logger
import logging


def main():
    # 设置城市与日志级别
    logger.setLevel(logging.INFO)

    try:
        # 第一步：获取电影列表
        logger.info("=== 第一步：获取电影列表 ===")
        update_movie_item()

        # 第二步：获取电影详情
        logger.info("=== 第二步：获取电影详情 ===")
        update_movie_detail()

        # 第三步：选择喜爱电影
        logger.info("=== 第三步：选择喜爱电影 ===")
        select_movie()

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()

# TODO: 重构整个项目, 按
