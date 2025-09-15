from src.core.scraper import scraper
from src.core.parser import parser
from src.database.operations import MovieOperations
from src.core.logger import logger


def main() -> bool:
    url = "https://www.maoyan.com/films?showType=1&offset=72"
    city = "上海"

    try:
        # 1. 设置城市
        scraper.set_city(city)

        # 2. 获取HTML内容
        success, html_content = scraper.get_html(url)

        if not success or not html_content:
            return False

        # 3. 解析电影数据
        movies_data = parser.parse_html_content(html_content)

        if not movies_data:
            return False

        # 4. 保存到数据库
        with MovieOperations() as db_ops:
            success_count, failure_count = db_ops.save_movies_batch(movies_data)

            if success_count > 0:
                # 显示统计信息
                stats = db_ops.get_statistics()
                logger.info(f"数据库中总电影数: {stats.get('total_movies', 0)}")

                return True
            else:
                logger.error("没有成功保存任何电影数据")
                return False

    except Exception as e:
        logger.error(f"流程异常: {e}")
        return False


if __name__ == "__main__":
    main()
