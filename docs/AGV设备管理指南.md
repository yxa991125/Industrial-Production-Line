# AGV设备管理指南

本文档介绍如何在系统中添加、删除和管理AGV设备。系统支持通过多种方式管理AGV设备：命令行工具、Python代码或配置文件直接编辑。

## 快速开始

### 使用命令行工具

我们提供了一个简单的命令行工具 `tools/manage_agv.py` 用于快速管理AGV设备。

1. 查看当前所有AGV设备：
```bash
python tools/manage_agv.py list
```

2. 添加新的AGV设备：
```bash
python tools/manage_agv.py add <设备ID> <蓝牙地址> <特征UUID>
```
例如：
```bash
python tools/manage_agv.py add agv_002 98:DA:B0:10:69:CB 0000ffe2-0000-1000-8000-00805f9b34fb
```

3. 删除AGV设备：
```bash
python tools/manage_agv.py remove <设备ID>
```
例如：
```bash
python tools/manage_agv.py remove agv_002
```

### 通过Python代码管理

如果您需要在代码中管理AGV设备，可以使用 `config.systemConfig` 类：

```python
from config.config import systemConfig

# 创建配置实例
cfg = systemConfig()

# 1. 添加新设备
success = cfg.add_agv(
    device_id="agv_002",
    address="98:DA:B0:10:69:CB",
    characteristic_uuid="0000ffe2-0000-1000-8000-00805f9b34fb"
)
if success:
    print("AGV设备添加成功")

# 2. 查看所有设备
devices = cfg.list_agvs()
for device_id, info in devices.items():
    print(f"设备: {device_id}")
    print(f"  地址: {info['address']}")
    print(f"  特征值: {info['characteristic_uuid']}")

# 3. 删除设备
if cfg.remove_agv("agv_002"):
    print("AGV设备删除成功")
```

## 配置文件格式

AGV设备信息存储在 `config/config.yaml` 中。系统支持两种格式：

### 1. 新格式（推荐）：支持多个AGV设备

```yaml
agvs:
  agv_001:
    address: '98:DA:B0:10:69:CA'
    characteristic_uuid: '0000ffe2-0000-1000-8000-00805f9b34fb'
  agv_002:
    address: '98:DA:B0:10:69:CB'
    characteristic_uuid: '0000ffe2-0000-1000-8000-00805f9b34fb'
```

### 2. 旧格式（向后兼容）：单个AGV设备

```yaml
agv:
  bluetooth_address: '98:DA:B0:10:69:CA'
  characteristic_uuid: '0000ffe2-0000-1000-8000-00805f9b34fb'
```

注：系统会自动将旧格式转换为新格式的内部表示。当您使用新的API添加设备时，配置文件会自动更新为新格式。

## 测试新添加的设备

添加设备后，您可以：

1. 启动测试API服务器：
```bash
python test_api_server.py
```

2. 使用浏览器访问 http://localhost:8000/docs 进行交互式测试

3. 或使用curl发送控制命令：
```bash
# 获取AGV状态
curl http://localhost:8000/agv/status

# 发送移动指令
curl -X POST http://localhost:8000/agv/command \
  -H "Content-Type: application/json" \
  -d '{"action":"forward"}'

# 发送停止指令
curl -X POST http://localhost:8000/agv/command \
  -H "Content-Type: application/json" \
  -d '{"action":"stop"}'
```

## 注意事项

1. **设备ID命名规范**：
   - 建议使用格式：`agv_XXX`，如 `agv_001`, `agv_002` 等
   - 仅使用字母、数字和下划线
   - 区分大小写

2. **蓝牙地址格式**：
   - 标准MAC地址格式：`XX:XX:XX:XX:XX:XX`
   - 必须是有效的蓝牙设备地址

3. **特征UUID格式**：
   - 标准UUID格式：`XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`
   - 对于AGV设备，通常是 `0000ffe2-0000-1000-8000-00805f9b34fb`

4. **并发注意事项**：
   - 避免多个进程同时修改配置文件
   - 修改配置后，需要重启使用该配置的程序才能生效

5. **备份建议**：
   - 修改配置前建议备份 `config.yaml`
   - 可以使用版本控制系统（如Git）跟踪配置变更

## 故障排除

1. 如果设备添加失败，检查：
   - 设备ID是否已存在
   - 蓝牙地址格式是否正确
   - 是否有权限写入配置文件

2. 如果设备无法连接，检查：
   - 蓝牙设备是否在范围内且已开启
   - 地址是否正确（可以用蓝牙调试工具验证）
   - 特征UUID是否正确

3. 如果配置文件出现问题：
   - 检查YAML格式是否正确
   - 尝试从备份恢复
   - 使用工具的list命令验证当前配置

## 扩展开发

如果您需要开发新的设备管理功能，可以：

1. 扩展 `systemConfig` 类添加新的管理方法
2. 修改 `tools/manage_agv.py` 添加新的命令行功能
3. 在 `agv/api.py` 中添加新的API端点

参考代码位置：
- 配置管理：`config/config.py`
- 命令行工具：`tools/manage_agv.py`
- API实现：`agv/api.py`