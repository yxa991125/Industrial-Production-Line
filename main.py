import threading
import time
import asyncio
from config.config import systemConfig
from hand.canfdHand import HandClient
from robot.Robot import RPC as RobotRPC
from robot.robotAction import RobotMoveControl
from core.PLCCycle import PLCSignalCycle
from cnc.cncRun import CNCStatus, CNCCommandExcute
from laser.laserWeb import app as laser_app
import agv.agvRun as agv_module

async def async_main():
    """异步主控制流程"""
    try:
        # 启动AGV系统
        print("启动AGV系统...")
        agv_tasks = await agv_module.start_agv_system()
        
        # 等待所有AGV任务
        await asyncio.gather(*agv_tasks)
        
    except Exception as e:
        print(f"异步主控制发生错误: {e}")
        # 停止AGV系统
        await agv_module.stop_agv_system()
    finally:
        print("异步主控制结束")

def main():
    """主程序入口"""
    try:
        print("系统启动...")
        
        # 1. 初始化系统配置
        cfg = systemConfig()
        
        # 2. 初始化手部控制（等待1s避免PLC初始化干扰）
        time.sleep(1)
        hand_client = HandClient()
        time.sleep(0.1)
        
        # 3. 初始化机器人
        robot = RobotRPC('192.168.58.2')
        initpos = [-58.219, -86.098, -23.685, -121.939, 89.867, -85.634]
        robot.MoveJ(initpos, 0, 0)
        robotmovecommand = RobotMoveControl(hand_client)
        
        # 4. 启动子系统线程
        threads = []
        
        # PLC 信号循环线程
        plc_thread = threading.Thread(target=PLCSignalCycle, daemon=True)
        plc_thread.start()
        threads.append(plc_thread)
        
        # AGV 控制线程（使用asyncio事件循环）
        agv_thread = threading.Thread(
            target=lambda: asyncio.run(async_main()),
            daemon=True
        )
        agv_thread.start()
        threads.append(agv_thread)
        
        # CNC 状态监测线程
        cnc_thread = threading.Thread(target=CNCStatus, daemon=True)
        cnc_thread.start()
        threads.append(cnc_thread)
        
        # 激光打印 Web 服务器
        laser_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        
        # 等待所有线程结束（实际上不会执行到这里，因为Flask应用会阻塞）
        for t in threads:
            t.join()
            
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭系统...")
        # 在这里可以添加清理代码
    except Exception as e:
        print(f"系统运行出错: {e}")
    finally:
        print("系统已停止")

if __name__ == '__main__':
    main()