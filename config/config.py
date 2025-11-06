import os
import yaml

def _load_yaml():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'config.yaml')
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_CFG = _load_yaml()
_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

class systemConfig:
    def __init__(self):
        # 读取应用程序配置
        app_cfg = _CFG.get('app', {})
        self.PLC_IP = app_cfg.get('PLC_IP', '192.168.58.10')
        self.laserPrinterFilePath = app_cfg.get('laserPrinterFilePath', '')
        self.laserPrinterSignaturePath = app_cfg.get('laserPrinterSignaturePath', '')
        
        # 读取PLC信号配置
        self.PLCConfig = _CFG.get('plc_signals', {})

        # 读取机器人动作配置
        self.robotConfig = _CFG.get('robot_actions', {})

        # 读取AGV蓝牙配置
        self.AGVs = _CFG.get('agvs', {})
        if self.AGVs:
            # 默认使用第一个设备的配置，用于向后兼容
            first = next(iter(self.AGVs.values()))
            self.AGV_address = first.get('address', '')
            self.AGV_characteristic_uuid = first.get('characteristic_uuid', '')
        else:
            self.AGV_address = ''
            self.AGV_characteristic_uuid = ''

        # 保存内部引用到全局配置对象，便于修改并持久化
        self._raw_cfg = _CFG

        # 读取机器人IP配置
        robot_ip = _CFG.get('IPconfig', {}).get('robot_ip', {})
        self.robot_ip = {
            'HOST': robot_ip.get('HOST', '192.168.58.2'),
            'PORT': robot_ip.get('PORT', 502)
        }

    # ---------- 持久化操作：对 config.yaml 中的 AGV 列表进行快速增删 ----------
    def _write_yaml(self):
        """内部方法：把 _raw_cfg 写回 config.yaml"""
        try:
            with open(_CFG_PATH, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._raw_cfg, f, allow_unicode=True, sort_keys=False)
            # 同步内存副本
            return True
        except Exception as e:
            print(f"写入配置文件失败: {e}")
            return False

    def add_agv(self, device_id: str, address: str, characteristic_uuid: str) -> bool:
        """往 config.yaml 中添加一个 AGV 设备（持久化）。

        返回 True 表示成功，False 表示失败或已存在。
        """
        if 'agvs' not in self._raw_cfg or not isinstance(self._raw_cfg.get('agvs'), dict):
            self._raw_cfg['agvs'] = {}

        if device_id in self._raw_cfg['agvs']:
            print(f"设备 {device_id} 已存在")
            return False

        self._raw_cfg['agvs'][device_id] = {'address': address, 'characteristic_uuid': characteristic_uuid}
        ok = self._write_yaml()
        if ok:
            # 更新运行时副本
            self.AGVs[device_id] = {'address': address, 'characteristic_uuid': characteristic_uuid}
            # 如果当前默认为空，设置为这个设备
            if not self.AGV_address:
                self.AGV_address = address
                self.AGV_characteristic_uuid = characteristic_uuid
        return ok

    def remove_agv(self, device_id: str) -> bool:
        """从 config.yaml 中删除一个 AGV 设备（持久化）。

        返回 True 表示成功，False 表示失败或不存在。
        """
        if 'agvs' not in self._raw_cfg or device_id not in self._raw_cfg['agvs']:
            print(f"设备 {device_id} 不存在")
            return False

        del self._raw_cfg['agvs'][device_id]
        ok = self._write_yaml()
        if ok:
            # 更新运行时副本
            if device_id in self.AGVs:
                del self.AGVs[device_id]
            # 如果删除的是默认设备，尝试切换默认
            if self.AGV_address and device_id == 'agv_001':
                if self.AGVs:
                    first = next(iter(self.AGVs.values()))
                    self.AGV_address = first.get('address', '')
                    self.AGV_characteristic_uuid = first.get('characteristic_uuid', '')
                else:
                    self.AGV_address = ''
                    self.AGV_characteristic_uuid = ''
        return ok

    def list_agvs(self):
        """返回当前内存中的 AGV 列表（device_id -> {address, characteristic_uuid}）"""
        return self.AGVs.copy()