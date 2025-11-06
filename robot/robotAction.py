import time
import threading
from robot.robotController import RobotController, run_async_in_thread
from robot.PoseDetectionClient import PoseDetectionClient

from config.config import systemConfig

robotActionObj = systemConfig().robotConfig

class RobotMoveControl:
    def __init__(self,hand_client):
        self.hand_client = hand_client
        self.operation = robotActionObj

    def action(self, key, robot): 
        """执行机器人动作组"""
        if key in ['HMIRobotCatchAUVFromAGV','HMIRobotCatchTrayFromAGV',
                  'HMIRobotCatchAUVFromCurving','HMIRobotCatchAUVFromAssembly']:
            grip_action = True  # 抓取动作
        else:
            grip_action = False  # 释放动作

        if key in self.operation:    
            positions = self.operation[key]
            position1 = positions['pos1']
            position2 = positions['pos2']
        
        if key == 'ChildCMDRobotAutoAlignAUV' or key == 'ChildCMDRobotRecenterTray':
            print(f"Moving to idle pos")
            robot.MoveJ(positions['pos1'], 0, 0)
            time.sleep(0.5)
            print(f"Moving to start pos")
            robot.MoveJ(positions['pos2'], 0, 0)
            time.sleep(0.5)
            print(f"recenter")
            robot.MoveJ(positions['pos3'], 0, 0)
            time.sleep(0.5)
            return

        if key == 'HMIRobotCatchAUVFromCurving':
            pos = [-22.969961166381836, -66.10355377197266, -82.11998748779297, -97.49507141113281, 90.33198547363281, -94.09561920166016]
            controller = RobotController(robot,pos)
            client = PoseDetectionClient()
            pose_thread = threading.Thread(target=run_async_in_thread, args=(client,), daemon=True)
            pose_thread.start()
            while not client.connetcted:
                print("waiting for connection...")
                time.sleep(1)

            while True:
                while not client.ready:
                    print("waiting for pose detection...")
                    time.sleep(1)
                controller.move_to_target_pose(client)
                client.ready = False
                errorCode, toolPose=robot.GetActualTCPPose(flag=1)
                print(f"Current tool pose: {toolPose}")
                break
            time.sleep(2)
        
        elif key == 'HMIRobotCatchAUVFromAssembly':
            pos = [61.19493865966797, -58.597442626953125, -66.8068618774414, -120.1806411743164, 73.4983139038086, -64.21932983398438]
            controller = RobotController(robot,pos)
            client = PoseDetectionClient()
            pose_thread = threading.Thread(target=run_async_in_thread, args=(client,), daemon=True)
            pose_thread.start()
            while not client.connetcted:
                print("waiting for connection...")
                time.sleep(1)

            while True:
                while not client.ready:
                    print("waiting for pose detection...")
                    time.sleep(1)
                controller.move_to_target_pose(client)
                client.ready = False
                errorCode, toolPose=robot.GetActualTCPPose(flag=1)
                print(f"Current tool pose: {toolPose}")
                break
            time.sleep(2)
        
        else:
            # 移动到第一个位置
            print(f"Moving to position1 for {key}")
            robot.MoveJ(position1, 0, 0)
            time.sleep(0.5)
            
            # 移动到第二个位置
            print(f"Moving to position2 for {key}")
            robot.MoveJ(position2, 0, 0)
            time.sleep(0.5)
        
        # 执行抓取/释放动作
        if grip_action:
            print("Executing grip action")
            self.hand_client.grip()
        else:
            print("Executing release action")
            self.hand_client.release()
        time.sleep(0.5)
        
        # 特殊处理放置到装配区的动作
        if key == 'HMIRobotPutDownAUVIntoAssembly' or key == 'HMIRobotCatchAUVFromAssembly':
            position3 = positions['pos3']          
            print("Moving to position3")
            robot.MoveJ(position3, 0, 0)
            time.sleep(0.5)

        else:
            # 返回第一个位置
            print("Returning to position1")
            robot.MoveJ(position1, 0, 0)
            time.sleep(0.5)
        
        if key == 'HMIRobotPutDownAUVIntoCurving':
            # self.action('ChildCMDRobotAutoAlignAUV',robot)
            self.action('ChildCMDRobotRecenterTray',robot)
        print(f"Action {key} completed")

def robotAction(key,robot): 
    global writeInputDict,robotmovecommand,PLCSignalDict
    print("signal:",key)
    print("value:",PLCSignalDict[key]['value'])
    print(writeInputDict)
    if  PLCSignalDict[key]['value']==True:
        robotmovecommand.action(key,robot)
        # 动作完成后，将对应的PLC信号重置为False
        writeInputDict.update({'controlData':{key:False}})
        print(f"Robot action {key} completed, signal reset to False")