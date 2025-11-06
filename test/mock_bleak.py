"""Mock BleakClient for offline testing (placed in test/ folder).

This is a copy of the mock used for testing, but colocated under `test/` so test code is self-contained.
"""

import asyncio

class MockBleakClient:
    def __init__(self, address):
        self.address = address
        self.is_connected = False
        self.written = []  # 存储 (characteristic_uuid, bytes)

    async def connect(self):
        # 模拟连接延迟
        await asyncio.sleep(0.05)
        self.is_connected = True
        print(f"[MockBleakClient] connected to {self.address}")

    async def disconnect(self):
        await asyncio.sleep(0.01)
        self.is_connected = False
        print(f"[MockBleakClient] disconnected from {self.address}")

    async def write_gatt_char(self, characteristic_uuid, data, response=True):
        # 记录发送的命令
        self.written.append((characteristic_uuid, data))
        print(f"[MockBleakClient] write to {characteristic_uuid}: {data}")
        # 模拟短延迟
        await asyncio.sleep(0.01)

    def get_commands(self):
        return [(uuid, data.decode('utf-8') if isinstance(data, (bytes, bytearray)) else data)
                for uuid, data in self.written]