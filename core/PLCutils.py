from flask_socketio import SocketIO, emit,join_room,leave_room
from flask import Flask, request, jsonify,render_template  
from io import BytesIO  
from PIL import Image  
import base64,json  
from flask_cors import CORS
import socketio
import numpy as np
import cv2,time,snap7
import svgwrite
import json,threading
from PIL import ImageOps
from snap7.util import set_string, get_string, get_bool, set_bool, get_int, set_int, get_real, set_real
import time
import os

class PLCUtils(object):
    def __init__(self, ip, rack, slot):
        self.plc = snap7.client.Client()
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.PLCValueDictToAll = {}  # 初始化 PLCValueDictToAll 属性
        self.lock = threading.Lock()  # 初始化线程锁
        self.connect()
        
    
    def connect(self):
        try:
            self.plc.connect(self.ip, self.rack, self.slot)
            print("Connected to PLC")
        except Exception as e:
            print(f"Failed to connect to PLC: {e}")
            time.sleep(5)
            self.connect()
    #处理图片转SVG
    def pictureToSVG(self,dataSignature):
        # 解码Base64字符串为二进制数据  
        signature_bytes = base64.b64decode(dataSignature.split(',')[1])  
        # 将二进制数据转换为PIL Image对象  
        signature_image = Image.open(BytesIO(signature_bytes))  
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        path = script_dir+'/static/upload/'
        # 保存图像到文件  
        signature_image.save(path+'signature.png', 'PNG')

        time.sleep(1)
        #读取图像
        image = Image.open(path+'signature.png')
        #将图像转化成灰度图像
        gray_image = image.convert('L')
        #设置图像阈值
        threshold = 1
        def threshold_image(pixel):   # 假设我们使用128作为阈值
            return 255 if pixel > threshold else 0
        #将图像变成2值图像
        binary_image = image.point(threshold_image)
        #寻找图像边缘
        #cv2.Canny(image, threshold1, threshold2)
        #image: 输入图像，通常是灰度图像
        #threshold1 (在您的代码中为100): 第一个阈值。这个阈值用于滞后阈值化。边缘函数首先会找到图像中所有大于此阈值的像素点，这些点被认为是强边缘点。
        #threshold2 (在您的代码中为200): 第二个阈值。这个阈值用于滞后阈值化。然后，函数会查看与强边缘点相连的所有像素点，如果它们的值大于这个阈值，则它们也被认为是边缘点。这有助于确保边缘是连续的，并减少噪声。
        edges = cv2.Canny(np.array(binary_image),1,1)
        #将边缘信息变成SVG文件,创建SVG对象画布
        svg = svgwrite.Drawing(filename=path+'signature.svg',size=('100px','100px'))
        #设置SVG画布的大小与edges图像的大小一致
        svg.viewbox(0,0,edges.shape[1],edges.shape[0])
        # 遍历edges图像的每一个像素，并在SVG中绘制相应的矩形
        
        for y in range(edges.shape[0]):
            for x in range(edges.shape[1]):
                if edges[y, x] > 0:  # 如果像素值大于0，认为是边缘
                    rect = svg.rect((y, x), width=5, height=5, fill='black')
                    svg.add(rect)
        svg.save()
    

    #PLC设置
    def getSetVal(self,DBnumber=0, Readstart=0, Readsize=0,
        varType="Bool",bitNum=0,setVar=None):
        data = self.plc.db_read(DBnumber, Readstart, Readsize)
        if varType=="Bool":
            temp_value = get_bool(data, 0,bitNum)
            if setVar != None:
                set_bool(data, 0, bitNum, setVar)
                self.plc.db_write(DBnumber, Readstart, data)
        if varType=="Int":
            temp_value = get_int(data, 0)
            if setVar != None:
                data = bytearray(2)  # Real类型占4个字节
                set_int(data, 0, setVar)
                self.plc.db_write(20, 6, data)
        if varType=="Real":
            temp_value = get_real(data, 0)
            if setVar != None:
                data = bytearray(4)
                set_real(data, 0, setVar)
                self.plc.db_write(DBnumber, Readstart, data)
        if varType=="String":
            temp_value = get_string(data, 0)
            if setVar != None:
                data = bytearray(4)
                set_string(data, 4, setVar)
                self.plc.db_write(DBnumber, Readstart, data)
        return temp_value

    def PLC_Threading(self, ReadPLCSignalDict={}, writePLCSignalDict={}, act="None", plc_queue=None):
        if act == "read":
            db_number = 20
            start_address = min(var['readStart'] for var in ReadPLCSignalDict.values())
            end_address = max(var['readStart'] + var['readSize'] for var in ReadPLCSignalDict.values())
            size = end_address - start_address
            data = self.plc.db_read(db_number, start_address, size)
            for key, var in ReadPLCSignalDict.items():
                start = var['readStart'] - start_address
                if var['varType'] == 'Bool':
                    var['value'] = get_bool(data, start, var['bitNum'])
                elif var['varType'] == 'Real':
                    var['value'] = get_real(data, start)
                self.PLCValueDictToAll.update({key: var['value']})
                print(self.PLCValueDictToAll)
            with self.lock:
                self.PLCValueDictToAll = {'PLC': self.PLCValueDictToAll}
            # self.PLCValueDictToAll = {'PLC': PLCValueDictToAll}
        elif act == "write":
            for key in writePLCSignalDict:
                self.getSetVal(DBnumber=writePLCSignalDict[key]['DBnumber'], Readstart=writePLCSignalDict[key]['readStart'],
                               Readsize=writePLCSignalDict[key]['readSize'], varType=writePLCSignalDict[key]['varType'],
                               bitNum=writePLCSignalDict[key]['bitNum'], setVar=writePLCSignalDict[key]['value'])
        plc_queue.task_done()

    
    def sendAllVarialble(self,inputDict):
        tempDict={}
        for key in inputDict:
            inputDict[key]['value'] = self.getSetVal(DBnumber=inputDict[key]['DBnumber'], Readstart=inputDict[key]['readStart'],
            Readsize=inputDict[key]['readSize'],varType=inputDict[key]['varType'],bitNum=inputDict[key]['bitNum'])
            # print(inputDict[key]['value'] )
            tempDict.update({key:inputDict[key]['value']})
        # print(tempDict)
        return {'PLC':tempDict}

    def setAllVarialble(self,inputDict):
        for key in inputDict:
            # print(inputDict[key]['value'])
            self.getSetVal(DBnumber=inputDict[key]['DBnumber'], Readstart=inputDict[key]['readStart'],
            Readsize=inputDict[key]['readSize'],varType=inputDict[key]['varType'],
            bitNum=inputDict[key]['bitNum'],setVar=inputDict[key]['value'])
        
        # print("all finished")

    # 订单设置
    def orderSet(self,dictPLC):
        #设置颜色
        self.getSetVal(DBnumber=20,Readstart=6,Readsize=2,
        varType="Int",bitNum=None,setVar = int(dictPLC['colorWeb']))
        #设置自动起飞
        self.getSetVal(DBnumber=20,Readstart=8,Readsize=1,
        varType="Bool",bitNum=0,setVar = self.stringToBool(dictPLC['flyWeb']))
        #设置装夹电池
        self.getSetVal(DBnumber=20,Readstart=8,Readsize=1,
        varType="Bool",bitNum=1,setVar = self.stringToBool(dictPLC['batteryWeb']))
        #设置需要打印
        boolNeedToPrint=self.getSetVal(DBnumber=20,Readstart=8,Readsize=1,
        varType="Bool",bitNum=2,setVar = self.stringToBool(dictPLC['printWeb']))
        #设置需要签名
        boolNeedSginature = self.getSetVal(DBnumber=20,Readstart=8,Readsize=1,
        varType="Bool",bitNum=3,setVar=self.stringToBool(dictPLC['signatureWeb']))
    
    def stringToBool(self,str):
        if str == "1" or "true" or "True" or "TRUE":
            return True
        else:
            return False
