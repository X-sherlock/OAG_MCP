#!/usr/bin/env python3
"""Create ifundtest.ifund_all_info and upsert deterministic development data."""

from __future__ import annotations

import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

SEED_ROWS = [
    {
        "COD_FUND": "000001", "NAM_FUND": "稳健价值混合A", "NAM_FUND_SHORT": "稳健价值",
        "COD_FUND_TYP": "01", "COD_FUND_STS": "01", "COD_FUND_RSK_LVL": "03",
        "COD_FUND_LIVE_STS": "0", "COD_PURC_STS": "2", "COD_REDM_STS": "1",
        "AMT_IDV_FST_SSCR_MIN": 1000, "AMT_IDV_FST_PURC_MIN": 100, "AMT_AIP_MIN": 100,
        "AMT_AIP_MAX": 50000, "AMT_FUND_SCL": 2500000000, "DATE_FUND_MKT": "20180115",
        "DATE_FUND_CRT": "20171220", "VLU_FUND_NAV": 1.2531, "VLU_FUND_NAV_ACML": 2.0478,
        "VLU_NAV_GRTH_YEAR": 0.166, "VLU_NAV_GRTH_3_MTH": 0.043, "VLU_NAV_GRTH_6_MTH": 0.082,
        "VLU_NAV_GRTH_THIS_YEAR": 0.086, "VLU_MAX_DD_YEAR": -0.061, "VLU_MAX_DD_3_MTH": -0.025,
        "VLU_MAX_DD_6_MTH": -0.036, "VLU_STD_YEAR": 0.118, "VLU_SHARP_YEAR": 1.28,
        "ID_RET_KIND_YEAR_RANK": 14, "ID_VLU_MAX_DD_KIND_RANK_YEAR": 27,
        "ID_STD_KIND_RANK_YEAR": 20, "ID_SHARP_KIND_RANK_YEAR": 13, "VLU_EX_BM_YEAR": 0.052,
        "NAM_MAGR_1": "张晨", "DAYS_OF_MAGR_1": 3200, "AMT_MAGR_SCL_1": 18000000000,
        "VLU_MAGR_TERM_RET_1": 86.5, "DATE_STRT_1": "20180115",
        "PCT_STOCK_ASSET": 62.5, "PCT_CCY_ASSET": 4.0, "PCT_BOND_ASSET": 28.0,
        "PCT_OTHER_ASSET": 5.5, "PCT_FUND_ASSET": 0.0, "NAM_CMPY": "华夏示例基金管理有限公司",
    },
    {
        "COD_FUND": "000002", "NAM_FUND": "成长先锋股票A", "NAM_FUND_SHORT": "成长先锋",
        "COD_FUND_TYP": "02", "COD_FUND_STS": "01", "COD_FUND_RSK_LVL": "05",
        "COD_FUND_LIVE_STS": "0", "COD_PURC_STS": "2", "COD_REDM_STS": "1",
        "AMT_IDV_FST_SSCR_MIN": 1000, "AMT_IDV_FST_PURC_MIN": 100, "AMT_AIP_MIN": 100,
        "AMT_AIP_MAX": 50000, "AMT_FUND_SCL": 4200000000, "DATE_FUND_MKT": "20200310",
        "DATE_FUND_CRT": "20200201", "VLU_FUND_NAV": 1.6842, "VLU_FUND_NAV_ACML": 2.3510,
        "VLU_NAV_GRTH_YEAR": 0.306, "VLU_NAV_GRTH_3_MTH": 0.081, "VLU_NAV_GRTH_6_MTH": 0.153,
        "VLU_NAV_GRTH_THIS_YEAR": 0.142, "VLU_MAX_DD_YEAR": -0.142, "VLU_MAX_DD_3_MTH": -0.064,
        "VLU_MAX_DD_6_MTH": -0.092, "VLU_STD_YEAR": 0.246, "VLU_SHARP_YEAR": 1.05,
        "ID_RET_KIND_YEAR_RANK": 8, "ID_VLU_MAX_DD_KIND_RANK_YEAR": 68,
        "ID_STD_KIND_RANK_YEAR": 65, "ID_SHARP_KIND_RANK_YEAR": 37, "VLU_EX_BM_YEAR": 0.101,
        "NAM_MAGR_1": "李锐", "DAYS_OF_MAGR_1": 2600, "AMT_MAGR_SCL_1": 12500000000,
        "VLU_MAGR_TERM_RET_1": 114.2, "DATE_STRT_1": "20200310",
        "NAM_MAGR_2": "周宁", "DAYS_OF_MAGR_2": 1800, "AMT_MAGR_SCL_2": 6800000000,
        "VLU_MAGR_TERM_RET_2": 42.1, "DATE_STRT_2": "20220105",
        "PCT_STOCK_ASSET": 88.0, "PCT_CCY_ASSET": 2.0, "PCT_BOND_ASSET": 6.0,
        "PCT_OTHER_ASSET": 4.0, "PCT_FUND_ASSET": 0.0, "NAM_CMPY": "先锋示例基金管理有限公司",
    },
    {
        "COD_FUND": "000003", "NAM_FUND": "安心纯债A", "NAM_FUND_SHORT": "安心纯债",
        "COD_FUND_TYP": "03", "COD_FUND_STS": "01", "COD_FUND_RSK_LVL": "02",
        "COD_FUND_LIVE_STS": "0", "COD_PURC_STS": "2", "COD_REDM_STS": "1",
        "AMT_IDV_FST_SSCR_MIN": 100, "AMT_IDV_FST_PURC_MIN": 10, "AMT_AIP_MIN": 10,
        "AMT_AIP_MAX": 10000, "AMT_FUND_SCL": 8700000000, "DATE_FUND_MKT": "20150618",
        "DATE_FUND_CRT": "20150520", "VLU_FUND_NAV": 1.1062, "VLU_FUND_NAV_ACML": 1.3824,
        "VLU_NAV_GRTH_YEAR": 0.061, "VLU_NAV_GRTH_3_MTH": 0.014, "VLU_NAV_GRTH_6_MTH": 0.029,
        "VLU_NAV_GRTH_THIS_YEAR": 0.051, "VLU_MAX_DD_YEAR": -0.018, "VLU_MAX_DD_3_MTH": -0.008,
        "VLU_MAX_DD_6_MTH": -0.012, "VLU_STD_YEAR": 0.032, "VLU_SHARP_YEAR": 1.62,
        "ID_RET_KIND_YEAR_RANK": 34, "ID_VLU_MAX_DD_KIND_RANK_YEAR": 7,
        "ID_STD_KIND_RANK_YEAR": 6, "ID_SHARP_KIND_RANK_YEAR": 3, "VLU_EX_BM_YEAR": 0.019,
        "NAM_MAGR_1": "王静", "DAYS_OF_MAGR_1": 4100, "AMT_MAGR_SCL_1": 24000000000,
        "VLU_MAGR_TERM_RET_1": 63.8, "DATE_STRT_1": "20150618",
        "PCT_STOCK_ASSET": 1.5, "PCT_CCY_ASSET": 8.0, "PCT_BOND_ASSET": 86.0,
        "PCT_OTHER_ASSET": 4.0, "PCT_FUND_ASSET": 0.5, "NAM_CMPY": "安心示例基金管理有限公司",
    },
    {
        "COD_FUND": "000004", "NAM_FUND": "均衡配置FOF A", "NAM_FUND_SHORT": "均衡FOF",
        "COD_FUND_TYP": "04", "COD_FUND_STS": "01", "COD_FUND_RSK_LVL": "04",
        "COD_FUND_LIVE_STS": "0", "COD_PURC_STS": "2", "COD_REDM_STS": "1", "IND_FOF": "1",
        "AMT_IDV_FST_SSCR_MIN": 1000, "AMT_IDV_FST_PURC_MIN": 100, "AMT_AIP_MIN": 100,
        "AMT_AIP_MAX": 30000, "AMT_FUND_SCL": 1900000000, "DATE_FUND_MKT": "20210608",
        "DATE_FUND_CRT": "20210510", "VLU_FUND_NAV": 1.3275, "VLU_FUND_NAV_ACML": 1.7186,
        "VLU_NAV_GRTH_YEAR": 0.139, "VLU_NAV_GRTH_3_MTH": 0.037, "VLU_NAV_GRTH_6_MTH": 0.071,
        "VLU_NAV_GRTH_THIS_YEAR": 0.095, "VLU_MAX_DD_YEAR": -0.083, "VLU_MAX_DD_3_MTH": -0.039,
        "VLU_MAX_DD_6_MTH": -0.057, "VLU_STD_YEAR": 0.137, "VLU_SHARP_YEAR": 1.19,
        "ID_RET_KIND_YEAR_RANK": 20, "ID_VLU_MAX_DD_KIND_RANK_YEAR": 38,
        "ID_STD_KIND_RANK_YEAR": 34, "ID_SHARP_KIND_RANK_YEAR": 24, "VLU_EX_BM_YEAR": 0.041,
        "NAM_MAGR_1": "陈平", "DAYS_OF_MAGR_1": 2900, "AMT_MAGR_SCL_1": 15500000000,
        "VLU_MAGR_TERM_RET_1": 71.3, "DATE_STRT_1": "20210608",
        "PCT_STOCK_ASSET": 32.0, "PCT_CCY_ASSET": 6.0, "PCT_BOND_ASSET": 24.0,
        "PCT_OTHER_ASSET": 3.0, "PCT_FUND_ASSET": 35.0, "NAM_CMPY": "均衡示例基金管理有限公司",
    },
]


def main() -> None:
    load_dotenv(ROOT / ".env", override=False)
    connection = mysql.connector.connect(
        host=os.getenv("IFUND_DB_HOST") or os.environ["OAG_TDSQL_HOST"],
        port=int(os.getenv("IFUND_DB_PORT") or os.getenv("OAG_TDSQL_PORT", "3306")),
        user=os.getenv("IFUND_DB_USER") or os.environ["OAG_TDSQL_USER"],
        password=os.getenv("IFUND_DB_PASSWORD") or os.environ["OAG_TDSQL_PASSWORD"],
        charset="utf8mb4",
    )
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS `ifundtest` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        cursor.execute("USE `ifundtest`")
        cursor.execute("SHOW TABLES LIKE 'ifund_all_info'")
        if cursor.fetchone() is None:
            cursor.execute((ROOT / "table_info.sql").read_text(encoding="utf-8"))
        for row in SEED_ROWS:
            columns = list(row)
            placeholders = ", ".join(["%s"] * len(columns))
            column_sql = ", ".join(f"`{column}`" for column in columns)
            updates = ", ".join(f"`{column}` = VALUES(`{column}`)" for column in columns if column != "COD_FUND")
            cursor.execute(
                f"INSERT INTO `ifund_all_info` ({column_sql}) VALUES ({placeholders}) "
                f"ON DUPLICATE KEY UPDATE {updates}",
                tuple(row[column] for column in columns),
            )
        connection.commit()
        print(f"Initialized ifundtest.ifund_all_info with {len(SEED_ROWS)} deterministic rows.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
