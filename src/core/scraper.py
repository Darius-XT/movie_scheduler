import requests
from src.config.logger_config import logger


class Scraper:
    def __init__(self):
        # 生成反爬虫请求头
        def get_headers():
            # 设置cookies字符串（用于Cookie请求头）
            set_cookies = "__mta=216316201.1756952460622.1757579996782.1757581024561.15; uuid_n_v=v1; uuid=C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA; _csrf=f9b6559b1b01185a39433a65b188cb83193b343236faa3555dc69a7b5d2a9505; _ga=GA1.1.200491387.1756952456; Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1756952460; HMACCOUNT=FAC79C52BFC838B4; _lxsdk_cuid=1991286fcf4c8-0502fc73ab8c0c-16525636-384000-1991286fcf5c8; comingMovieIds=1498162,1592162,1320548,1524059,1520596,1487834,1413318,1469373,1499719,1593966,1496400,1207331,1547375,1565240,1470975,1524039,1360592,1552050,1389785,1527959,1500265,1522764,1416590,1548780,1526767,1523868,1303013,1470096,1515498,1490987,1548214,1228042,1518527,1471073,1297975,484024,1523963,1506370,1457158,1573266,1505776,1500340,1528920,1487870,1529836,1527147,1536795,1572309,1251132,1399324,1428854,1504204,1501817,1536843,1491440,1489329,1478868,1531501,1552202,1533022,1550284,1530742,1525896,1531752,1370922,1491711,1504105,1340084,1535808,1501767,1371106,356895,1519878,1490546,1523850,1254449,1461184,257609,1429503,4430,1531115,1395127,1518012,346650,1491824,1422798,1489992,1490085,1490646,1528598,1522873,1376912,1371742,1491455,1502895,1498191,1469785,1298556,1504573,1501854,1479540,1528908,1399234,1471072,1463806,1500853,1505654,1528899,1504556,1499664,1519992,1489955,1520846,1443420,1491283,1515510,1373968,1505531,1431804,1505554,1491759,1462732,1545360,1522535,572277,1519937,1565186,1543619; _lxsdk=C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA; _lx_utm=utm_source%3Dgoogle%26utm_medium%3Dorganic; ci=1; recentCis=1%3D10%3D1245%3D1126%3D150; old-moviepage-ci=1; global-guide-isclose=true; hotMovieIds=1515448,1298226,1505571,1520596,1522657,1500636,1432141,1207331,1531082,1523743,1499719,1522287,1454962,1542730,1547424,1496400,343898,1575780,1489326,1511555,1562636,1469373,1592162,1516994,1547369,1461072,1530145,9714,1250604,1498162,1320548,1547375,1572273,1536837,1538211,1490948,1491476,36688,1518617,1250679,1552050,1566861,1462651,40308,1487834,1431675,1559961,1509826,1528424,1470975,1568020,1545629,1584781,1415196,1583990,1360592,1302189,1547294,1413318,1534647,171,1500899,246386,1475139,1589374,1227946,207516,273622,4895,6730,9840,8778,231767,15720,14943,1206,233746,94,158,6823,596040,1289244,1480618,1490285,1449451,1447819,1525228; _ga_WN80P4PSY7=GS2.1.s1757910205$o29$g1$t1757910453$j2$l0$h0; Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1757910454; __mta=216316201.1756952460622.1757581024561.1757910454024.16; _lxsdk_s=1994b9d0228-cd8-eec-971%7C%7C13"
            return {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Cookie": set_cookies,  # 添加cookies到请求头
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

        self.session = requests.Session()  # 连接复用与cookie管理
        self.headers = get_headers()
        self.city_map = {
            "北京": 1,
            "上海": 10,
        }

    # 设置城市
    def set_city(self, city: str):
        if city not in self.city_map:
            logger.error(f"不支持的城市: {city}")
            return

        self.session.cookies.set("ci", str(self.city_map[city]), domain="maoyan.com")
        self.session.cookies.set(
            "recentCis",
            f"{str(self.city_map[city])}%3D10%3D1245%3D1126%3D150",
            domain="maoyan.com",
        )
        logger.info(f"城市设置为: {city} (ID: {self.city_map[city]})")

    def get_html(self, url: str) -> str:
        """核心功能：获取URL的HTML内容"""
        try:
            logger.info(f"正在访问: {url}")

            # 记录当前session中的所有cookie
            if self.session.cookies:
                logger.debug("当前session中的cookies:")
                for cookie in self.session.cookies:
                    logger.debug(
                        f"  {cookie.name}={cookie.value} (domain={cookie.domain}, path={cookie.path})"
                    )
            else:
                logger.debug("当前session中没有cookies")

            response = self.session.get(
                url,
                headers=self.headers,
                timeout=15,  # 设置超时时间
                allow_redirects=True,  # 允许重定向
            )

            logger.info(f"response状态码: {response.status_code}")
            logger.info(f"最终URL: {response.url}")
            logger.info(f"HTML长度: {len(response.text)} 字符")

            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"获取HTML失败: {e}")
            return ""


scraper = Scraper()
