"""影院数据更新器（由原 get_cinema_list 迁移）"""

from src.core.info_update_manager.all_cinema_info_updater.json_with_batch_cinema_info_scraper import (
    JsonWithBatchCinemaInfoScraper,
)
from src.core.info_update_manager.all_cinema_info_updater.json_with_batch_cinema_info_parser import (
    JsonWithBatchCinemaInfoParser,
)
from src.db.db_operate_manager import db_operate_manager
from src.utils.logger import logger


class AllCinemaInfoUpdater:
    def __init__(self):
        self.scraper = JsonWithBatchCinemaInfoScraper()
        self.parser = JsonWithBatchCinemaInfoParser()

    def update_all_cinema_info(
        self, keyword: str = "影", city_id: int = 10
    ) -> tuple[int, int]:
        """更新所有影院信息（从猫眼API抓取影院数据）

        Args:
            keyword (str): 影院搜索关键词，用于搜索影院名称。
                默认为 "影"。
                示例值: "影", "电影院", "影院"
            city_id (int): 影院所在城市的ID。
                默认为 10。
                示例值: 1, 10

        Returns:
            tuple[int, int]: (成功保存数量, 失败数量)
                第一个元素是成功保存的影院数量，例如: 25
                第二个元素是保存失败的影院数量，例如: 0
                示例返回值: (25, 0)
        """
        logger.info(f"开始采集城市ID={city_id}的影院数据...")

        all_cinemas_data = []
        page = 1

        while True:
            logger.debug(f"抓取第{page}页影院数据")

            # 爬取影院数据
            success, raw_content = self.scraper.scrape_json_with_batch_cinema_info(
                keyword=keyword, city_id=city_id, page=page
            )

            if not success or not raw_content:
                logger.warning(f"获取第{page}页失败，结束抓取")
                break

            # 解析影院数据
            cinemas_data = self.parser.parse_json_with_batch_cinema_info(raw_content)

            if not cinemas_data:
                logger.debug(
                    f"第{page}页解析结果为空，影院数据抓取完毕，共{page - 1}页"
                )
                break

            logger.debug(f"第{page}页: 解析到{len(cinemas_data)}家影院")
            all_cinemas_data.extend(cinemas_data)
            page += 1

        if not all_cinemas_data:
            logger.warning("没有获取到任何影院数据")
            return 0, 0

        logger.info(f"成功解析到 {len(all_cinemas_data)} 家影院数据（共{page - 1}页）")

        # 保存到数据库
        success_count, failure_count = db_operate_manager.save_cinemas_batch(
            all_cinemas_data
        )

        logger.info(
            f"数据保存完成: 成功保存 {success_count} 家，失败 {failure_count} 家"
        )

        # 显示统计信息
        db_operate_manager.print_statistics()

        return success_count, failure_count


all_cinema_info_updater = AllCinemaInfoUpdater()
