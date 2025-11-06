from . import Robot
from .PoseDetectionClient import PoseDetectionClient
import numpy as np
import math
import time
import os
import cv2
import asyncio
from scipy.spatial.transform import Rotation
import threading

class RobotController:
    def __init__(self, robot, pos):
        self.robot = robot
        if not self.initial_position(pos):
            raise Exception("Failed to move robot to initial position")
            
    def get_cartesian_from_transform(self, transform_matrix):
        """从变换矩阵提取笛卡尔坐标"""
        position = transform_matrix[:3, 3]  # x, y, z
        position = position * 1000  # 转换为毫米
        rotation_matrix = transform_matrix[:3, :3]
        rot = Rotation.from_matrix(rotation_matrix)
        # 转4元数
        #print("orientation\n", rot.as_quat())
        # 欧拉角计算
        euler_angles = rot.as_euler('ZYX', degrees=True)
        rx, ry, rz = euler_angles[2], euler_angles[1], euler_angles[0]  # 转换为rx, ry, rz
        objPoseInCam = [position[0], position[1], position[2], rx, ry, rz]
        
        return objPoseInCam

    def move_to_target_pose(self, client:PoseDetectionClient):
        """
        Move the robot end-effector to the target pose using Cartesian space movement (MoveL)
        """
        # Get target pose from matrix
        objPoseInCam = client.center_poses[0]#取第一个识别到的物体位姿
        print(f"obj pose in Camera:\n {objPoseInCam}")
        if objPoseInCam.shape != (4,4):
            print("No valid pose detected. Exiting move_to_target_pose.")
            return

        #填灵巧手的偏移量
        hand2ObjOffset = np.array([7, 5, -200])#以机械臂末端为参考坐标系填写xyz偏移量(在飞机上方30cm处停顿，再下探30cm)
        #识别位姿误差补偿,在一次定位完成后填写
        #errorOffset = [10, 10, 0]
        errorOffset = [0, 0, 0]
        handPoseOffset = np.array([orin + err for orin, err in zip(hand2ObjOffset, errorOffset)]) / 1000

        #对齐物体坐标系
        target_in_ob = np.array([
            [ 0, 0,-1, -handPoseOffset[2]],
            [-1, 0, 0, -handPoseOffset[0]],
            [ 0, 1, 0, handPoseOffset[1]],
            [ 0, 0, 0, 1]
        ])

        cam2CenterPoseOffset = np.array([32.5, -80, 0])/1000
        # 构建位姿变换矩阵
        cam_in_ee = np.array([
            [-1, 0, 0, cam2CenterPoseOffset[0]],
            [ 0,-1, 0, cam2CenterPoseOffset[1]],
            [ 0, 0, 1, cam2CenterPoseOffset[2]],
            [ 0, 0, 0, 1]
        ])

        # 位姿变换
        targetPoseTF = cam_in_ee @ objPoseInCam @ target_in_ob
        print(f"target pose in tool frame: \n{targetPoseTF}")

        targetPoseDelta = self.get_cartesian_from_transform(targetPoseTF)
        targetPoseDelta = np.round(np.array(targetPoseDelta), 2)

        # Get current tool pose
        errorCode, toolPose=self.robot.GetActualTCPPose(flag=1)
        print(f"Current tool pose: {toolPose}")
        
        # Create target pose in Cartesian space [x, y, z, rx, ry, rz]        
        print(f"Target pose: {targetPoseDelta}")
        
        input("Press Enter to move to target pose...")        
        # Move to target pose using MoveL
        # Parameters: desc_pos, tool, user, other parameters use defaults
        if(self.robot.MoveL(desc_pos=toolPose, user=0, tool=0, offset_flag=2, offset_pos=targetPoseDelta)!= 0):
            print("Failed to move to target pose")
            return
        if(self.robot.StartJOG(4,3,1,30,10,30)!= 0):
            print("Failed to move to target pose")
        else:
            print("Movement to target pose completed")

    def initial_position(self,pos):
        try:
            # pos1=[-22.969961166381836, -66.10355377197266, -82.11998748779297, -97.49507141113281, 90.33198547363281, -94.09561920166016]
            print("Moving to initial position...")
            self.robot.MoveJ(pos, 0, 0)
            print("Initial position reached successfully")
            return True
        except Exception as e:
            print(f"Error during initial position movement: {e}")
            return False
        
    def fine_tune_xyz(self):
        """
        用于微调xyz方向的位置，记录每个方向的调整总量并输出
        """
        total_adjust = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        axis_map = {"X": 1, "Y": 2, "Z": 3}
        print("开始微调xyz。输入格式如：X 1.5 或 Y -2，输入 q 退出。")
        while True:
            user_input = input("请输入要微调的轴和距离（如 x 1.5），或输入q退出: ")
            if user_input.strip().lower() == "q":
                break
            try:
                axis, value = user_input.strip().split()
                print(axis)
                print(value)
                axis = axis.upper()
                value = float(value)
                if axis not in axis_map:
                    print("轴只能是X Y或Z")
                    continue
                dir = 1 if value > 0 else 0
                jog = abs(value)
                self.robot.StartJOG(4, axis_map[axis], dir, jog, 20.0, 30.0)
                time.sleep(1)
                total_adjust[axis] += value
                print(f"{axis}方向已调整{value}mm，当前累计调整：{total_adjust}")
            except Exception as e:
                print("输入有误，请重新输入。错误信息：", e)
        print("微调结束，总调整量：", total_adjust)
        return total_adjust

    def hand_up(self):
        self.robot.StartJOG(2,3,1,80,vel=20.0,acc=100.0) #世界坐标系下z轴点动
        time.sleep(1)

async def pose_detection(client:PoseDetectionClient):
    try:
        await client.connect()

        while True:
            try:
                # 检测位姿
                result = await client.detect_poses(is_first_frame=False)
                
                # 处理结果
                #print(f"Poses: {result['poses'].shape}")
                #print(f"Center poses: {result['center_poses'].shape}")
                client.poses = result['poses']
                client.center_poses = result['center_poses']
                
                # 显示图像
                cv2.imshow('Remote Pose Detection', result['visualization_image'])
                
                # 按键处理
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' '):  # 空格键重新初始化
                    print("redetect...")
                    result = await client.detect_poses(is_first_frame=True)
                elif key == ord('c'):
                    client.ready = True
                elif key == 27:  # ESC键退出
                    break
                    
                # 控制帧率
                await asyncio.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Detection error: {e}")
                break
                    
    finally:
        print("Closing connection...")
        await client.close()
        cv2.destroyAllWindows()

def run_async_in_thread(client):
    asyncio.run(pose_detection(client))

if __name__ == "__main__":
    DEBUG = False
    #DEBUG = True
    # 初始化位置
    robot = Robot.RPC('192.168.58.2')
    pos=[-22.969961166381836, -66.10355377197266, -82.11998748779297, -97.49507141113281, 90.33198547363281, -94.09561920166016]
    controller = RobotController(robot,pos)
    client = PoseDetectionClient()
    #asyncio.run(pose_detection(client))
    # 在后台线程中运行姿势检测
    pose_thread = threading.Thread(target=run_async_in_thread, args=(client,),daemon=True)
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
        controller.fine_tune_xyz()
