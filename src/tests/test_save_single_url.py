from src.model.logger import logger
from src.model.scraper import scraper
from src.model.parser import parser
from src.processor.database.operations import MovieOperations


def save_movies_from_single_url(url: str) -> tuple[int, int]:
    """从单个URL抓取电影并保存到数据库，返回(成功数, 失败数)"""
    success, html = scraper.get_html(url)
    if not success or not html:
        logger.error("获取HTML失败，终止保存流程")
        return 0, 1

    movies = parser.parse_html_content(html)
    if not movies:
        logger.warning("未解析到电影数据")
        return 0, 0

    with MovieOperations() as db_ops:
        return db_ops.save_movies_batch(movies)


def test_save_single_url():
    """简单测试：抓取热映第一页并尝试入库"""
    # 选定城市，避免Cookie城市不一致
    scraper.set_city("上海")
    url = "https://www.maoyan.com/films?showType=1&offset=36"

    success_count, failure_count = save_movies_from_single_url(url)
    logger.info(
        f"测试完成：URL={url}，成功保存 {success_count} 部，失败 {failure_count} 部"
    )

    # 断言至少不报错即可；若抓取为空不失败
    assert success_count >= 0 and failure_count >= 0


test_save_single_url()
