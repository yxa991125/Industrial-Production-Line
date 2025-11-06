from flask import Flask, render_template, request, jsonify
from core.PLCutils import PLCUtils
import json
from config.config import systemConfig

PLC_IP = systemConfig().PLC_IP # 获取PLC的IP地址
PLCObj = None  # 延迟创建PLC通信对象

def get_plc():
    """延迟创建并获取PLC对象，避免在导入时建立连接"""
    global PLCObj
    if PLCObj is None:
        try:
            PLCObj = PLCUtils(PLC_IP, 0, 1)
        except Exception as e:
            print(f"警告：PLC连接失败 - {e}")
    return PLCObj

# 全局字典用于存储网页数据
app = Flask(import_name=__name__)
app.static_folder = "static"

#region     TODO:HH网页
@app.route('/')
def index():
    print(123)
    return render_template('index.html')

#收到消息，写PLC值
@app.route('/userInfo',methods = ['POST'])
def indexPost():
    global dictTotal
    print("Web Receive Data")
    dataRecvStr = request.get_data().decode()    # 获取请求数据并解码
    print(dataRecvStr)
    dataRecvJson = json.loads(dataRecvStr)     # 将字符串解析为JSON对象
    # 更新字典中的值
    dictTotal['colorWeb']= dataRecvJson['color']
    dictTotal['batteryWeb']= dataRecvJson['battery']
    dictTotal['flyWeb']= dataRecvJson['fly']
    dictTotal['printWeb']= dataRecvJson['print']
    dictTotal['signatureWeb'] = dataRecvJson['signature'] 
    if dictTotal['signatureWeb'] != "":
        plc = get_plc()
        if plc:
            plc.pictureToSVG(dictTotal['signatureWeb'])    # 将签名转换为SVG格式
            # 返回成功响应  
            return jsonify({'status': 'success', 'message': 'Signature saved'}), 200 
        else:
            return jsonify({'status': 'error', 'message': 'PLC未连接'}), 503
    else:
        print("no data")
    return 'Data received', 200  # 返回状态码200和一个简单的消息
