import socket
import time
from config.config import systemConfig

appConfigObj = systemConfig()

def startLaserPrinting(key):
    global writeInputDict
    try:
        # 创建一个TCP/IP套接字
        laserPrinter_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 连接服务器
        server_address = ('localhost', 7890)    # 服务器地址
        laserPrinter_sock.connect(server_address)     # 连接到服务器
        # 发送数据给服务器
        message = '{"F":"L","P":"123456"}#'     # 打印指令
        laserPrinter_sock.sendall(message.encode())
        print("Message sent1")
        response = laserPrinter_sock.recv(1024)  # 假设响应不会超过1024字节
        print("Received:", response.decode())
        
        #打印机文件路径，注意替换 fileMsg = '{"F":"ODC","DP":"D:\\\\smartFabInDeskProjectCode\\\\code\\\Final\\\\laserPrinting\\\\softwareNew\\\\BslCAD2.orzx"}#'
        fileMsg = appConfigObj.laserPrinterFilePath
        laserPrinter_sock.sendall(fileMsg.encode())
        print("Message sent2")
        response = laserPrinter_sock.recv(1024)  # 假设响应不会超过1024字节
        print("Received:", response.decode())

        # 打印图像文件路径，注意替换 
        curveMsg= appConfigObj.laserPrinterSignaturePath
        laserPrinter_sock.sendall(curveMsg.encode())
        response = laserPrinter_sock.recv(1024)  # 假设响应不会超过1024字节
        print("Received:", response.decode())

        #开始雕刻
        excuteMsg= '{"F":"M"}#'    # 开始雕刻指令
        laserPrinter_sock.sendall(excuteMsg.encode())   # 发送开始指令
        print("Message sent4")
        time.sleep(6)
        writeInputDict.update({'controlData':{key:False}})    # 更新控制数据
        print(writeInputDict)
        return True
        
    except:
        laserPrinter_sock.close()
    finally:
        laserPrinter_sock.close()