from bleak import BleakClient
import asyncio
import time
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config import systemConfig

# 创建配置实例
config = systemConfig()

# 全局变量定义
AGV_States = {}  # 每台AGV的状态: device_id -> {'userMsg': {}, 'client': BleakClient}
writeInputDict = {'controlData': {}}
PLCSignalDict = config.PLCConfig  # 从配置中获取PLC信号配置

# 初始化所有AGV设备的状态
for device_id, info in config.AGVs.items():
    AGV_States[device_id] = {
        'userMsg': {'action': 'None', 'status': 'None'},
        'client': None,
        'address': info['address'],
        'characteristic_uuid': info['characteristic_uuid']
    }

# 定义异步发送命令的函数
async def send_command(client, characteristic_uuid, command):
    try:
        await client.write_gatt_char(characteristic_uuid, command, response=True)
        print(f"命令发送成功: {command}")
    except Exception as e:
        print(f"发送命令时发生错误: {e}")

def AGVAction(device_id: str):
    """处理指定AGV的动作控制逻辑"""
    global AGV_States, writeInputDict, PLCSignalDict
    
    # 获取当前AGV的状态
    state = AGV_States[device_id]
    userMsg = state['userMsg']
    
    ListCtrlStr = ['HMIAGVCanForwardMoving', 'HMIAGVReachedLogistic',
                   'HMIAGVReachedAssembly', 'HMIAGVCanBackwardMoving']
    
    # 检查是否到达货架位置
    if PLCSignalDict[ListCtrlStr[1]]['value']:
        time.sleep(1.5)
        userMsg['action'] = 'atLogistic'
        writeInputDict.update({'controlData': {ListCtrlStr[0]: False, ListCtrlStr[1]: False,
                                             ListCtrlStr[2]: False, ListCtrlStr[3]: False}})
    
    # 检查是否到达装配位置
    if PLCSignalDict[ListCtrlStr[2]]['value']:
        time.sleep(2)
        userMsg['action'] = 'atAssembly'
        writeInputDict.update({'controlData': {ListCtrlStr[0]: False, ListCtrlStr[1]: False,
                                             ListCtrlStr[2]: False, ListCtrlStr[3]: False}})
    
    # 检查是否可以前进（仅在没有手动停止或已经前进/后退命令时）
    if PLCSignalDict[ListCtrlStr[0]]['value'] and userMsg.get('action') not in ('stop', 'forward', 'backward'):
        userMsg['action'] = 'forward'
        writeInputDict.update({'controlData': {ListCtrlStr[0]: False}})
    
    # 检查是否可以后退（仅在没有手动停止或已经前进/后退命令时）
    if PLCSignalDict[ListCtrlStr[3]]['value'] and userMsg.get('action') not in ('stop', 'forward', 'backward'):
        userMsg['action'] = 'backward'
        writeInputDict.update({'controlData': {ListCtrlStr[3]: False}})

# AGV 控制器
async def agv_control_loop(device_id: str, client: BleakClient):
    """单个AGV设备的控制循环"""
    global AGV_States
    state = AGV_States[device_id]
    characteristic_uuid = state['characteristic_uuid']
    
    try:
        print(f"AGV设备 {device_id} 控制循环开始...")
        while True:
            # 处理AGV动作
            AGVAction(device_id)
            
            userMsg = state['userMsg']
            command = None

            # 如果收到手动停止指令，优先立即发送停止
            if userMsg.get('action') == 'stop':
                command = "$TZ!"  # 停止指令
                print(f"AGV {device_id}: 手动停止请求")
                userMsg['status'] = 'stop'

            else:
                if userMsg['status'] != 'move':
                    if userMsg['action'] == 'forward':
                        command = "$ZNXJ!"  # 前行巡线指令
                        print(f"AGV {device_id}: 前进")
                        userMsg['status'] = 'move'
                    elif userMsg['action'] == 'backward':
                        command = "$RZNXJ!"  # 逆向巡线指令
                        print(f"AGV {device_id}: 后退")
                        userMsg['status'] = 'move'
                    else:
                        # 没有可执行的动作，等待下一轮
                        command = None
                else:
                    # 当前处于移动状态，检查是否需要停止（到达目的地）
                    if userMsg['action'] in ('atAssembly', 'atLogistic'):
                        command = "$TZ!"  # 停止指令
                        userMsg['status'] = 'stop'
                        print(f'AGV {device_id}: 停止（已到达目的地）')
                    else:
                        # 维持移动状态，不重复发送控制命令
                        command = None

            # 发送命令（统一在发送前进行编码）
            if command is not None:
                await send_command(client, characteristic_uuid, command.encode('utf-8'))

            # 等待下一轮
            await asyncio.sleep(1)

    except Exception as e:
        print(f"AGV {device_id} 控制循环发生错误: {str(e)}")
        raise

async def start_agv_system():
    """启动AGV控制系统
    
    返回值:
        control_tasks: 包含所有AGV控制任务的列表
    """
    print("正在初始化AGV连接...")
    
    control_tasks = []
    
    # 连接所有AGV设备
    for device_id, state in AGV_States.items():
        try:
            # 连接到AGV设备
            print(f"正在连接AGV设备 {device_id}...")
            client = BleakClient(state['address'])
            await client.connect()
            print(f"AGV设备 {device_id} 连接成功！")
            
            # 存储客户端连接
            state['client'] = client
            
            # 创建设备控制任务
            control_task = asyncio.create_task(
                agv_control_loop(device_id, client)
            )
            control_tasks.append(control_task)
            
        except Exception as e:
            print(f"连接AGV设备 {device_id} 失败: {str(e)}")
            continue
            
    return control_tasks

async def stop_agv_system():
    """停止AGV控制系统，安全断开所有设备连接"""
    # 断开所有设备连接
    for device_id, state in AGV_States.items():
        client = state.get('client')
        if client and client.is_connected:
            try:
                # 在断开连接前发送停止命令
                await send_command(client, state['characteristic_uuid'], "$TZ!".encode('utf-8'))
            except Exception:
                pass
            await client.disconnect()
            print(f"AGV设备 {device_id} 已断开连接")