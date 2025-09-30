"""影院数据更新器（由原 get_cinema_list 迁移）"""

from .cinema_list_scraper import update_cinema_scraper
from .cinema_list_parser import update_cinema_parser
from src.db.db_operator import DBOperator
from src.logger import logger


class CinemaUpdater:
    def update_cinema(self, keyword: str = "影", city_id: int = 10):
        city_names = {1: "北京", 10: "上海"}
        city_name = city_names.get(city_id, f"城市{city_id}")

        logger.info(f"开始采集{city_name}的影院数据...")

        # 爬取影院数据
        success, raw_content = update_cinema_scraper.scrape(
            keyword=keyword, city_id=city_id
        )
        if not success or not raw_content:
            logger.warning("没有获取到影院数据")
            return 0, 0

        # 解析影院数据
        cinemas_data = update_cinema_parser.parse(raw_content)
        if not cinemas_data:
            logger.warning("解析后没有获取到影院数据")
            return 0, 0

        logger.info(f"成功解析到 {len(cinemas_data)} 家影院数据")

        # 保存到数据库
        with DBOperator() as db_op:
            success_count, failure_count = db_op.save_cinemas_batch(cinemas_data)

        logger.info(
            f"数据保存完成: 成功保存 {success_count} 家，失败 {failure_count} 家"
        )

        # 显示统计信息
        with DBOperator() as db_op:
            db_op.print_statistics()

        return success_count, failure_count


cinema_updater = CinemaUpdater()
