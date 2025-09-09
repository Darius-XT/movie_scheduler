import requests
from fake_useragent import UserAgent


class HTMLFetcher:
    def __init__(self):
        # 生成反爬虫请求头
        def get_headers():
            return {
                "User-Agent": UserAgent(),
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

        self.session = requests.Session()  # 连接复用与cookie管理
        self.headers = get_headers()
        self.city_map = {
            "北京": 1,
            "上海": 10,
        }

    # 设置城市
    def set_city(self, city: str):
        self.session.cookies.set("ci", str(self.city_map[city]), domain="maoyan.com")
        self.session.cookies.set(
            "recentCis",
            f"{str(self.city_map[city])}%3D10%3D1245%3D1126%3D150",
            domain="maoyan.com",
        )

    def get_html(self, url: str) -> str:
        """核心功能：获取URL的HTML内容"""
        try:
            print(f"正在访问: {url}")

            # 打印当前session中的所有cookie
            print("当前session中的cookies:")
            for cookie in self.session.cookies:
                print(
                    f"  {cookie.name}={cookie.value} (domain={cookie.domain}, path={cookie.path})"
                )
            print()

            response = self.session.get(
                url,
                headers=self.headers,
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


if __name__ == "__main__":
    fetcher = HTMLFetcher()
    fetcher.set_city("上海")
    # 测试猫眼网站
    url = "https://www.maoyan.com"
    html_content = fetcher.get_html(url)

    # 显示前500个字符
    if html_content:
        with open("html_content.html", "w") as f:
            f.write(html_content)
    else:
        print("未能获取到HTML内容")
