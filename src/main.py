from src.core.scraper import scraper

if __name__ == "__main__":
    scraper.set_city("上海")
    url = "https://www.maoyan.com/films?showType=1&offset=72"
    html_file_path = "src/data/html_content.html"

    scraper.get_and_save_html(url, html_file_path)
