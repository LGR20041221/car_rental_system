"""
时区安全的日期范围工具。

在 USE_TZ=True 且 MySQL 环境下，`created_at__date=` 等日期过滤存在时区转换偏移问题，
统一改用「当天零点 ~ 次日零点」的 datetime 区间查询，保证统计口径与本地时区一致。
"""
import datetime

from django.utils import timezone


def day_start(day):
    """某日本地时区的零点（作为 datetime 返回，存入库时自动转 UTC）。"""
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))


def day_end(day):
    """某日次日的零点，用于 [day, day+1) 开区间上界。"""
    return timezone.make_aware(
        datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time.min)
    )
