"""放映日期解析器测试。"""

from app.use_cases.show_fetching.parsers.show_date_parser import show_date_parser


def test_show_date_parser_extracts_dates_from_json_payload() -> None:
    """解析器应从新接口返回的 JSON 中提取全部日期。"""
    payload = """
    {
      "code": 0,
      "data": {
        "dates": [
          {"date": "2026-04-08", "isPredate": 1, "labelResource": []},
          {"date": "2026-04-14", "isPredate": 0, "labelResource": []},
          {"date": "2026-04-15", "isPredate": 0, "labelResource": []}
        ]
      },
      "errMsg": "",
      "success": true
    }
    """

    assert show_date_parser.parse_showdate(payload) == [
        "2026-04-08",
        "2026-04-14",
        "2026-04-15",
    ]
