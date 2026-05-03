"""影院场次解析器测试。"""

from app.show.show_client import show_client


def test_cinema_show_parser_falls_back_to_vip_price_when_discount_price_is_stonefont() -> None:
    """当普通价格字段是 stonefont HTML 片段时，应回退到明文 VIP 价格。"""
    payload = """
    {
      "data": {
        "cinemaId": 10,
        "cinemaName": "测试影院",
        "movies": [
          {
            "id": 1,
            "nm": "测试电影",
            "shows": [
              {
                "showDate": "2026-04-08",
                "plist": [
                  {
                    "tm": "20:45",
                    "discountSellPrice": "<span class=\\"stonefont\\">&#xf3e8;&#xea6f;</span>",
                    "vipDisPrice": "32",
                    "vipPrice": "35"
                  }
                ]
              }
            ]
          }
        ]
      }
    }
    """

    result = show_client.parse(payload, "测试电影")

    assert len(result) == 1
    assert result[0].price == "32"


def test_cinema_show_parser_filters_to_target_show_date() -> None:
    """指定日期时应只返回该日期的场次。"""
    payload = """
    {
      "data": {
        "cinemaId": 10,
        "cinemaName": "测试影院",
        "movies": [
          {
            "id": 1,
            "nm": "测试电影",
            "shows": [
              {
                "showDate": "2026-04-08",
                "plist": [
                  {
                    "tm": "20:45",
                    "discountSellPrice": "32"
                  }
                ]
              },
              {
                "showDate": "2026-04-09",
                "plist": [
                  {
                    "tm": "21:30",
                    "discountSellPrice": "36"
                  }
                ]
              }
            ]
          }
        ]
      }
    }
    """

    result = show_client.parse(payload, "测试电影", "2026-04-09")

    assert len(result) == 1
    assert result[0].show_date == "2026-04-09"
    assert result[0].show_time == "21:30"
