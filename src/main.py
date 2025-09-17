from src.base.scraper import get_scraper
from src.processor.get_movie import get_movies
from src.processor.database.operations import MovieOperations
from src.base.logger import setup_logger

# 模块加载时初始化单例实例
logger = setup_logger()
scraper = get_scraper()

# TODO: 已确认, 抓取到的电影取决于 cookie 中的 movie_id
# TODO: 能不能动态得到网站服务器返回的 cookie 中的 movie_id, 不再手动配置 cookie?


def main():
    city = "上海"

    try:
        # 设置城市
        get_scraper(city)

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
