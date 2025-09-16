from src.model.scraper import scraper
from src.processor.get_movie import get_movies
from src.processor.database.operations import MovieOperations
from src.model.logger import logger

# TODO: 搞明白为什么网页显示的电影列表和请求时候的不一样


def main():
    city = "上海"

    try:
        # 设置城市
        scraper.set_city(city)

        total_movies = get_movies()

        logger.debug(f"本次抓取总计: {total_movies}部电影")

        # 显示最终统计
        with MovieOperations() as db_ops:
            stats = db_ops.get_statistics()
            logger.info(f"数据库中总电影数: {stats.get('total_movies', 0)}")

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()
