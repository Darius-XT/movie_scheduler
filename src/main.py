from src.base.scraper import get_scraper
from src.processor.get_movie import get_movies
from src.processor.database.operations import MovieOperations
from src.base.logger import setup_logger
import logging

# TODO: 已确认, 抓取到的电影取决于 cookie 中的 movie_id
# TODO: 能不能动态得到网站服务器返回的 cookie 中的 movie_id, 不再手动配置 cookie?


def main():
    # 在主函数中首先初始化logger，确保它是第一次调用
    logger = setup_logger(level=logging.INFO)
    get_scraper("上海")

    try:
        get_movies()

        # 显示最终统计
        with MovieOperations() as db_ops:
            db_ops.get_statistics()

    except Exception as e:
        logger.error(f"主流程异常: {e}")
        return


if __name__ == "__main__":
    main()
