from src.base.scraper import get_scraper
from src.processor.get_movie import get_movies
from src.processor.database.operations import MovieOperations
from src.base.logger import setup_logger

# 模块加载时初始化单例实例
logger = setup_logger()
scraper = get_scraper()

# TODO: 现在只有第一页的抓取是正常的, 后面得到的结果都跟对应城市对不上(不属于任何一个正确页面), 而且切换城市后页面得到的内容不会变化
# TODO: 搞明白在浏览器中切换城市的逻辑


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
