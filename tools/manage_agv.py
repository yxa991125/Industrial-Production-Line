"""简单命令行工具：基于 config.systemConfig 快速增删列出 AGV 设备
用法示例：
  python tools/manage_agv.py add agv_002 98:DA:B0:10:69:CB 0000ffe2-0000-1000-8000-00805f9b34fb
  python tools/manage_agv.py remove agv_002
  python tools/manage_agv.py list
"""
import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config import systemConfig


def main():
    parser = argparse.ArgumentParser(description='Manage AGV devices in config.yaml')
    sub = parser.add_subparsers(dest='cmd')

    p_add = sub.add_parser('add')
    p_add.add_argument('device_id')
    p_add.add_argument('address')
    p_add.add_argument('uuid')

    p_remove = sub.add_parser('remove')
    p_remove.add_argument('device_id')

    p_list = sub.add_parser('list')

    args = parser.parse_args()
    cfg = systemConfig()

    if args.cmd == 'add':
        ok = cfg.add_agv(args.device_id, args.address, args.uuid)
        if ok:
            print('添加成功')
        else:
            print('添加失败（可能已存在或写入错误）')
    elif args.cmd == 'remove':
        ok = cfg.remove_agv(args.device_id)
        if ok:
            print('删除成功')
        else:
            print('删除失败（可能不存在）')
    else:
        agvs = cfg.list_agvs()
        for k, v in agvs.items():
            print(f"{k}: address={v.get('address')} uuid={v.get('characteristic_uuid')}")

if __name__ == '__main__':
    main()
