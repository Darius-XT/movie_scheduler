#!/usr/bin/env python3
"""
影院数据采集脚本
运行此脚本将爬取所有影院数据并保存到数据库中
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.get_cinema_list import collect_and_save_cinemas, show_cinema_stats


def main():
    """主函数 - 采集影院数据"""
    print("🎬 影院数据采集脚本")
    print("=" * 50)

    # 采集上海的影院数据（默认）
    print("正在采集上海地区的影院数据...")
    collect_and_save_cinemas(keyword="影", city_id=10)

    print("\n" + "=" * 50)
    print("📊 数据库统计信息:")
    show_cinema_stats()

    print("\n✅ 影院数据采集完成！")


if __name__ == "__main__":
    main()
