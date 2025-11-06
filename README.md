# Industry 控制系统 — 项目说明文档

> 说明：本文档以中文撰写，覆盖仓库结构、各模块职责、启动/停止方法、运行先决条件、常见错误与调试建议，以及后续改进建议。

## 一、项目概览

这是一个混合异步/多线程的工业控制仿真与集成工程，包含 AGV（蓝牙/BLE）、机器人控制、CNC 控制、PLC 交互、激光打印 Web 服务及灵巧手（CANFD）等子系统。项目旨在把各独立子模块以最小耦合方式集成到顶层 `main.py`，同时保留每个模块的可单独运行与调试接口。

主要语言：Python 3.9+ / 3.11（建议使用项目的 conda 环境）

关键第三方库（见 `requirements.txt`）：
- bleak（BLE）
- snap7（PLC）
- flask / flask-socketio（Web）
- numpy, opencv-python, scipy（机器人与视觉）
- python-socketio, websockets（实时/异步通信）

## 二、仓库结构（顶级说明）

- `main.py` — 顶层启动/编排程序（启动 PLC 循环、AGV 异步循环、CNC、激光 Web 等）。
- `config/` — 配置相关（`config.py`, `config.yaml`），包含 `systemConfig` 工厂/类，提供 `PLCConfig`、AGV 列表等配置信息。
- `core/` — 核心工具与周期逻辑：
  - `PLCCycle.py` — PLC 的读写周期、信号分发逻辑（把 PLC 信号映射为机器人/AGV/CNC/激光动作触发）。
  - `PLCutils.py` — PLC 低层读写封装（snap7 客户端封装）。
- `agv/` — AGV 子系统（BLE）：
  - `agvRun.py` — AGV 多设备管理：`AGV_States`、`start_agv_system()`、`stop_agv_system()`、`agv_control_loop(device_id, client)`。
  - `device/` — 设备模型与驱动模板。
- `robot/` — 机器人子系统：
  - `Robot.py` — XML-RPC / socket 的机器人 SDK 封装（RPC 客户端）。
  - `robotController.py` — 机器人高阶控制/位置变换、交互代码（含 `RobotController` 类）。
  - `robotAction.py` — 将 PLC/HMI 信号映射为机器人动作（`robotAction(key, robot)`）。
  - `PoseDetectionClient.py` — 远程姿态检测客户端（async websockets）。
- `cnc/` — CNC 控制：`cncRun.py`（UDP 命令发送、状态监测）。
- `laser/` — 激光打印 Web：
  - `laserWeb.py` — Flask 应用（前端/签名上传），已改为延迟创建 PLC 客户端。
  - `laserRun.py` — 与激光打印机 socket 通讯逻辑（启动雕刻流程）。
- `hand/` — 灵巧手驱动（CANFD），例如 `canfdHand.py`（低层 DLL 绑定及 HandClient）。
- `test/` — 离线测试与 Mock（例如 MockBleakClient 和 offline AGV 测试脚本）。
- `tools/` — 工具脚本（`check_imports.py` 等）用于快速检查工程导入/环境状态。

## 三、总体设计与并发模型

- AGV：基于 asyncio（Bleak），每台设备一个 `agv_control_loop(device_id, client)` 协程，通过 `start_agv_system()` 启动并返回任务列表。
- PLC：采用阻塞式周期（线程）读取/写入 PLC（snap7），在 `PLCCycle.PLCSignalCycle()` 中运行一个周期线程。为避免导入时阻塞，PLC 客户端实例化被改为延迟（on-demand）创建。
- CNC/Hand/激光：使用线程封装阻塞 I/O（UDP、TCP、DLL）。
- Robot：通过 XML-RPC 或 socket 与机器人控制器通信；高阶动作在独立线程中触发以避免阻塞 PLC 循环。

设计原则：模块负责自身运行模型（async 或 thread）。顶层只负责 orchestration（启动/停止）。模块间通过共享的配置/信号字典（`PLCSignalDict`、`writeInputDict`）或明确的 start/stop API 进行松耦合交互。

## 四、如何运行

1) 激活 conda 环境（假设你已创建并安装依赖）

```powershell
conda activate <your-project-env>
cd d:\Code\Industry
```

2) 运行项目（顶层）

```powershell
python main.py
```

说明：`main.py` 会：
- 初始化手部、机器人（会尝试连接到设备地址，若没有设备会打印警告并继续）
- 启动 PLC 周期线程、AGV 异步线程与 CNC 状态线程
- 启动激光打印的 Flask Web 服务（默认端口 5000）

3) 单模块运行（用于调试）
- 离线 AGV 测试（基于 Mock）：
  - 运行 `python -m test.test_offline_agv` 或相应脚本
- 激光 Web（独立运行）：
  - `python laser/laserWeb.py` （或以 `flask run` 的方式，视环境而定）

## 五、重要的 API / 函数说明

- AGV
  - `agv.agvRun.start_agv_system()` -> async: 连接注册设备并返回 control tasks
  - `agv.agvRun.stop_agv_system()` -> async: 向每台 AGV 发停止并断开连接
- PLC
  - `core.PLCutils.PLCUtils(ip, rack, slot)` -> PLC 客户端，含 `getSetVal`, `orderSet`, `PLC_Threading` 等辅助
  - `core.PLCCycle.PLCSignalCycle()` -> 线程函数，周期性读取 PLC 并触发子系统动作
- Robot
  - `robot.Robot.RPC(host)` -> 机器人 RPC 客户端
  - `robot.robotAction.robotAction(key, robot)` -> 执行与 PLC 信号对应的机器人动作
- CNC
  - `cnc.cncRun.CNCCommandExcute()` -> CNC 命令执行线程函数
  - `cnc.cncRun.CNCStatus()` -> 轮询 CNC 状态
- Laser
  - `laser.laserRun.startLaserPrinting(key)` -> 与雕刻机交互执行打印任务
  - `laser.laserWeb.get_plc()` -> 延迟获取 PLC 对象（避免导入期间建立网络连接）

## 六、常见问题与排查建议

1) 导入时报错 `ModuleNotFoundError: No module named 'robot'` 或 `No module named 'PoseDetectionClient'`
   - 原因：模块相对导入不一致、运行时的 `sys.path` 未包含项目根。
   - 解决：使用 `python -m tools.check_imports`（模块方式）或将项目根（d:\Code\Industry）加入 `PYTHONPATH`。

2) 导入时阻塞或大量重试日志（例如 snap7 报 `TCP : Unreachable peer`）
   - 原因：模块在导入阶段创建了 PLC 客户端并在无法连接时进行无限重试。
   - 解决：工程已将若干模块改为延迟创建 PLC（例如 `laser/laserWeb.py`）；如仍有模块在导入时创建 PLC 实例，需将其改为按需创建（`get_plc()`）或放入 `if __name__ == '__main__'`。

3) 机器人/PLC 连接失败
   - 在没有真实硬件时，运行会打印网络错误或超时。对于离线测试，请使用仓库中的 `test/mock_bleak.py` 与 `test/test_offline_agv.py`。

4) 线程/协程混用导致状态竞态
   - 请确保对共享结构（如 `writeInputDict`、`PLCSignalDict`）在必要处使用 `threading.Lock()` 或其他同步手段。`core/PLCCycle.py` 中已使用 `thread_lock` 在触发外部线程时保护关键区域。

## 七、测试策略与建议

- 单元与集成测试：建议逐步为关键模块添加 pytest 测试，优先覆盖：
  - `agv` 的状态转换与命令生成（通过 MockBleakClient）
  - `core.PLCutils` 的读写封装（通过模拟 snap7 返回的数据）
  - `robot.robotAction` 的动作触发逻辑（使用 Fake robot RPC）

- 离线/CI：创建一个 `test_ci` 任务，使用 Mock/仿真替代真实设备，在 CI 中执行非硬件依赖的测试。

## 八、已知短期改进项

1. 把所有模块的“启动/停止”封装成统一的 ModuleManager（注册/生命周期管理）。
2. 改进 `PLCutils.connect()` 的重试逻辑：避免递归调用并提供可配置的重试上限和退避策略。
3. 为每个模块增加健康检查接口（HTTP 或 socket），便于监控与自动恢复。
4. 增加日志配置（使用 `logging` 模块替代 print，并写入文件/控制台），便于分析生产环境问题。
5. 写若干 pytest 测试，并配置 GitHub Actions 或其它 CI 来自动运行 smoke tests。
