from fastapi import FastAPI, HTTPException
from typing import Dict
import uvicorn

app = FastAPI(title="AGV Control API")

# 引用全局变量
from agv.agvRun import userMsg, writeInputDict, PLCSignalDict

@app.post("/agv/command")
async def send_agv_command(command: Dict[str, str]):
    """
    发送AGV控制指令
    
    参数示例:
    {
        "action": "forward"  // 可选值: forward, backward, stop
    }
    """
    if "action" not in command:
        raise HTTPException(status_code=400, detail="Missing 'action' field")
    
    action = command["action"]
    if action not in ["forward", "backward", "stop"]:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'forward', 'backward', or 'stop'")
    
    # 更新全局状态
    userMsg["action"] = action
    userMsg["status"] = "None"  # 重置状态让AGV响应新指令
    
    return {"status": "success", "message": f"Command {action} sent to AGV"}

@app.get("/agv/status")
async def get_agv_status():
    """获取AGV当前状态"""
    return {
        "userMsg": userMsg,
        "plcSignals": {
            "HMIAGVCanForwardMoving": PLCSignalDict.get("HMIAGVCanForwardMoving", {}).get("value", False),
            "HMIAGVReachedLogistic": PLCSignalDict.get("HMIAGVReachedLogistic", {}).get("value", False),
            "HMIAGVReachedAssembly": PLCSignalDict.get("HMIAGVReachedAssembly", {}).get("value", False),
            "HMIAGVCanBackwardMoving": PLCSignalDict.get("HMIAGVCanBackwardMoving", {}).get("value", False)
        }
    }

@app.post("/agv/plc/simulate")
async def simulate_plc_signal(signals: Dict[str, bool]):
    """
    模拟PLC信号用于测试
    
    参数示例:
    {
        "HMIAGVCanForwardMoving": true,
        "HMIAGVReachedLogistic": false,
        "HMIAGVReachedAssembly": false,
        "HMIAGVCanBackwardMoving": false
    }
    """
    valid_signals = [
        "HMIAGVCanForwardMoving",
        "HMIAGVReachedLogistic",
        "HMIAGVReachedAssembly",
        "HMIAGVCanBackwardMoving"
    ]
    
    for signal, value in signals.items():
        if signal in valid_signals and signal in PLCSignalDict:
            PLCSignalDict[signal]["value"] = value
    
    return {"status": "success", "message": "PLC signals updated"}

def start_api_server():
    """启动API服务器"""
    uvicorn.run(app, host="0.0.0.0", port=8000)