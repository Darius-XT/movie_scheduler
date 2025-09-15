from src.core.scraper import scraper
from src.core.parser import parser
from src.config.logger_config import logger

if __name__ == "__main__":
    scraper.set_city("上海")
    url = "https://www.maoyan.com/films?showType=1&offset=72"
    html_content = scraper.get_html(url)

    # 保存HTML内容到文件
    html_file_path = "src/data/html_content.html"
    if html_content:
        with open(html_file_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        logger.info("HTML内容已保存到 html_content.html")
        
        # 解析HTML并提取电影信息
        movies = parser.parse_html_file(html_file_path)
        
        if movies:
            # 保存电影信息到JSON文件
            json_file_path = "src/data/movies.json"
            success = parser.save_to_json(movies, json_file_path)
            
            if success:
                logger.info(f"成功提取并保存了 {len(movies)} 部电影的信息")
            else:
                logger.error("保存电影信息失败")
        else:
            logger.error("未能提取到电影信息")
    else:
        logger.error("未能获取到HTML内容")
