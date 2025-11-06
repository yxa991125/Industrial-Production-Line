import socket
import time
from config.config import systemConfig

# 控制变量
CNCWorkMod = 0
writeInputDict = {}
PLCSignalDict = systemConfig().PLCConfig
writeInputDict = {'controlData': {}, 'displayData': {}}

# 后台处理CNC加工命令
def CNCCommandExcute():
    global CNCWorkMod,PLCSignalDict
    CNCCommand_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # 创建UDP套接字
    try:
        while True:   
            message =""    # 初始化消息
            # print(CNCWorkMod)  
            if CNCWorkMod==0 and PLCSignalDict['mBCurvingMachineCanStart']['value'] == True:
                CNCCommand_socket.sendto('cncUnlock'.encode(),('127.0.0.1',8066))   # 发送解锁命令
                data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                message = str(data.decode())
                time.sleep(1)
            if message=="CNCUnlockSignalReceived":
                CNCWorkMod +=10
            
            if CNCWorkMod==10:
                CNCCommand_socket.sendto('cncHome'.encode(),('127.0.0.1',8066))   # 发送回原点命令
                time.sleep(2)
                data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                message = str(data.decode())
                if message =="CNCHomeSignalReceived":
                    CNCWorkMod +=10

            if CNCWorkMod==20 :
                CNCWorkMod +=10

            if CNCWorkMod==30:
                CNCCommand_socket.sendto('cncLoadFile'.encode(),('127.0.0.1',8066))     # 发送加载文件命令
                data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                message = str(data.decode())
                time.sleep(2)
                if message=="CNCLoadFileSignalReceived":
                    CNCWorkMod =100

            if CNCWorkMod ==100 :
                current_time = time.time()
                if 'last_execution_time' not in globals() or current_time - last_execution_time >= 60:
                    CNCCommand_socket.sendto('cncToOriginPoint'.encode(),('127.0.0.1',8066))     # 发送回原点命令
                    data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                    message = str(data.decode())
                    time.sleep(2)
                    if message=="cncAtOriginPoint":
                        CNCWorkMod +=100
                    last_execution_time = current_time
                    

            if CNCWorkMod==200:
                CNCCommand_socket.sendto('cncSetXYZZeroPoint'.encode(),('127.0.0.1',8066))    # 发送设置零点命令
                data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                message = str(data.decode())
                CNCWorkMod +=100
                

            if CNCWorkMod==300:
                
                time.sleep(15)
                CNCCommand_socket.sendto('cncStartCurving'.encode(),('127.0.0.1',8066))     # 发送开始雕刻命令
                try:
                    data, addrServer = CNCCommand_socket.recvfrom(1024)  # 接收数据
                except socket.error:
                    continue
                message = str(data.decode())
                
                time.sleep(1)
                if message=="cncCurvingHasStarted":
                    print(message)
                    CNCWorkMod=9999

            # if dictCNCStatus['txtStatus'] == "Alarm":
            #     CNCWorkMod =0

            if CNCWorkMod ==9999:
                writeInputDict.update({'controlData':{'mBCurvingMachineCanStart': False}})   # 更新控制数据
                if PLCSignalDict['mBCurvingMachineCanStart']['value'] == False:
                    CNCWorkMod =0
                    time.sleep(2)
                    CNCCommand_socket.close()
                    break
    except Exception as e:
        print(f"Error: {e}")
        CNCCommand_socket.close()

# 获取CNC状态信息
def CNCStatus():
    global writeInputDict,PLCSignalDict
    CNCStatus_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:  
        CNCStatus_socket.sendto('positionRequest'.encode(), ('127.0.0.1',8065))
        data, addrServer = CNCStatus_socket.recvfrom(1024)  # 接收数据
        message = str(data.decode())
        
        if "," in message:
            MsgList = message.split(',')
            for item in MsgList[:3]:
                PLCSignalDict[item.split(':')[0]]['value']=item.split(':')[1]
                writeInputDict.update({'displayData':{item.split(':')[0]:item.split(':')[1]}})
        return {'txtStatus': MsgList[3].split(':')[1]}