#!/usr/bin/env python
"""Django 命令行管理入口，用于启动服务、执行迁移、生成测试数据等。"""
import os
import sys


def main():
    """设置 Django 环境变量并执行命令行操作。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'car_rental_system.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请确认已按 README 安装依赖。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
