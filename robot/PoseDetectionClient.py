import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import time

class PoseDetectionClient:
    def __init__(self, uri='ws://192.168.137.4:8889'):
        self.uri = uri
        self.websocket = None
        self.poses = None
        self.center_poses = None
        self.connetcted = False
        self.ready = False
        
    async def connect(self):
        """连接到服务器"""
        self.websocket = await websockets.connect(
            self.uri, 
            ping_timeout=120,  # 增加ping超时到60秒
            ping_interval=20, # 每20秒发送一次ping
            close_timeout=30  # 关闭超时30秒
        )
        self.connetcted = True
        print(f"Connected to {self.uri}")
    
    async def detect_poses(self, is_first_frame=False):
        """请求位姿检测"""
        message = {
            'command': 'detect',
            'is_first_frame': is_first_frame,
            'timestamp': time.time()
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if data['status'] == 'success':
            # 解码原始图像
            orig_image_data = base64.b64decode(data['original_image'])
            orig_nparr = np.frombuffer(orig_image_data, np.uint8)
            original_image = cv2.imdecode(orig_nparr, cv2.IMREAD_COLOR)
            
            # 解码可视化图像
            vis_image_data = base64.b64decode(data['visualization_image'])
            vis_nparr = np.frombuffer(vis_image_data, np.uint8)
            visualization_image = cv2.imdecode(vis_nparr, cv2.IMREAD_COLOR)
            
            return {
                'poses': np.array(data['poses']),
                'center_poses': np.array(data['center_poses']),
                'original_image': original_image,
                'visualization_image': visualization_image,
                'timestamp': data['timestamp']
            }
        else:
            raise Exception(data['message'])
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()

async def main():
    client = PoseDetectionClient()
    
    try:
        await client.connect()

        while True:
            try:
                # 检测位姿
                result = await client.detect_poses(is_first_frame=False)
                
                # 处理结果
                print(f"Poses: {result['poses'].shape}")
                print(f"Center poses: {result['center_poses'].shape}")
                
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

if __name__ == "__main__":
    asyncio.run(main())