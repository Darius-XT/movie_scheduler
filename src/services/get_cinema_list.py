"""影院数据采集服务"""

import logging
from src.operators.scrapers.cinema_list_scraper import cinema_list_scraper
from src.operators.parsers.cinema_list_parser import parser as cinema_parser
from src.db.db_operator import DBOperator
from src.logger import logger


def collect_and_save_cinemas(keyword: str = "影", city_id: int = 10):
    """采集并保存影院数据到数据库

    Args:
        keyword: 搜索关键词
        city_id: 城市ID (1=北京, 10=上海)
    """
    city_names = {1: "北京", 10: "上海"}
    city_name = city_names.get(city_id, f"城市{city_id}")

    logger.info(f"开始采集{city_name}的影院数据...")

    try:
        # 爬取影院数据
        success, raw_content = cinema_list_scraper.scrape_cinema_page(
            keyword=keyword, city_id=city_id
        )

        if not success or not raw_content:
            logger.warning("没有获取到影院数据")
            return

        # 解析影院数据
        cinemas_data = cinema_parser.parse_cinema_list(raw_content)

        if not cinemas_data:
            logger.warning("解析后没有获取到影院数据")
            return

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

    except Exception as e:
        logger.error(f"采集影院数据时发生错误: {e}")


if __name__ == "__main__":
    # 设置日志级别为DEBUG以查看详细过程
    logger.setLevel(logging.INFO)

    print("=== 影院数据采集服务单元测试 ===\n")

    # 采集并保存上海的影院数据
    collect_and_save_cinemas(keyword="影", city_id=10)
