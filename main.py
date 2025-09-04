import requests
import time
import random
from fake_useragent import UserAgent


class SimpleHTMLFetcher:
    def __init__(self):
        self.session = requests.Session()  # 连接复用与cookie管理
        self.ua = UserAgent()  # 使用fake_useragent库随机生成User-Agent

    def get_headers(self):
        """生成反爬虫请求头"""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    def get_html(self, url: str) -> str:
        """核心功能：获取URL的HTML内容"""
        try:
            print(f"正在访问: {url}")

            # 随机延迟
            time.sleep(random.uniform(1, 3))

            response = self.session.get(
                url,
                headers=self.get_headers(),
                timeout=15,  # 设置超时时间
                allow_redirects=True,  # 允许重定向
            )

            print(f"状态码: {response.status_code}")
            print(f"最终URL: {response.url}")
            print(f"HTML长度: {len(response.text)} 字符")

            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return ""

        except Exception as e:
            print(f"获取HTML失败: {e}")
            return ""


def get_url_html(url: str) -> str:
    """核心功能：获取任意URL的HTML内容"""
    fetcher = SimpleHTMLFetcher()

    html = fetcher.get_html(url)

    if html:
        # 保存到文件
        filename = f"{url.replace('https://', '').replace('http://', '').replace('/', '_').replace('?', '_').replace(':', '_')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"HTML已保存到: {filename}")

    return html


if __name__ == "__main__":
    # 测试猫眼网站
    url = "https://www.maoyan.com"
    html_content = get_url_html(url)

    # 显示前500个字符
    if html_content:
        print("\n前500个字符:")
        print("-" * 50)
        print(html_content[:500])
    else:
        print("未能获取到HTML内容")
