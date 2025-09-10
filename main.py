from HTMLFetcher import fetcher
from logger_config import logger

if __name__ == "__main__":
    fetcher.set_city("上海")
    url = "https://www.maoyan.com"
    html_content = fetcher.get_html(url)

    # 保存HTML内容到文件
    if html_content:
        with open("html_content.html", "w") as f:
            f.write(html_content)
        logger.info("HTML内容已保存到 html_content.html")
    else:
        logger.error("未能获取到HTML内容")
