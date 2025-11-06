"""离线测试脚本（位于 test/）: 在没有真实AGV设备时验证AGV控制逻辑。

用法（在项目根目录 D:\Code\Industry 下运行）：
    python -m test.test_offline_agv

说明：
- 从 `test.mock_bleak` 导入 MockBleakClient，替换 `agvRun.BleakClient`。
- 创建虚拟 AGV 条目并初始化 PLCSignalDict。
- 启动 AGV 系统，模拟 PLC 信号，打印 Mock 客户端接收到的命令。
"""

import asyncio
import time

from agv import agvRun
from test.mock_bleak import MockBleakClient

async def run_test():
    # 用 MockBleakClient 替换真实的 BleakClient
    agvRun.BleakClient = MockBleakClient

    # 清理并准备一个虚拟设备
    device_id = 'virtual1'
    agvRun.AGV_States.clear()
    agvRun.AGV_States[device_id] = {
        'userMsg': {'action': None, 'status': None},
        'client': None,
        'address': 'virtual_addr',
        'characteristic_uuid': 'mock-char-uuid'
    }

    # 确保PLC信号字典包含 AGVAction 需要的键
    signals = ['HMIAGVCanForwardMoving','HMIAGVReachedLogistic','HMIAGVReachedAssembly','HMIAGVCanBackwardMoving']
    agvRun.PLCSignalDict = {k: {'value': False} for k in signals}

    # 启动AGV系统（仅创建任务并返回任务句柄）
    tasks = await agvRun.start_agv_system()

    # 让系统稳定运行一会儿
    await asyncio.sleep(0.2)

    # 模拟可以前进的信号
    print('\n--- 模拟: 可以前进 (HMIAGVCanForwardMoving = True) ---')
    agvRun.PLCSignalDict['HMIAGVCanForwardMoving']['value'] = True
    await asyncio.sleep(0.6)
    # 清除信号
    agvRun.PLCSignalDict['HMIAGVCanForwardMoving']['value'] = False

    # 等待命令发送并维持运动
    await asyncio.sleep(0.6)

    # 模拟到达货架位置
    print('\n--- 模拟: 到达货架 (HMIAGVReachedLogistic = True) ---')
    agvRun.PLCSignalDict['HMIAGVReachedLogistic']['value'] = True
    await asyncio.sleep(1.0)
    # 清除到达信号
    agvRun.PLCSignalDict['HMIAGVReachedLogistic']['value'] = False

    # 等待短暂时间以便命令被写入
    await asyncio.sleep(0.3)

    # 检查 Mock 客户端发送的命令
    client = agvRun.AGV_States[device_id]['client']
    if client is None:
        print('错误：模拟客户端未创建')
    else:
        print('\n--- 模拟设备发送的命令（可读）---')
        for idx, (uuid, data) in enumerate(client.get_commands(), 1):
            print(f"{idx}. char={uuid}, data={data}")

    # 停止AGV系统并断开连接
    await agvRun.stop_agv_system()

    # 取消所有任务（如果 start_agv_system 返回了任务，主程序可能会 await_gather）
    for t in tasks:
        t.cancel()

    # 等待取消生效
    await asyncio.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(run_test())