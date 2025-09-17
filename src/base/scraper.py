"""爬取HTML内容"""

import requests
from singleton_decorator import singleton
from src.base.logger import setup_logger
from src.config import settings

# 城市映射常量
CITY_MAPPING = {
    "北京": 1,
    "上海": 10,
}

# Cookie模板常量 - 包含城市ID占位符
COOKIE_TEMPLATE = "__mta=216316201.1756952460622.1757923756387.1757989065410.19; uuid_n_v=v1; uuid=C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA; _csrf=f9b6559b1b01185a39433a65b188cb83193b343236faa3555dc69a7b5d2a9505; _ga=GA1.1.200491387.1756952456; Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1756952460; HMACCOUNT=FAC79C52BFC838B4; _lxsdk_cuid=1991286fcf4c8-0502fc73ab8c0c-16525636-384000-1991286fcf5c8; _lxsdk=C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA; _lx_utm=utm_source%3Dgoogle%26utm_medium%3Dorganic; comingMovieIds=1207331,1547375,1565240,1538211,1470975,1524039,1360592,1552050,1389785,1527959,1595812,1500265,1522764,1416590,1548780,1489329,257609,1526767,1523868,1303013,1470096,1355795,1520391,1593640,1515498,1490987,1548214,1228042,1518527,1471073,1297975,484024,1523963,1506370,1457158,1573266,1505776,1500340,1528920,1487870,1529836,1527147,1536795,1572309,1251132,1489355,1399324,1428854,1502253,1504204,1501817,1536843,1491440,1478868,1531501,1552202,1533022,1550284,1530742,1525896,1531752,1565162,1370922,1491711,1504105,1340084,1535808,1501767,1371106,356895,1519878,1490546,1523850,1254449,1461184,1429503,4430,1531115,1395127,346650,1518012,1422798,1491824,1522873,1489992,1490085,1528598,1490646,1376912,1491455,1371742,1502895,1498191,1298556,1469785,1504573,1501854,1479540,1528908,1399234,1471072,1463806,1500853,1505654,1528899,1504556,1499664,1519992,1489955,1520846,1443420,1491283,1515510,1373968,1505531,1431804,1505554,1491759,1462732,1545360,1522535,572277,1519937,1568094,1565186,1543619; ci={city_id}; recentCis={city_id}%3D1%3D50%3D1245%3D1126; hotMovieIds=1515448,1298226,1505571,1500636,1207331,1522657,1520596,1542730,1454962,1547424,1523743,1511555,1531082,343898,1522287,1562636,1469373,1432141,1575780,1499719,1509826,1489326,1547375,1552050,1530145,1498162,1547369,1461072,1538211,4895,1536837,1592162,1490948,94,1496400,1516994,1431675,9714,1559961,122157,1480618,1320548,1518617,1250604,6823,1302189,1288259,158,1289244,8778,1206,1547294,1462651,36688,1360592,1250679,1487834,1470975,40308,1528424,1566861,1524039,1572273,1584781,1525122,246386,1568020,1413194,1524059,207516,273622,6730,9840,231767,15720,14943,253331,1294,1317,233746,300,596040,1300301,1337941,1462221,1490285,1449451,1477714,1542925,1447819,1500899,1492737,1512657,1427899,1491476,1551836,1528363,1321801,1489531; old-moviepage-ci={city_id}; global-guide-isclose=true; Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1758112967; __mta=216316201.1756952460622.1757989065410.1758112966687.20; _ga_WN80P4PSY7=GS2.1.s1758112949$o41$g1$t1758113302$j60$l0$h0; _lxsdk_s=19957b2a336-b9b-2f9-d41%7C%7C5"

# 请求头配置基础模板（不包含Cookie）
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Host": "www.maoyan.com",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}


class Scraper:
    def __init__(self, city: str | None = None):
        self.city = city or settings.city
        self.city_id = self._get_city_id(self.city)

        # 生成包含cookie的请求头
        self.headers = self._build_headers()
        self.session = requests.Session()  # 连接复用与cookie管理

    def _get_city_id(self, city: str) -> int:
        """获取城市ID"""
        return CITY_MAPPING.get(city, CITY_MAPPING[settings.city])

    def _build_headers(self) -> dict:
        """构建包含Cookie的请求头"""
        # 复制基础请求头
        headers = DEFAULT_HEADERS.copy()

        # 生成包含城市ID的Cookie
        cookie = COOKIE_TEMPLATE.format(city_id=self.city_id)
        headers["Cookie"] = cookie

        return headers

    def get_html(self, url: str) -> tuple[bool, str]:
        """核心功能：获取URL的HTML内容

        Returns:
            tuple[bool, str]: (是否成功, HTML内容)
        """
        try:
            setup_logger().debug(f"开始爬取URL: {url}")

            # 记录当前请求头中的Cookie
            setup_logger().debug(f"当前请求头中的Cookie: {self.headers['Cookie']}")

            response = self.session.get(
                url,
                headers=self.headers,
                timeout=settings.request_timeout,
                allow_redirects=settings.request_allow_redirects,
            )

            setup_logger().debug(f"response状态码: {response.status_code}")
            setup_logger().debug(f"最终URL: {response.url}")
            setup_logger().debug(f"HTML长度: {len(response.text)} 字符")

            if response.status_code == 200:
                setup_logger().debug("成功获取HTML内容")
                return True, response.text
            else:
                setup_logger().warning(f"请求失败，状态码: {response.status_code}")
                return False, ""

        except Exception as e:
            setup_logger().error(f"获取HTML失败: {e}")
            return False, ""


@singleton
def get_scraper(city: str = settings.city) -> Scraper:
    """惰性创建并返回 Scraper 单例。"""
    city = city or settings.city
    return Scraper(city)
