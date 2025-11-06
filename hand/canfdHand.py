import time
import threading
import keyboard
from ctypes import *
import platform
import struct

ZCAN_DEVICE_TYPE = c_uint

INVALID_DEVICE_HANDLE  = 0
INVALID_CHANNEL_HANDLE = 0

'''
 Device Type
'''
ZCAN_USBCANFD_200U    = ZCAN_DEVICE_TYPE(41)
ZCAN_USBCANFD_100U    = ZCAN_DEVICE_TYPE(42)
'''
 Interface return status
'''
ZCAN_STATUS_ERR         = 0
ZCAN_STATUS_OK          = 1
ZCAN_STATUS_ONLINE      = 2
ZCAN_STATUS_OFFLINE     = 3
ZCAN_STATUS_UNSUPPORTED = 4

'''
 CAN type
'''
ZCAN_TYPE_CAN    = c_uint(0)
ZCAN_TYPE_CANFD  = c_uint(1)



'''
 Device information
'''
class ZCAN_DEVICE_INFO(Structure):
    _fields_ = [("hw_Version", c_ushort),
                ("fw_Version", c_ushort),
                ("dr_Version", c_ushort), 
                ("in_Version", c_ushort), 
                ("irq_Num", c_ushort),
                ("can_Num", c_ubyte),
                ("str_Serial_Num", c_ubyte * 20),
                ("str_hw_Type", c_ubyte * 40),
                ("reserved", c_ushort * 4)]

    def __str__(self):
        return "Hardware Version:%s\nFirmware Version:%s\nDriver Interface:%s\nInterface Interface:%s\nInterrupt Number:%d\nCAN Number:%d\nSerial:%s\nHardware Type:%s\n" %(
                self.hw_version, self.fw_version, self.dr_version, self.in_version, self.irq_num, self.can_num, self.serial, self.hw_type)
                
    def _version(self, version):
        return ("V%02x.%02x" if version // 0xFF >= 9 else "V%d.%02x") % (version // 0xFF, version & 0xFF)
    
    @property
    def hw_version(self):
        return self._version(self.hw_Version)

    @property
    def fw_version(self):
        return self._version(self.fw_Version)
    
    @property
    def dr_version(self):
        return self._version(self.dr_Version)
    
    @property
    def in_version(self):
        return self._version(self.in_Version)

    @property
    def irq_num(self):
        return self.irq_Num

    @property
    def can_num(self):
        return self.can_Num

    @property
    def serial(self):
        serial = ''
        for c in self.str_Serial_Num:
            if c > 0: 
               serial += chr(c)
            else:
                break 
        return serial

    @property
    def hw_type(self):
        hw_type = ''
        for c in self.str_hw_Type:
            if c > 0:
                hw_type += chr(c)
            else:
                break
        return hw_type

class _ZCAN_CHANNEL_CAN_INIT_CONFIG(Structure):
    _fields_ = [("acc_code", c_uint),
                ("acc_mask", c_uint),
                ("reserved", c_uint),
                ("filter",   c_ubyte),
                ("timing0",  c_ubyte),
                ("timing1",  c_ubyte),
                ("mode",     c_ubyte)]

class _ZCAN_CHANNEL_CANFD_INIT_CONFIG(Structure):
    _fields_ = [("acc_code",     c_uint),
                ("acc_mask",     c_uint),
                ("abit_timing",  c_uint),
                ("dbit_timing",  c_uint),
                ("brp",          c_uint),
                ("filter",       c_ubyte),
                ("mode",         c_ubyte),
                ("pad",          c_ushort),
                ("reserved",     c_uint)]

class _ZCAN_CHANNEL_INIT_CONFIG(Union):
    _fields_ = [("can", _ZCAN_CHANNEL_CAN_INIT_CONFIG), ("canfd", _ZCAN_CHANNEL_CANFD_INIT_CONFIG)]

class ZCAN_CHANNEL_INIT_CONFIG(Structure):
    _fields_ = [("can_type", c_uint),
                ("config", _ZCAN_CHANNEL_INIT_CONFIG)]

class ZCAN_CHANNEL_ERR_INFO(Structure):
    _fields_ = [("error_code", c_uint),
                ("passive_ErrData", c_ubyte * 3),
                ("arLost_ErrData", c_ubyte)]

class ZCAN_CHANNEL_STATUS(Structure):
    _fields_ = [("errInterrupt", c_ubyte),
                ("regMode",      c_ubyte),
                ("regStatus",    c_ubyte), 
                ("regALCapture", c_ubyte),
                ("regECCapture", c_ubyte),
                ("regEWLimit",   c_ubyte),
                ("regRECounter", c_ubyte),
                ("regTECounter", c_ubyte),
                ("Reserved",     c_ubyte)]

class ZCAN_CAN_FRAME(Structure):
    _fields_ = [("can_id",  c_uint, 29),
                ("err",     c_uint, 1),
                ("rtr",     c_uint, 1),
                ("eff",     c_uint, 1), 
                ("can_dlc", c_ubyte),
                ("__pad",   c_ubyte),
                ("__res0",  c_ubyte),
                ("__res1",  c_ubyte),
                ("data",    c_ubyte * 8)]

class ZCAN_CANFD_FRAME(Structure):
    _fields_ = [("can_id", c_uint, 29), 
                ("err",    c_uint, 1),
                ("rtr",    c_uint, 1),
                ("eff",    c_uint, 1), 
                ("len",    c_ubyte),
                ("brs",    c_ubyte, 1),
                ("esi",    c_ubyte, 1),
                ("__pad",  c_ubyte, 6),
                ("__res0", c_ubyte),
                ("__res1", c_ubyte),
                ("data",   c_ubyte * 64)]

class ZCANdataFlag(Structure):
    _pack_  =  1
    _fields_= [("frameType",c_uint,2),
               ("txDelay",c_uint,2),
               ("transmitType",c_uint,4),
               ("txEchoRequest",c_uint,1),
               ("txEchoed",c_uint,1),
               ("reserved",c_uint,22),
               ]



class ZCANFDData(Structure):            ##表示 CAN/CANFD 帧结构,目前仅作为 ZCANDataObj 结构的成员使用
    _pack_  =  1
    _fields_= [("timestamp",c_uint64),
               ("flag",ZCANdataFlag),
               ("extraData",c_ubyte*4),
               ("frame",ZCAN_CANFD_FRAME),]





class ZCANDataObj(Structure):
    _pack_  =  1
    _fields_= [("dataType",c_ubyte),
               ("chnl",c_ubyte),
               ("flag",c_ushort),
               ("extraData",c_ubyte*4),
               ("zcanfddata",ZCANFDData),##88个字节
               ("reserved",c_ubyte*4),
               ]
    
class ZCAN_Transmit_Data(Structure):
    _fields_ = [("frame", ZCAN_CAN_FRAME), ("transmit_type", c_uint)]

class ZCAN_Receive_Data(Structure):
    _fields_  = [("frame", ZCAN_CAN_FRAME), ("timestamp", c_ulonglong)]

class ZCAN_TransmitFD_Data(Structure):
    _fields_ = [("frame", ZCAN_CANFD_FRAME), ("transmit_type", c_uint)]

class ZCAN_ReceiveFD_Data(Structure):
    _fields_ = [("frame", ZCAN_CANFD_FRAME), ("timestamp", c_ulonglong)]

class ZCAN_AUTO_TRANSMIT_OBJ(Structure):
    _fields_ = [("enable",   c_ushort),
                ("index",    c_ushort),
                ("interval", c_uint),
                ("obj",      ZCAN_Transmit_Data)]

class ZCANFD_AUTO_TRANSMIT_OBJ(Structure):
    _fields_ = [("enable",   c_ushort),
                ("index",    c_ushort),
                ("interval", c_uint),
                ("obj",      ZCAN_TransmitFD_Data)]

class ZCANFD_AUTO_TRANSMIT_OBJ_PARAM(Structure):   #auto_send delay
    _fields_ = [("indix",  c_ushort),
                ("type",   c_ushort),
                ("value",  c_uint)]

class IProperty(Structure):
    _fields_ = [("SetValue", c_void_p), 
                ("GetValue", c_void_p),
                ("GetPropertys", c_void_p)]



class ZCAN(object):
    def __init__(self):
        if platform.system() == "Windows":
            self.__dll = windll.LoadLibrary("./zlgcan/zlgcan_x64/zlgcan.dll")
        else:
            print("No support now!")
        if self.__dll == None:
            print("DLL couldn't be loaded!")

    def OpenDevice(self, device_type, device_index, reserved):
        try:
            return self.__dll.ZCAN_OpenDevice(device_type, device_index, reserved)
        except:
            print("Exception on OpenDevice!") 
            raise

    def CloseDevice(self, device_handle):
        try:
            return self.__dll.ZCAN_CloseDevice(device_handle)
        except:
            print("Exception on CloseDevice!")
            raise

    def GetDeviceInf(self, device_handle):
        try:
            info = ZCAN_DEVICE_INFO()
            ret = self.__dll.ZCAN_GetDeviceInf(device_handle, byref(info))
            return info if ret == ZCAN_STATUS_OK else None
        except:
            print("Exception on ZCAN_GetDeviceInf")
            raise

    def DeviceOnLine(self, device_handle):
        try:
            return self.__dll.ZCAN_IsDeviceOnLine(device_handle)
        except:
            print("Exception on ZCAN_ZCAN_IsDeviceOnLine!")
            raise

    def InitCAN(self, device_handle, can_index, init_config):
        try:
            return self.__dll.ZCAN_InitCAN(device_handle, can_index, byref(init_config))
        except:
            print("Exception on ZCAN_InitCAN!")
            raise

    def StartCAN(self, chn_handle):
        try:
            return self.__dll.ZCAN_StartCAN(chn_handle)
        except:
            print("Exception on ZCAN_StartCAN!")
            raise

    def ResetCAN(self, chn_handle):
        try:
            return self.__dll.ZCAN_ResetCAN(chn_handle)
        except:
            print("Exception on ZCAN_ResetCAN!")
            raise

    def ClearBuffer(self, chn_handle):
        try:
            return self.__dll.ZCAN_ClearBuffer(chn_handle)
        except:
            print("Exception on ZCAN_ClearBuffer!")
            raise

    def ReadChannelErrInfo(self, chn_handle):
        try:
            ErrInfo = ZCAN_CHANNEL_ERR_INFO()
            ret = self.__dll.ZCAN_ReadChannelErrInfo(chn_handle, byref(ErrInfo))
            return ErrInfo if ret == ZCAN_STATUS_OK else None
        except:
            print("Exception on ZCAN_ReadChannelErrInfo!")
            raise

    def ReadChannelStatus(self, chn_handle):
        try:
            status = ZCAN_CHANNEL_STATUS()
            ret = self.__dll.ZCAN_ReadChannelStatus(chn_handle, byref(status))
            return status if ret == ZCAN_STATUS_OK else None
        except:
            print("Exception on ZCAN_ReadChannelStatus!")
            raise

    def GetReceiveNum(self, chn_handle, can_type = ZCAN_TYPE_CAN):
        try:
            return self.__dll.ZCAN_GetReceiveNum(chn_handle, can_type)
        except:
            print("Exception on ZCAN_GetReceiveNum!")
            raise

    def Transmit(self, chn_handle, std_msg, len):
        try:
            return self.__dll.ZCAN_Transmit(chn_handle, byref(std_msg), len)
        except:
            print("Exception on ZCAN_Transmit!")
            raise

    def Receive(self, chn_handle, rcv_num, wait_time = c_int(-1)):
        try:
            rcv_can_msgs = (ZCAN_Receive_Data * rcv_num)()
            ret = self.__dll.ZCAN_Receive(chn_handle, byref(rcv_can_msgs), rcv_num, wait_time)
            return rcv_can_msgs, ret
        except:
            print("Exception on ZCAN_Receive!")
            raise
    
    def TransmitFD(self, chn_handle, fd_msg, len):
        try:
            return self.__dll.ZCAN_TransmitFD(chn_handle, byref(fd_msg), len)
        except:
            print("Exception on ZCAN_TransmitFD!")
            raise
    
            
    def TransmitData(self,device_handle,msg,len):
        try:
            return self.__dll.ZCAN_TransmitData(device_handle,byref(msg),len)
        except:
            print("Exception on ZCAN_TransmitData!")
            raise
    def ReceiveFD(self, chn_handle, rcv_num, wait_time = c_int(-1)):
        try:
            rcv_canfd_msgs = (ZCAN_ReceiveFD_Data * rcv_num)()
            ret = self.__dll.ZCAN_ReceiveFD(chn_handle, byref(rcv_canfd_msgs), rcv_num, wait_time)
            return rcv_canfd_msgs, ret
        except:
            print("Exception on ZCAN_ReceiveF D!")
            raise

    def ReceiveData(self,device_handle,rcv_num,wait_time = c_int(-1)):
        try:
            rcv_can_data_msgs = (ZCANDataObj * rcv_num)()
            ret = self.__dll.ZCAN_ReceiveData(device_handle , rcv_can_data_msgs, rcv_num,wait_time)
            return  rcv_can_data_msgs ,ret
        except:
            print("Exception on ZCAN_ReceiveData!")
            raise


    def GetIProperty(self, device_handle):
        try:
            self.__dll.GetIProperty.restype = POINTER(IProperty)
            return self.__dll.GetIProperty(device_handle)
        except:
            print("Exception on ZCAN_GetIProperty!")
            raise

    def SetValue(self, iproperty, path, value):
        try:
            func = CFUNCTYPE(c_uint, c_char_p, c_char_p)(iproperty.contents.SetValue)
            return func(c_char_p(path.encode("utf-8")), c_char_p(value.encode("utf-8")))
        except:
            print("Exception on IProperty SetValue")
            raise
            
    def SetValue1(self, iproperty, path, value):                                              #############################
        try:
            func = CFUNCTYPE(c_uint, c_char_p, c_char_p)(iproperty.contents.SetValue)
            return func(c_char_p(path.encode("utf-8")), c_void_p(value))
        except:
            print("Exception on IProperty SetValue")
            raise
            

    def GetValue(self, iproperty, path):
        try:
            func = CFUNCTYPE(c_char_p, c_char_p)(iproperty.contents.GetValue)
            return func(c_char_p(path.encode("utf-8")))
        except:
            print("Exception on IProperty GetValue")
            raise

    def ReleaseIProperty(self, iproperty):
        try:
            return self.__dll.ReleaseIProperty(iproperty)
        except:
            print("Exception on ZCAN_ReleaseIProperty!")
            raise
        
    def ZCAN_SetValue(self,device_handle,path,value):
        try:
            self.__dll.ZCAN_SetValue.argtypes=[c_void_p,c_char_p,c_void_p]
            return self.__dll.ZCAN_SetValue(device_handle,path.encode("utf-8"),value)
        except:
            print("Exception on ZCAN_SetValue")
            raise
    
    def ZCAN_GetValue(self,device_handle,path):
        try:
            self.__dll.ZCAN_GetValue.argtypes =[c_void_p,c_char_p]
            self.__dll.ZCAN_GetValue.restype =c_void_p
            return self.__dll.ZCAN_GetValue(device_handle,path.encode("utf-8"))
        except:
            print("Exception on ZCAN_GetValue")
            raise

class HandClient:
    def __init__(self, sys_id=0, channel=0, device_type=ZCAN_USBCANFD_100U, device_index=0):
        self.sys_id = sys_id
        self.channel = channel
        self.device_type = device_type
        self.device_index = device_index
        self.device_handle = None
        self.channel_handle = None
        self.zcanlib = ZCAN()
        self.connected = False
        self.status = {}  # 存储各手指状态
        self.recv_thread = None
        self.running = False
        if self.connect():
            print("Connection successful!")
        else:
            print("Connection failed")
        
    def connect(self):
        """连接CAN设备并初始化通道"""
        # 打开设备
        self.device_handle = self.zcanlib.OpenDevice(self.device_type, self.device_index, 0)
        if self.device_handle == INVALID_DEVICE_HANDLE:
            print("Open CANFD Device failed!")
            return False
            
        # 获取设备信息
        info = self.zcanlib.GetDeviceInf(self.device_handle)
        print(f"Device Information:\n{info}")
        
        # 配置通道
        if not self._config_channel():
            self.zcanlib.CloseDevice(self.device_handle)
            return False
            
        # 启动接收线程
        self.running = True
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()
        
        self.connected = True
        print("Connected to hand controller")
        return True
        
    def _config_channel(self):
        """配置CAN通道"""
        # 设置CANFD模式
        ret = self.zcanlib.ZCAN_SetValue(self.device_handle, 
                                        f"{self.channel}/canfd_standard", 
                                        "0".encode("utf-8"))
        if ret != ZCAN_STATUS_OK:
            print(f"Set CH{self.channel} CANFD standard failed!")
            return False
            
        # 设置内部终端电阻
        ret = self.zcanlib.ZCAN_SetValue(self.device_handle, 
                                        f"{self.channel}/initenal_resistance", 
                                        "1".encode("utf-8"))
        if ret != ZCAN_STATUS_OK:
            print(f"Open CH{self.channel} resistance failed!")
            return False
            
        # 设置波特率
        ret = self.zcanlib.ZCAN_SetValue(self.device_handle,
                                        f"{self.channel}/canfd_abit_baud_rate",
                                        "1000000".encode("utf-8"))
        if ret != ZCAN_STATUS_OK:
            print(f"Set CH{self.channel} baud failed!")
            return False
            
        # 初始化通道
        chn_init_cfg = ZCAN_CHANNEL_INIT_CONFIG()
        chn_init_cfg.can_type = ZCAN_TYPE_CANFD
        chn_init_cfg.config.canfd.mode = 0  # 正常模式
        
        self.channel_handle = self.zcanlib.InitCAN(self.device_handle, self.channel, chn_init_cfg)
        if self.channel_handle == 0:
            print(f"InitCAN CH{self.channel} failed!")
            return False
        time.sleep(0.1)
        # 启动CAN通道
        ret = self.zcanlib.StartCAN(self.channel_handle)
        if ret != ZCAN_STATUS_OK:
            print(f"StartCAN CH{self.channel} failed!")
            return False
            
        print(f"Channel {self.channel} initialized and started")
        return True
        
    def disconnect(self):
        """断开连接"""
        if not self.connected:
            return True
            
        self.running = False
        if self.recv_thread and self.recv_thread.is_alive():
            self.recv_thread.join(timeout=1.0)
            
        if self.channel_handle:
            self.zcanlib.ResetCAN(self.channel_handle)
            
        if self.device_handle:
            self.zcanlib.CloseDevice(self.device_handle)
            
        self.connected = False
        print("Disconnected")
        return True
        
    def _recv_loop(self):
        """接收反馈数据的线程"""
        while self.running:
            # 获取可接收的帧数量
            rcv_num = self.zcanlib.GetReceiveNum(self.channel_handle, ZCAN_TYPE_CANFD)
            if rcv_num > 0:
                # 接收帧
                rcv_canfd_msgs, rcv_num = self.zcanlib.ReceiveFD(self.channel_handle, rcv_num, 10)  # 10ms超时
                
                for i in range(rcv_num):
                    frame = rcv_canfd_msgs[i].frame
                    # 只处理来自灵巧手的反馈帧 (ID = 0x180 + sys_id)
                    if frame.can_id == (0x180 + self.sys_id):
                        self._parse_feedback(frame.data, frame.len)
                        
            time.sleep(0.01)  # 短暂休眠

    def _recv_now(self):
        # 获取可接收的帧数量
        rcv_num = self.zcanlib.GetReceiveNum(self.channel_handle, ZCAN_TYPE_CANFD)
        if rcv_num > 0:
            # 接收帧
            rcv_canfd_msgs, rcv_num = self.zcanlib.ReceiveFD(self.channel_handle, rcv_num, 10)  # 10ms超时
            
            for i in range(rcv_num):
                frame = rcv_canfd_msgs[i].frame
                # 只处理来自灵巧手的反馈帧 (ID = 0x180 + sys_id)
                if frame.can_id == (0x180 + self.sys_id):
                    self._parse_feedback(frame.data, frame.len)

    def _parse_feedback(self, data, length):
        """解析反馈数据"""
        if length < 48:
            return
            
        try:
            # 解析手指ID (D0-D1)
            finger_id = data[0] | (data[1] << 8)
            
            # 解析各字段 (小端序)
            status = {
                'angle': struct.unpack('<h', bytes(data[2:4]))[0],          # D2-D3: 角度(度*100)
                'driver_temp': struct.unpack('<i', bytes(data[4:8]))[0],    # D4-D7: 驱动板温度(℃)
                'position': struct.unpack('<i', bytes(data[8:12]))[0],      # D8-D11: 当前位置
                'speed': struct.unpack('<h', bytes(data[12:14]))[0],        # D12-D13: 速度(度/秒)
                'current': struct.unpack('<h', bytes(data[14:16]))[0],      # D14-D15: 电流(mA)
                'motor_temp': struct.unpack('<h', bytes(data[16:18]))[0],   # D16-D17: 电机温度(℃)
                'torque': struct.unpack('<h', bytes(data[18:20]))[0],       # D18-D19: 力矩(PWM)
                'voltage': struct.unpack('<H', bytes(data[20:22]))[0] * 0.001,  # D20-D21: 电压(V)
                'normal_force': struct.unpack('<f', bytes(data[24:28]))[0], # D24-D27: 法向力(N)
                'tangential_force': struct.unpack('<f', bytes(data[32:36]))[0],  # D32-D35: 切向力(N)
                'tangential_direction': struct.unpack('<H', bytes(data[40:42]))[0],  # D40-D41: 切向力方向(°)
                'proximity': struct.unpack('<I', bytes(data[44:48]))[0]    # D44-D47: 接近觉
            }
            
            # 更新状态
            self.status[finger_id] = status
        except Exception as e:
            print(f"Error parsing feedback: {e}")
            
    def _send_control_frame(self, finger_id, position, torque):
        """发送控制指令到指定手指"""
        if not self.connected:
            print("Not connected")
            return False
            
        # 构造控制帧 (标准CAN帧，8字节)
        control_frame = ZCAN_Transmit_Data()
        control_frame.transmit_type = 0  # 正常发送
        control_frame.frame.eff = 0      # 标准帧
        control_frame.frame.rtr = 0      # 数据帧
        control_frame.frame.can_id = 0x100 + self.sys_id  # 控制帧ID
        
        # 填充数据 (协议格式)
        control_frame.frame.can_dlc = 8
        control_frame.frame.data[0] = 0x06  # 控制指令标识
        control_frame.frame.data[1] = finger_id  # 手指ID
        # 位置 (小端序)
        control_frame.frame.data[2] = position & 0xFF
        control_frame.frame.data[3] = (position >> 8) & 0xFF
        # 力矩 (小端序)
        control_frame.frame.data[4] = torque & 0xFF
        control_frame.frame.data[5] = (torque >> 8) & 0xFF
        # 保留字节
        control_frame.frame.data[6] = 0
        control_frame.frame.data[7] = 0
        
        # 发送控制帧
        try:
            ret = self.zcanlib.Transmit(self.channel_handle, control_frame, 1)
            return ret == 1
        except Exception as e:
            print(f"Send control frame error: {e}")
            return False

    def _send_control_frame_hall(self, finger_id, position, velocity):
        """发送控制指令到指定手指"""
        if not self.connected:
            print("Not connected")
            return False
            
        # 构造控制帧 (标准CAN帧，8字节)
        control_frame = ZCAN_Transmit_Data()
        control_frame.transmit_type = 0  # 正常发送
        control_frame.frame.eff = 0      # 标准帧
        control_frame.frame.rtr = 0      # 数据帧
        control_frame.frame.can_id = 0x100 + self.sys_id  # 控制帧ID
        
        # 填充数据 (协议格式)
        control_frame.frame.can_dlc = 8
        control_frame.frame.data[0] = 0x06  # 控制指令标识
        control_frame.frame.data[1] = finger_id  # 手指ID
        # 位置 (小端序)
        control_frame.frame.data[2] = position & 0xFF
        control_frame.frame.data[3] = (position >> 8) & 0xFF
        # 力矩 (小端序)
        control_frame.frame.data[4] = velocity & 0xFF
        control_frame.frame.data[5] = (velocity >> 8) & 0xFF
        # 保留字节
        control_frame.frame.data[6] = 0
        control_frame.frame.data[7] = 0
        
        # 发送控制帧
        try:
            ret = self.zcanlib.Transmit(self.channel_handle, control_frame, 1)
            return ret == 1
        except Exception as e:
            print(f"Send control frame error: {e}")
            return False
            
    def grip(self):
        """执行抓取动作"""
        success = True
        for finger_id in range(1, 4):
            success &= self._send_control_frame(finger_id, 250, 200)
            time.sleep(0.01)
            self._recv_now()
        return success
    
    def release(self):
        """执行松开动作"""
        success = True
        for finger_id in range(1, 4):
            success &= self._send_control_frame(finger_id, 0, 200)
            time.sleep(0.01)
            self._recv_now()
        return success
    
    def reset(self):
        """复位手部"""
        # 先清除错误
        success = True
        self.clear_errors()
        # 然后释放所有手指
        for finger_id in range(1, 4):
            success &= self._send_control_frame_hall(finger_id, 0, 350)
            time.sleep(0.01)
            self._recv_now()
        return success
    
    def clear_errors(self):
        """清除错误"""
        if not self.connected:
            print("Not connected")
            return False
            
        # 构造错误清除帧
        control_frame = ZCAN_Transmit_Data()
        control_frame.transmit_type = 0  # 正常发送
        control_frame.frame.eff = 0      # 标准帧
        control_frame.frame.rtr = 0      # 数据帧
        control_frame.frame.can_id = 0x100 + self.sys_id  # 控制帧ID
        
        # 填充数据 (错误清除指令)
        control_frame.frame.can_dlc = 8
        control_frame.frame.data[0] = 0x03  # 错误清除指令
        control_frame.frame.data[1] = 0xA4
        for i in range(2, 8):
            control_frame.frame.data[i] = 0  # 填充0
            
        # 发送错误清除指令
        try:
            ret = self.zcanlib.Transmit(self.channel_handle, control_frame, 1)
            return ret == 1
        except Exception as e:
            print(f"Clear errors error: {e}")
            return False
    
    def get_status(self, finger_id=None):
        """获取当前状态"""
        if finger_id:
            return self.status.get(finger_id, {})
        return self.status

def keyboard_listener(client):
    """键盘监听线程"""
    print("\nControls:")
    print("  G - Grip")
    print("  R - Release")
    print("  + - Increase grip hall value")
    print("  - - Decrease grip hall value")
    print("  S - Show status")
    print("  X - Reset hand")
    print("  D - Disconnect")
    print("  C - Connect")
    print("  Q - Quit")
    
    while True:
        cmd = input("\nEnter command (h for help): ").strip().lower()
        
        if not cmd:
            continue
            
        if cmd == 'q':
            print("Exiting...")
            client.disconnect()
            break
            
        elif cmd == 'g':
            client.grip()
            
        elif cmd == 'r':
            client.reset()
            
        elif cmd == '+':
            status = client.get_status()
            if "grip_hall_value" in status:
                new_value = status["grip_hall_value"] + 50
                client.set_grip_hall_value(new_value)
                
        elif cmd == '-':
            status = client.get_status()
            if "grip_hall_value" in status:
                new_value = status["grip_hall_value"] - 50
                client.set_grip_hall_value(new_value)
                
        elif cmd == 's':
            print("\nCurrent Status:")
            for fid, status in client.get_status().items():
                print(f"Finger {fid}:")
                for k, v in status.items():
                    print(f"  {k}: {v}")

if __name__ == "__main__":
    # 创建灵巧手客户端
    client = HandClient(sys_id=0, channel=0, device_type=ZCAN_USBCANFD_100U)
    
    keyboard_listener(client)