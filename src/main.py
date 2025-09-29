# 主函数, 调用需要的业务逻辑

from src.services.get_movie_list import get_movie_list
from src.services.get_movie_details import get_movie_details
from src.services.get_favorate_movies import get_favorite_movies
from src.logger import logger
import logging


def main():
    # 设置城市与日志级别
    logger.setLevel(logging.INFO)

    try:
        # 第一步：获取电影列表
        logger.info("=== 第一步：获取电影列表 ===")
        get_movie_list()

        # 第二步：获取电影详情
        logger.info("=== 第二步：获取电影详情 ===")
        get_movie_details()

        # 第三步：选择喜爱电影
        logger.info("=== 第三步：选择喜爱电影 ===")
        get_favorite_movies()

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()
