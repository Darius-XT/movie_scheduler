"""获取指定类型的所有电影(包括爬取, 解析, 更新数据库的完整流程)"""

from src.processor.database.operations import MovieOperations
from src.base.parser import parser
from src.base.logger import logger
from src.base.scraper import scraper


# 获取指定类型的所有电影, 并返回成功得到的电影数量
def get_movies() -> int:
    offset = 0
    total_movies = 0

    # 遍历所有电影类型
    for show_type in range(1, 3):
        show_type_name = "正在热映" if show_type == 1 else "即将上映"
        logger.info(f"开始抓取{show_type_name}电影...\n")

        offset = 0
        type_movies = 0

        # 对每种类型进行分页抓取
        while True:
            url = f"https://www.maoyan.com/films?showType={show_type}&offset={offset}"
            logger.debug(f"抓取{show_type_name}第{offset//18 + 1}页 (offset={offset})")

            try:
                # 获取HTML内容
                success, html_content = scraper.get_html(url)

                if not success or not html_content:
                    logger.warning(f"获取页面失败，跳过 offset={offset}")
                    break

                # 检查是否为空页面
                if parser.is_empty_page(html_content):
                    logger.debug(f"{show_type_name}电影抓取完毕，共{offset//18}页")
                    break

                # 解析电影数据
                movies_data = parser.parse_html_content(html_content)

                if not movies_data:
                    logger.error(
                        f"第{offset//18 + 1}页通过了空白页面检测, 但未解析到电影数据，结束抓取"
                    )
                    break

                # 保存到数据库
                with MovieOperations() as db_ops:
                    success_count, failure_count = db_ops.save_movies_batch(movies_data)
                    type_movies += success_count
                    total_movies += success_count
                    logger.debug(
                        f"第{offset//18 + 1}页: 成功保存{success_count}部电影，失败{failure_count}部"
                    )

                # 准备下一页
                offset += 18

            except Exception as e:
                logger.error(f"抓取第{offset//18 + 1}页异常: {e}")
                break

        logger.debug(f"{show_type_name}电影抓取完成，共抓取{type_movies}部电影")

    logger.info(f"所有电影抓取完成，总共成功抓取{total_movies}部电影")
    return total_movies
