# Renesas 机器马 AI 导师 V16.21

面向瑞萨 RA4M2 机器马学习套件的 Windows AI 辅助开发软件，提供工程管理、代码学习、AI 编程辅导、3D 动作仿真、编译烧录、OLED 取模、串口调试和内置教程。

本分支 `AI_Teacher_Version_16.21` 保存 V16.21 源码，项目位于 [`AITEACHER/`](AITEACHER/)。

## 相比 V16.18 的主要更新

- **教程资料**：新增智能小马硬件安装教程、蓝牙小马 AI 辅助零编程高级模式教程和《AI 时代第一课：API 的调用》，可在软件内离线阅读。
- **按钮操作**：放大图片取模、教程阅读等窗口中的按钮和数值调节区域，补充深浅主题下清晰可见的上下箭头及按下反馈。
- **烧录端口**：一键烧录同时显示 COM 号和连接设备名称，支持刷新、保留选择和手动输入端口。
- **安装向导**：首次安装和升级均可选择安装位置；新增品牌欢迎页，统一中文字体，优化留白、步骤提示与说明文字。
- **界面引导**：移除顶部“离线可用 · 16 节”标识，保留章节搜索与阅读功能。

详细更新记录：

- [V16.19 教程与操作更新](AITEACHER/V16.19版本更新说明.md)
- [V16.20 界面与端口更新](AITEACHER/V16.20版本更新说明.md)
- [V16.21 安装向导更新](AITEACHER/V16.21版本更新说明.md)

## 从源码运行

在 `AITEACHER` 目录中使用 Python 3.11 创建虚拟环境，安装依赖后启动：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main_host_computer.py
```

使用 AI 功能前，请在软件的“API 设置”中填写服务地址、API 密钥和模型。教程资料可离线阅读。

## 打包

Windows 程序使用 PyInstaller 打包，安装向导使用 Inno Setup 6 编译。详见 [打包说明](AITEACHER/打包说明.md)。

本分支包含源码、教程、模型、工程模板和打包脚本；`.venv`、`build`、`dist`、运行日志及个人配置不随源码提交。
