from src.operators.url_scraper import scraper
from src.services.get_movie import get_movies
from src.db.db_operator import DBOperator
from src.db.db_connector import db_connector
from src.logger import logger
import logging


def main():
    # 设置城市与日志级别
    logger.setLevel(logging.INFO)
    scraper.set_city("上海")

    try:
        get_movies()

        # 显示最终统计
        with DBOperator(db_connector) as db_ops:
            db_ops.get_statistics()

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()

# TODO: 现在已经可以取得列表中的电影信息, 但仍然缺失: 电影国家, 电影简介, 电影在哪些影院上映, 上映的时间是什么时候, 目前还有什么座位可以选, 每个座位的票价是多少
