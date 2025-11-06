from typing import Dict, Optional
from bleak import BleakClient
import asyncio
from dataclasses import dataclass
from config.config import systemConfig


@dataclass
class AGVDevice:
    """AGV设备类，用于存储AGV设备的信息"""
    device_id: str
    name: str
    address: str
    characteristic_uuid: str
    status: str = "disconnected"
    client: Optional[BleakClient] = None

    async def connect(self) -> bool:
        """连接AGV设备"""
        try:
            self.client = BleakClient(self.address)
            await self.client.connect()
            self.status = "connected"
            print(f"设备 {self.name}({self.device_id}) 连接成功")
            return True
        except Exception as e:
            print(f"设备 {self.name}({self.device_id}) 连接失败: {e}")
            self.status = "disconnected"
            return False

    async def disconnect(self):
        """断开AGV设备连接"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            self.status = "disconnected"
            print(f"设备 {self.name}({self.device_id}) 已断开连接")

    async def send_command(self, command: str):
        """发送命令到AGV设备"""
        if not self.client or not self.client.is_connected:
            raise ConnectionError("设备未连接")
        
        try:
            encoded_command = command.encode('utf-8')
            await self.client.write_gatt_char(self.characteristic_uuid, encoded_command, response=True)
            print(f"发送命令到设备 {self.name}({self.device_id}): {command}")
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False


class AGVDeviceManager:
    """AGV设备管理器，用于管理多个AGV设备"""
    def __init__(self):
        self.devices: Dict[str, AGVDevice] = {}

    def register_device(self, device_id: str, name: str, address: str, 
                       characteristic_uuid: str = systemConfig.AGV_characteristic_uuid) -> AGVDevice:
        """注册新的AGV设备"""
        if device_id in self.devices:
            raise ValueError(f"设备ID {device_id} 已存在")
        
        device = AGVDevice(
            device_id=device_id,
            name=name,
            address=address,
            characteristic_uuid=characteristic_uuid
        )
        self.devices[device_id] = device
        print(f"注册新设备: {name}({device_id})")
        return device

    def unregister_device(self, device_id: str):
        """注销AGV设备"""
        if device_id not in self.devices:
            raise ValueError(f"设备ID {device_id} 不存在")
        
        device = self.devices[device_id]
        if device.status == "connected":
            asyncio.create_task(device.disconnect())
        
        del self.devices[device_id]
        print(f"注销设备: {device.name}({device_id})")

    def get_device(self, device_id: str) -> Optional[AGVDevice]:
        """获取指定的AGV设备"""
        return self.devices.get(device_id)

    def get_all_devices(self) -> Dict[str, AGVDevice]:
        """获取所有注册的AGV设备"""
        return self.devices.copy()

    async def connect_device(self, device_id: str) -> bool:
        """连接指定的AGV设备"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"设备ID {device_id} 不存在")
        return await device.connect()

    async def disconnect_device(self, device_id: str):
        """断开指定的AGV设备连接"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"设备ID {device_id} 不存在")
        await device.disconnect()

    async def send_command_to_device(self, device_id: str, command: str) -> bool:
        """向指定的AGV设备发送命令"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"设备ID {device_id} 不存在")
        return await device.send_command(command)