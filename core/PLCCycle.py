import threading
import time
from config.config import systemConfig
from snap7.util import get_bool, get_real, set_bool, set_real, set_int
from robot.robotAction import robotAction
from robot import Robot
from laser.laserRun import startLaserPrinting
from cnc.cncRun import CNCCommandExcute
import agv.agvRun as agvmod
import core.PLCutils

# 初始化系统配置
cfg = systemConfig()
PLC_IP = cfg.PLC_IP   # PLC的IP地址
PLCSignalDict = cfg.PLCConfig    # PLC信号字典
PLCObj = None  # 延迟实例化 PLCObj，避免在导入时进行网络连接

# writeInputDict 默认结构，避免未定义
writeInputDict = {}

# 机器人实例化（延迟/容错）
robot_instance = None
try:
    robot_instance = Robot.RPC('192.168.58.2')
except Exception as e:
    print(f"Warning: robot RPC init failed: {e}")
thread_lock = threading.Lock() # 创建线程锁
dictTotal = {'signatureWeb': ""}
writeInputDict = {}  # 初始化写入PLC的输入字典

def PLCSignalCycle():
    global writeInputDict,dictTotal,PLCSignalDict
    avoidRepeatDIct = {}    # 用于避免重复执行的字典
    while True: 
        # 读PLC信号，并处理
        # 延迟初始化 PLCObj（避免在模块导入时进行网络连接）
        global PLCObj
        if PLCObj is None:
            try:
                PLCObj = core.PLCutils.PLCUtils(PLC_IP, 0, 1)
            except Exception as e:
                print(f"Failed to init PLCObj: {e}")
                time.sleep(5)
                continue

        db_number = 20   # 数据块号
        # 获取PLC信号的起始和结束地址
        start_address = min(var['readStart'] for var in PLCSignalDict.values())
        end_address = max(var['readStart'] + var['readSize'] for var in PLCSignalDict.values())
        size = end_address - start_address      # 计算读取的大小
        try:
            data = PLCObj.plc.db_read(db_number, start_address, size)     # 从PLC读取数据
        except Exception as e:
            print(f"Failed to read PLC DB {db_number}: {e}")
            time.sleep(2)
            continue
        # 遍历PLC信号字典
        for key, var in PLCSignalDict.items():
            start = var['readStart'] - start_address
            # 根据变量类型读取数据
            if var['varType'] == 'Bool':
                var['value'] = get_bool(data, start, var['bitNum'])
            elif var['varType'] == 'Real':
                var['value'] = get_real(data, start)
            PLCSignalDict[key]['value'] = var['value']
            # 处理机器人信号
            if 'HMIRobot' in key and var['value'] == True:
                # 检查是否可以执行该动作，避免重复执行
                if key not in avoidRepeatDIct or (time.time() - avoidRepeatDIct[key]['last_executed']) > 90:
                    with thread_lock:
                        threading.Thread(target=robotAction, args=(key, robot_instance), daemon=True).start()   # 启动机器人动作线程
                    avoidRepeatDIct.update({key: {'last_executed': time.time()}})      # 更新最后执行时间            
            
            # 处理AGV信号
            if 'HMIAGV' in key and var['value'] == True:
                # 检查是否可以执行该动作，避免重复执行
                if key not in avoidRepeatDIct or (time.time() - avoidRepeatDIct[key]['last_executed']) > 10:
                    with thread_lock:
                        # AGVAction 已改为按 device_id 处理，触发所有已注册设备的动作处理
                        try:
                            for dev_id in agvmod.AGV_States.keys():
                                threading.Thread(target=agvmod.AGVAction, args=(dev_id,), daemon=True).start()
                        except Exception as e:
                            print(f"Error triggering AGVAction: {e}")
                    avoidRepeatDIct.update({key:{'last_executed':time.time()}})      # 更新最后执行时间
                    
            # 处理激光打印机信号
            if 'HMILaserPrinter' in key and var['value'] == True:
                # 检查是否可以执行该动作，避免重复执行
                if key not in avoidRepeatDIct or (time.time() - avoidRepeatDIct[key]['last_executed']) > 20:
                    with thread_lock:
                        threading.Thread(target=startLaserPrinting, args=(key,), daemon=True).start()     # 启动激光打印线程
                    avoidRepeatDIct.update({key:{'last_executed':time.time()}})       # 更新最后执行时间
            
            # 处理CNC信号
            if 'mBCurvingMachineCanStart' in key and var['value'] == True:
                # 检查是否可以执行该动作，避免重复执行
                if key not in avoidRepeatDIct or (time.time() - avoidRepeatDIct[key]['last_executed']) > 60:
                    # 调用CNC制造处理函数
                    with thread_lock:   
                        threading.Thread(target=CNCCommandExcute,  daemon=True).start()      # 启动CNC命令执行线程
                    avoidRepeatDIct.update({key:{'last_executed':time.time()}})       # 更新最后执行时间

        # 写PLC信号（按DB分组写入，避免使用循环后的未定义变量）
        try:
            for controlType in ('displayData', 'controlData'):
                if controlType not in writeInputDict:
                    continue

                # 更新 PLCSignalDict 中的值
                for key, val in writeInputDict[controlType].items():
                    if key in PLCSignalDict:
                        PLCSignalDict[key]['value'] = val

                # 根据 controlType 过滤出要写的变量
                if controlType == 'displayData':
                    tempTotalDict = {key: value for key, value in PLCSignalDict.items() if value.get('readStart', 0) >= 14}
                else:
                    tempTotalDict = {key: value for key, value in PLCSignalDict.items() if value.get('readStart', 0) < 14}

                if not tempTotalDict:
                    continue

                # 按 DBnumber 分组写入
                groups = {}
                for key, var in tempTotalDict.items():
                    dbnum = var.get('DBnumber', db_number)
                    groups.setdefault(dbnum, {})[key] = var

                for dbnum, vars_in_db in groups.items():
                    min_read_start = min(v['readStart'] for v in vars_in_db.values())
                    max_end = max(v['readStart'] + v.get('readSize', 1) for v in vars_in_db.values())
                    length = max_end - min_read_start
                    data = bytearray(length)
                    for key, var in vars_in_db.items():
                        start_index = var['readStart'] - min_read_start
                        if var['varType'] == 'Bool':
                            set_bool(data, start_index, var['bitNum'], var['value'])
                        elif var['varType'] == 'Real':
                            set_real(data, start_index, var['value'])
                        elif var['varType'] == 'Int':
                            set_int(data, start_index, var['value'])
                    try:
                        PLCObj.plc.db_write(dbnum, min_read_start, data)
                    except Exception as e:
                        print(f"Error writing to PLC DB {dbnum}: {e}")

        except Exception as e:
            print(f"Error writing to PLC: {e}")

        finally:
            # 重置为默认结构以保证下一次循环安全
            writeInputDict = {'controlData': {}, 'displayData': {}}

        #set HMI Order
        if dictTotal['signatureWeb'] != "":    # 如果签名不为空
            PLCObj.orderSet(dictTotal)       # 设置PLC订单
            dictTotal['signatureWeb'] = ""    # 清空签名
        time.sleep(2) #写和读的间隔时间(太短会导致写的时候再次读取，动作重复执行)

