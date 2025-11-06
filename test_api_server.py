"""独立的测试API服务器，用于远程控制和测试AGV设备。"""
import uvicorn
from agv.api import app

if __name__ == "__main__":
    print("启动AGV测试API服务器...")
    print("API文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)