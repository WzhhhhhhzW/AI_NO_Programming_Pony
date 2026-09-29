# AI导师上位机

AI导师上位机是智能小马 AI 辅助嵌入式学习套件的 Windows 桌面程序。它围绕当前瑞萨 RA4M2 工程，提供工程浏览、代码编辑、AI 答疑、分步课程、编译诊断和固件烧录。初级模式支持受控修改源码；高级模式以十七课课程和只读答疑帮助学习者独立完成工程。

## 快速启动

在 `AI导师上位机/AITEACHER/` 下，双击：

```text
dist/RenesasHorseTutor/RenesasHorseTutor.exe
```

请保留 `dist/RenesasHorseTutor/` 整个文件夹。程序所需的 Qt、AI 客户端、工程模板和 `rfp-cli` 位于同级的 `_internal/` 中，仅复制 exe 无法保证正常运行。打包版无需另装 Python。

首次使用建议按下面的顺序操作：

1. 在“⚙️ API 设置”中填写可用的模型服务地址和密钥。AI 对话需要网络连接。当前版本的 Agent 会话使用 Anthropic 协议端点；若填写的是以 `/v1` 结尾的地址，程序会尝试换算为同一服务下的 `/anthropic` 地址。所用服务必须实际支持该端点。界面中的 `model` 字段用于“知识详解”功能，主对话模型由“档位”选择。
2. 点击“🆕 新建工程”选择内置模板，或点击“📂 打开工程”选择已有的 e² studio 工程根目录。RA 工程根目录应包含 `configuration.xml`。内置模板有 LED、舵机、OLED 和完整机器马四类。
3. 选择“初级（直接生成）”或“高级（引导思考）”。在右侧向 AI 导师提问；高级模式可用“上一步”“下一步”浏览课程。
4. 检查代码与修改差异，保存手动编辑的文件。点击“🔨 一键编译”，确认本次构建成功并生成 `.srec` 或 `.hex` 固件。
5. 将开发板连接到电脑，在“🔥 一键烧录”中确认串口、烧录工具和固件文件。按开发板要求将 BOOT 开关拨到 ON 并重新上电，再开始烧录。完成后将 BOOT 拨回 OFF，重新上电观察效果。

## 环境要求

| 用途 | 要求 |
| --- | --- |
| 运行打包版 | Windows；保留完整的 `dist/RenesasHorseTutor/` 文件夹 |
| AI 对话 | 网络连接，以及可用且兼容当前接口的模型服务配置 |
| 编译 RA 工程 | 可用的 `arm-none-eabi-gcc` 工具链、GNU Make 4.0 及含 `makefile` 的 `Debug/` 或 `Release/` 构建目录；通常通过 e² studio 安装与生成 |
| 修改 FSP 外设配置 | e² studio 或 RA Smart Configurator |
| 烧录开发板 | 可用的 `rfp-cli`、正确的串口、固件文件和硬件 BOOT 设置；打包版已带 `rfp-cli` |

工作空间及工程名称建议使用纯英文、数字路径，不要包含中文字符。当前程序会拒绝在含非 ASCII 字符的工程路径下编译，避免工具链路径编码问题。新建工程的工作空间也必须已存在并可写。

## 两种学习模式

**初级模式：** AI 可读取当前工程，并对 `src/` 内的 C/C++ 源文件进行局部编辑。程序在每轮修改前保存源码快照，结束后展示真实文件差异，并提供本轮撤销入口。AI 可执行受控的编译自检。它不能直接改动 FSP 自动生成目录；需要改变时钟、引脚、PWM 通道或通信配置时，应在 RASC 中操作。

**高级模式：** AI 可读取工程并调用编译诊断，但不具有编辑源码的工具权限。十七课按开发流程依次覆盖开发板测试、工程创建、外设配置、PWM 驱动、动作逻辑、OLED、主程序、烧录与蓝牙联调。课程进度在本次运行中维护，重新启动软件后从第一课开始。

两种模式下，AI 的解释和编译自检都不能代替实机检查。初级模式撤销源码后，如需让硬件回到旧行为，应重新编译并烧录。

## 编译与烧录说明

- “一键编译”针对当前打开的工程运行真实构建。设置窗口可填写工具链 `bin` 目录和 `make` 可执行文件；打包目录内未包含 Arm GNU 工具链及 GNU Make。
- 界面构建前会清理旧的 `.srec`、`.hex`、`.mot` 文件，并在成功后寻找本次固件。AI 在对话中的编译自检主要用于诊断；正式烧录应使用界面确认的构建产物。
- 编译成功后，固件路径会自动填入烧录窗口。烧录时再次核对文件、串口与 BOOT 状态。程序返回烧录成功后，还应查看小马的动作或显示是否达到目标。
- 若工程缺少含 `makefile` 的构建目录，先在 e² studio 中生成并构建一次工程。若编译工具不可用，在编译设置中指定对应路径。

## 从源码运行与重新打包

现有开发环境使用 Python 3.11。进入 `AI导师上位机/AITEACHER/` 后，可在 Windows 终端执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main_host_computer.py
```

源码入口为 `main_host_computer.py`。现有 `.venv` 记录了原开发机路径，换电脑时应重新创建。需要重新生成 Windows 打包版时：

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller RenesasHorseTutor.spec --noconfirm
```

打包输出在 `dist/RenesasHorseTutor/`。更多打包细节见 `打包说明.md`。

## 目录与配置

| 路径或文件 | 作用 |
| --- | --- |
| `main_host_computer.py` | 程序入口 |
| `ui_main.py` | 主界面与工作流程 |
| `advisor.py`、`prompts.py` | AI 会话、工具权限与教学提示 |
| `curriculum.py`、`lesson_flow.py` | 高级模式课程 |
| `project_manager.py`、`tools/templates/` | 模板工程创建 |
| `builder.py`、`build_tool.py`、`flasher.py` | 编译、自检与烧录 |
| `snapshot.py` | 初级模式的改动对比与撤销 |
| `requirements.txt`、`RenesasHorseTutor.spec` | 源码依赖与打包配置 |

用户配置和日志写入 `%APPDATA%\RenesasHorseAI\`。其中 `api_config.json` 保存 API 参数，`workspace_config.json` 保存工作空间和最近工程，`logs/` 存放运行日志。不要将包含密钥的配置文件发给他人。

## 常见问题

| 现象 | 先检查什么 |
| --- | --- |
| AI 无法读取或修改工程 | 是否先打开了正确的工程根目录；手动编辑的文件是否已保存；网络及 API 配置是否可用 |
| AI 不修改 `ra/` 等文件 | 这些是 FSP 生成内容；在 RASC 中调整配置后重新生成 |
| 编译提示找不到构建目录 | 工程的 `Debug/` 或 `Release/` 中是否有 `makefile` |
| 编译提示找不到工具 | 在“一键编译”设置中指定 Arm GNU 工具链和 GNU Make 路径 |
| 烧录后现象未变化 | 核对是否使用本次固件、BOOT 状态、串口、实际调用的函数、OLED 刷新，以及供电与接线 |

## 发布与维护注意

当前源码中存在预置 API 凭据。对外共享源码或重新打包发布前，应移除并轮换该凭据，改为由使用者自行配置；用户配置文件也应避免进入共享资料。旧版教学材料中关于模型名称、界面布局及复制代码的描述与当前程序不完全一致，使用说明以本 README 和当前源码为准。
