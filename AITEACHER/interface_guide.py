"""Offline, searchable student guide matching the application's workflow."""
from pathlib import Path
import sys

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                             QSplitter, QTextBrowser, QVBoxLayout, QWidget)
from styles import dialog_stylesheet

CHAPTERS = [
('从这里开始：第一次使用', '''## 这款软件能做什么？
AI 导师帮助你完成小马嵌入式开发：创建工程、学习代码、按需求生成动作、预览仿真、编译固件，再连接实物验证。没有焊接完成的同学，也可先学习和做仿真。

### 推荐的第一次操作
1. 打开顶部 **新建工程**，选择 **机器马入门工程（前进、趴下）**。
2. 选择纯英文工作空间，例如 `D:/e2s_workspace`，填写英文工程名。
3. 工程创建后，点击 **3D 仿真**，在右侧遥控区体验前进和趴下。
4. 要使用 AI，请先完成 **API 设置**，再在右侧说出需求，例如“请添加后退动作，保留前进和趴下”。
5. 查看修改，重新载入仿真验证；保存后编译，最后在硬件上烧录测试。

### 新生电脑需要准备什么？
接收完整的 `RenesasHorseTutor` 软件文件夹并保留目录结构，从其中的 exe 启动。教程、模型、阅读与播放组件随软件提供；不要只复制 exe。
AI 需要网络和你配置的 API。教程、取模与仿真可离线使用。连接实物时，电脑需正确识别串口设备；修改外设配置需安装 RASC 或 e2 studio。
'''),
('认识界面：顶部、左侧、中央、右侧', '''### 顶部：选择工具
- **界面引导**：这份使用手册，支持目录和关键词搜索。
- **打开工程 / 保存代码**：选择工程、保存编辑。
- **新建工程 / RASC配置**：创建教学工程，配置芯片外设。
- **3D 仿真 / 进阶教程 / OLED 取模 / 串口调试**：动作预览、资料学习、图像数据制作和真实设备通信。
- **一键编译 / 一键烧录**：生成固件并下载到开发板。
- **阶段 / API 设置 / 亮色或暗色模式**：选择学习方式、配置 AI、切换外观。

### 左侧：工程与功能入口
工程树中选择源文件。高级模式提供 **代码指引** 入口，仿真也有对应入口。

### 中央：当前工作区
显示代码编辑器、参考代码区或 3D 仿真。切回工程文件即可继续编辑。

### 右侧：AI 导师
输入需求或问题，查看解释和修改记录。高级模式另有课程切换与知识详解。

### 下方：编译输出
编译时显示日志与问题列表。双击问题条目可定位对应代码行。
'''),
('新建工程：从两个动作逐步扩展', '''### 操作步骤
1. 点击 **新建工程**，选择模板。
2. 选择工作空间，填写工程名；路径和名称使用英文、数字，避免中文与空格。
3. 确认创建，等待复制完成。机器马模板已经包含所需的外设配置与构建文件。

### 有哪些模板？
- LED 点灯工程：学习 GPIO 输出。
- 舵机控制工程：学习定时器、PWM 与角度。
- OLED 显示工程：学习 I2C 与屏幕显示。
- 机器马入门工程：通过蓝牙控制前进和趴下。

### 入门机器马的初始动作
发送 ASCII 字符 **1**：趴下；**2**：前进。发送时不追加换行。前进完成后恢复基础姿态，上电也有内部姿态复位。
左转、右转、后退、摇尾巴等功能，等你提出对应需求后再由 AI 生成。新模板只影响之后新建的工程，已有工程保持自己的代码。

### 学习示例
先体验前进，再提出“请把前进速度稍微调慢，其他不变”；比较代码中的延时变化和仿真效果。接着提出“请新增后退，并分配一个未占用的蓝牙字符”。
'''),
('打开工程、编辑与保存', '''### 打开已有工程
点击 **打开工程**，选择工程根目录，而不是单独的 `.c` 文件。根目录通常含 `src`、`ra_gen`、`configuration.xml`，可编译工程还应有带 makefile 的 `Debug` 目录。

### 编辑流程
1. 在左侧工程树点击文件，在中央查看或编辑。
2. 应用代码主要位于 `src`；外设生成文件位于 `ra_gen`、`ra_cfg` 等目录。
3. 点击 **保存代码** 保存编辑。切换工程或退出时，如出现未保存提示，按需要保存后继续。
4. 编译读取磁盘上的文件；编译前处理保存提示，确保固件包含刚才的修改。

### 常用文件
- `hal_entry.c`：初始化、主循环与动作指令分支。
- `action.c / action.h`：动作实现与声明。
- `PWM.c / PWM.h`：舵机输出接口。
- `oled.c / oled.h`：OLED 底层显示接口。

文件名以你当前工程为准。RASC 生成目录建议通过配置工具更新。
'''),
('API 设置：启用 AI', '''### 必填的三个字段
- **base_url**：服务商提供的 API 接口基础地址，不是网页登录页面。
- **api_key**：你在服务商平台创建的完整密钥。
- **model**：该接口支持的准确模型标识，不是自己给密钥起的名称。

### 操作步骤
1. 向课程老师或 API 服务商确认这三项信息。
2. 打开 **API 设置**，填写并保存。软件没有可代用的默认 AI 配置。
3. 选择合适档位；先使用均衡档体验。
4. 回到右侧，发送一个简短问题确认响应正常。

### 连接失败时
检查网络、接口地址、模型名以及账户是否有可用额度。认证错误通常需要核对密钥；模型不存在时应核对模型标识。保留错误文字，便于老师排查。

密钥用于访问你的 API 账户，请勿把包含完整密钥的截图发给其他人。初级模式会按需求读取相关工程代码并发送给所配置的 AI 服务。
'''),
('初级模式：让 AI 按需求修改代码', '''### 适合什么情况？
你希望先看到具体效果，通过提出需求、观察修改和验证结果理解代码。

### 操作步骤
1. 顶部 **阶段** 选择 **初级（直接生成）**，打开目标工程并配置 API。
2. 在右侧描述一个明确需求，例如“新增左转动作，保留已有前进和趴下”。
3. 等待 AI 读取代码、修改相关文件；查看回复中的文件差异。
4. 打开对应文件检查修改，重新载入仿真，再运行编译。
5. 如果效果不对，描述实际现象与预期差别，让 AI 调整本次功能。

### 如何提问更有效？
一次提出一个可验证变化，如速度、重复次数、某个动作或显示内容。说明要保留哪些已有行为。入门工程不会预先补齐所有动作。

### 查看与撤销
修改卡片可以定位文件；出现 **撤销这次修改** 时，可回退该次 AI 修改。撤销前留意自己随后编辑的内容，先保存需要保留的代码。
AI 生成后仍应检查仿真、编译和实物效果；成功回复不等于硬件已经验证。
'''),
('高级模式：课程与代码指引', '''### 适合什么情况？
你希望亲自编写代码，让 AI 提供讲解和参考。

### 操作步骤
1. 将 **阶段** 切换为 **高级（引导思考）**。
2. 使用课程的上一步、下一步或课程选择入口学习相应内容。
3. 点击左侧 **代码指引**，在中央查看参考代码。
4. 在右侧询问具体实现，例如“给我 PWM 舵机驱动的参考代码，并解释占空比换算”。
5. 选择需要的代码片段或参考文件，点击 **复制当前代码**，自行粘贴到合适的工程位置。
6. 检查函数声明、调用位置与依赖，保存后编译验证。

### 与初级模式的区别
高级模式主要提供参考与解释，由你完成工程编辑。代码指引以课程的 Dog 实例工程为参考；参考工程包含更多完整功能，不代表你的入门工程已实现这些动作。
代码指引中的内容不会因显示出来就自动写入学生工程。
'''),
('知识详解与进阶教程', '''### 知识详解
在高级模式切到要学习的课程，点击 **知识详解**。弹窗解释当前步骤相关概念；AI 讲解需要有效 API 和网络。若加载报错，核对 API 设置和错误信息。

### 进阶教程
点击顶部 **进阶教程**，在下拉框选择：
- 瑞萨入门教程 1–9。
- 瑞萨入门教程 10–19。
- OLED 专题教程。
- 蓝牙串口操作视频。
- 小马建模与 3D 打印教程。

### 阅读 PDF
左侧目录可展开章节，输入关键词筛选标题，点击跳转。顶部可切换上一页、下一页，输入页码或改变缩放方式。点击目录按钮可隐藏目录、扩大阅读区域。

### 播放视频
选择蓝牙视频后点击播放，可暂停、拖动进度条及调节音量。切换教程会停止当前视频，关闭窗口会暂停播放。
教材在软件内打开，不需要另找原文件，也不需要使用 AI 才能阅读。
'''),
('3D 仿真：先观察动作，再烧录', '''### 操作步骤
1. 打开你的工程，点击 **3D 仿真**。代码会自动载入，无需再点开始或播放。
2. 右侧蓝牙遥控区显示当前源码支持的动作。入门模板初始只有前进和趴下。
3. 点击动作按钮，观察四肢、尾巴及 OLED 输出。
4. 拖动场景旋转视角，滚轮缩放；需要时点击复位视角。
5. 修改代码后点击 **重新载入代码**，以当前内容重新运行。

### 模拟手机蓝牙软件
在遥控卡片的“我的控制按钮”处点击 **添加**，填写按钮名称和要发送的内容。例如按钮名称填“左转”，发送内容填 `4`。保存后即可像手机蓝牙串口软件一样点击发送。

发送内容支持数字、英文字母和英文符号，最长 32 个字符；多字符会按虚拟串口逐字节发送。自定义按钮保存在本机，可随时删除。按钮只是发送数据，代码中仍需有接收并处理该数据的分支，才会产生对应动作。

### 新动作为什么没有按钮？
动作不仅需要函数，还需要主循环中的指令分支与蓝牙接收逻辑。请确认 AI 同步完成这些部分，再重新载入。仅添加函数声明不会自动形成可执行的遥控动作。

### 动作指令如何执行？
按钮通过虚拟蓝牙送入当前代码。当前动作执行中，会保留最后一次按钮指令，等待程序再次接收。
未打开学生工程时，仿真使用内置完整 Dog 示例，因此可能看到更多按钮；练习自己的代码时先打开对应工程。

### 仿真能验证什么？
用于观察动作顺序、延时、关节输出与屏幕变化。它支持课程工程的部分 C 和外设行为，并不是完整芯片、电路或供电仿真。修改后仍需编译，最后通过实物校准和验证。
'''),
('角度测算与物理参数', '''### 测算舵机输入值
1. 在仿真页面点击 **角度测算**。
2. 拖动四肢或尾巴对应滑块，摆出目标姿态。
3. 查看对应整数输入、可达角度与脉宽，复制整数代码。
4. 将相关 `*_SetDuty(...)` 调用用于自己的动作函数，并添加合适延时。
5. 返回遥控，恢复之前的仿真。

测算期间暂停代码与物理。输入值对应关系由当前工程驱动计算，不应把一个工程的整数值直接套到任意舵机项目。

### 校准与物理环境
舵机校准可调整零位、方向与角度比例。物理环境可调整质量、重心、摩擦和力矩等参数。调整后按页面按钮应用；需要重新比较时恢复标准参数。

显示角度和机械参数是教学模型的估计结果。真实零位、安装方向、载荷与摩擦可能不同，最终应结合实物确认。
'''),
('OLED 取模：图片、文字与手绘', '''### 图片取模
1. 点击顶部 **OLED 取模**，导入 PNG、JPG 或 BMP 等图片。
2. 设定宽高，选择等比留白或拉伸。
3. 调整黑白阈值；根据需要反色、旋转或镜像，以点阵预览为准。

### 文字取模
选择文字取模，输入文字、字体和像素字号。调整画布尺寸，让文字完整放入；超出画布的部分会裁切。

### 手动修改点阵
左键绘点，右键擦除；清空点阵可从空白开始画。修改来源或转换参数会重新生成点阵，覆盖手工修改。

### 生成工程代码
1. 填写合法数组名和显示坐标。
2. 复制 C 代码，或导出 `.h` 文件；也可保存点阵 PNG。
3. 数组定义只放在一个编译单元中；若导出头文件，将它包含在需要的一个 `.c` 文件中。
4. 把示例中的 `OLED_ShowPicture` 和 `OLED_Refresh` 调用放入实际显示函数，按需要清屏。
5. 编译并观察仿真 OLED。

工具按标准工程的 128×64 屏幕编码：纵向 8 点、低位在上、按页排列。高度会补齐到 8 的倍数，连同显示坐标不能超出屏幕。预览按程序坐标显示，实物竖装时可按需要旋转素材。
'''),
('串口调试：与真实设备通信', '''### 连接步骤
1. 接入设备，点击 **串口调试 → 刷新串口**。
2. 选择对应端口，按设备要求设置波特率、数据位、校验和停止位。
3. 点击打开串口，确认状态显示已连接。默认波特率为 9600，实际必须与设备一致。
4. 输入发送内容并点击发送，在接收区观察设备回复。

### 小马指令示例
入门工程：文本输入 `1` 是趴下，`2` 是前进，选择 **不追加**。十六进制方式对应 `31`、`32`，不要把十六进制 `01` 当作 ASCII 字符 `1`。
后续新增动作的指令以自己的源码为准。

### 收发选项
文本支持 UTF-8、GBK、ASCII；十六进制按完整字节输入，例如 `01 A0 FF`。文本可追加 LF、CR 或 CRLF，十六进制发送按输入字节原样发送。
勾选定时发送后按间隔重复发送，取消勾选可停止。可查看收发字节数、接收时间并保存当前接收日志；长时间接收仅保留有限历史，重要内容及时保存。

### 常见问题
没有端口：检查连接、设备驱动并刷新。打开失败：确认端口未被其他软件占用。乱码：检查波特率和编码。关闭窗口会断开串口并停止定时发送；烧录前先释放需要共用的串口。
'''),
('RASC 配置：修改外设', '''### 什么时候使用？
需要改变引脚、定时器、UART 波特率、I2C 或其它 FSP 配置时，点击 **RASC配置**。简单动作调整通常只改应用代码。

### 操作步骤
1. 先打开目标工程。
2. 点击 RASC配置，软件尝试启动本机 RASC 或 e2 studio。
3. 在配置工具中修改所需外设，确认引脚与实物一致，生成代码并保存。
4. 返回 AI 导师，核对应用代码使用的控制块和回调名称，重新编译。

### 打不开怎么办？
该入口需要本机安装 RASC 或 e2 studio，并且工程有 `configuration.xml`。请按课程环境要求安装；不要用手工改生成文件代替正常配置流程，后续生成可能覆盖修改。
'''),
('一键编译与问题定位', '''### 操作步骤
1. 打开完整工程并保存源代码。
2. 点击 **一键编译**，检查工具链与 make 路径，按提示开始。
3. 下方输出面板显示构建日志和问题列表，等待结果。
4. 编译成功会生成 `.srec` 等固件，并自动填入烧录窗口。

### 遇到错误
双击问题列表中的条目，跳到对应文件和行。把关键报错和预期行为交给 AI 导师处理，再重新编译。
找不到 Debug/makefile 时，先用 e2 studio 生成并构建工程。工程路径使用纯英文，避免路径编码问题。

### 彻底重编
外设生成文件或构建配置改变后，必要时选择彻底重编，重新构建全部编译单元。普通动作修改通常可直接增量编译。
编译成功表示固件能生成，不代表每个动作、电气连接或实际姿态都正确。
'''),
('一键烧录与实物验证', '''### 烧录前
先确认编译成功，检查烧录窗口中的固件是本次工程最新产物。准备开发板、数据线和正确的串口，关闭占用同一端口的串口调试窗口。

### 操作步骤
1. 按课程开发板要求将 BOOT 开关拨到 ON，并重新上电进入烧录状态。
2. 点击 **一键烧录**，核对烧录工具、端口、固件路径等参数。
3. 开始烧录，等待完成提示，过程中保持连接稳定。
4. 成功后将 BOOT 拨回 OFF，再重新上电运行。
5. 用对应蓝牙或串口指令测试动作，比较仿真与实物效果。

### 失败排查
检查端口选择、BOOT 状态、是否重新上电、固件路径和连接。端口被占用时先退出使用它的程序；不能只凭上一次编译成功就选择旧固件。
'''),
('常见问题与完整学习任务', '''### AI 无法使用
先配置 API 的地址、密钥和模型；检查网络与服务商返回错误。离线教材、取模和仿真仍可使用。

### 仿真没有显示新增动作
先确认打开的是目标工程，再重新载入。检查动作实现、头文件声明和蓝牙指令分支是否都已添加。

### 改了代码，实物没变化
保存代码，重新编译，核对固件路径，再烧录并重启。比较当前动作参数是否真的变化，OLED 是否调用刷新。

### 想换亮色或暗色
点击顶部主题按钮。界面引导也会同步切换，正文和目录仍可使用。

### 一次完整的学习练习
1. 新建机器马入门工程，体验前进、趴下。
2. 向 AI 提出“添加后退，保留原有动作，使用未占用的蓝牙指令”。
3. 查看哪些函数、声明、分支发生变化，记录指令字符。
4. 重新载入仿真，点击新增动作观察效果。
5. 保存、编译、烧录，在实物上验证。
6. 切换高级模式，询问关键代码原理，再尝试自己修改速度或步数。

这份界面引导无需联网。左侧搜索会同时匹配章节标题和正文，清空搜索可恢复全部目录。
''')]

CATEGORIES = (
    '开始使用', 'AI 与学习', '仿真与工具', '编译与硬件', '问题排查'
)


def chapter_category(index):
    if index <= 3:
        return CATEGORIES[0]
    if index <= 7:
        return CATEGORIES[1]
    if index <= 11:
        return CATEGORIES[2]
    if index <= 14:
        return CATEGORIES[3]
    return CATEGORIES[4]


class InterfaceGuide(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('界面引导 · AI 导师使用手册')
        self.setMinimumSize(820, 600)
        available = self.screen().availableGeometry()
        self.resize(min(1180, available.width() - 60),
                    min(820, available.height() - 80))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.matches = []
        self.current_chapter = 0
        self._theme = 'dark'

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        hero = QFrame()
        hero.setObjectName('guideHero')
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 14, 20, 14)
        hero_layout.setSpacing(14)

        logo = QLabel()
        logo.setObjectName('guideLogo')
        asset_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        pixmap = QPixmap(str(asset_root / 'assets' / 'app_icon.png'))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(58, 58, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(62, 62)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(logo)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel('AI 导师使用手册')
        title.setObjectName('guideHeroTitle')
        subtitle = QLabel('从第一次打开软件，到仿真、编译和实物验证')
        subtitle.setObjectName('guideHeroSubtitle')
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        hero_layout.addLayout(heading, 1)

        badge = QLabel('● 离线可用  ·  16 节')
        badge.setObjectName('guideOfflineBadge')
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(badge)
        root.addWidget(hero)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setObjectName('guideSplitter')
        split.setHandleWidth(7)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        sidebar = QFrame()
        sidebar.setObjectName('guideSidebar')
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 14)
        sidebar_layout.setSpacing(10)
        nav_title = QLabel('学习目录')
        nav_title.setObjectName('guideSectionTitle')
        sidebar_layout.addWidget(nav_title)

        self.search = QLineEdit()
        self.search.setObjectName('guideSearch')
        self.search.setPlaceholderText('搜索功能或问题…')
        self.search.setClearButtonEnabled(True)
        sidebar_layout.addWidget(self.search)

        self.category = QComboBox()
        self.category.setObjectName('guideCategory')
        self.category.addItems(['全部章节', *CATEGORIES])
        sidebar_layout.addWidget(self.category)

        self.count = QLabel()
        self.count.setObjectName('guideResultCount')
        sidebar_layout.addWidget(self.count)

        self.contents = QListWidget()
        self.contents.setObjectName('guideContents')
        self.contents.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.contents.setSpacing(6)
        sidebar_layout.addWidget(self.contents, 1)

        tip = QLabel('提示：先选章节，再按关键词查找具体问题。')
        tip.setObjectName('guideSidebarTip')
        tip.setWordWrap(True)
        sidebar_layout.addWidget(tip)
        split.addWidget(sidebar)

        content = QFrame()
        content.setObjectName('guideContentCard')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(22, 20, 22, 16)
        content_layout.setSpacing(8)

        self.chapter_meta = QLabel()
        self.chapter_meta.setObjectName('guideChapterMeta')
        content_layout.addWidget(self.chapter_meta)
        self.chapter_title = QLabel()
        self.chapter_title.setObjectName('guideChapterTitle')
        self.chapter_title.setWordWrap(True)
        content_layout.addWidget(self.chapter_title)

        self.reader = QTextBrowser()
        self.reader.setObjectName('guideReader')
        self.reader.setOpenExternalLinks(False)
        content_layout.addWidget(self.reader, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.prev_button = QPushButton('←  上一节')
        self.prev_button.setObjectName('guideNavSecondary')
        self.position = QLabel()
        self.position.setObjectName('guidePosition')
        self.position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = QPushButton('下一节  →')
        self.next_button.setObjectName('guideNavPrimary')
        footer.addWidget(self.prev_button)
        footer.addStretch(1)
        footer.addWidget(self.position)
        footer.addStretch(1)
        footer.addWidget(self.next_button)
        content_layout.addLayout(footer)
        split.addWidget(content)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([315, 825])

        self.search.textChanged.connect(self.filter)
        self.category.currentIndexChanged.connect(self.filter)
        self.contents.currentRowChanged.connect(self.show_chapter)
        self.prev_button.clicked.connect(lambda: self._step(-1))
        self.next_button.clicked.connect(lambda: self._step(1))

        self.apply_theme(getattr(parent, 'current_theme', 'dark'))
        self.filter()

    def _nav_card(self, chapter_index):
        card = QFrame()
        card.setObjectName('guideNavItem')
        card.setProperty('selected', False)
        card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        number = QLabel(f'{chapter_index + 1:02}')
        number.setObjectName('guideNavNumber')
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setFixedSize(34, 34)
        row.addWidget(number)
        text = QVBoxLayout()
        text.setSpacing(1)
        title = QLabel(CHAPTERS[chapter_index][0])
        title.setObjectName('guideNavTitle')
        title.setWordWrap(True)
        category = QLabel(chapter_category(chapter_index))
        category.setObjectName('guideNavCategory')
        text.addWidget(title)
        text.addWidget(category)
        row.addLayout(text, 1)
        return card

    def apply_theme(self, theme):
        self._theme = 'light' if theme == 'light' else 'dark'
        if self._theme == 'light':
            p = dict(window='#eef3f7', hero='#ffffff', sidebar='#f7fafc',
                     card='#ffffff', text='#193044', muted='#6b7d8d',
                     border='#cbd8e2', accent='#087f70', soft='#e3f4f0',
                     input='#ffffff', reader='#ffffff', code='#edf3f7')
        else:
            p = dict(window='#0d151e', hero='#172433', sidebar='#111c27',
                     card='#15212d', text='#edf5fa', muted='#9eb0bf',
                     border='#304556', accent='#63dbc3', soft='#183b3c',
                     input='#0e1923', reader='#111c26', code='#0b141c')
        self.setStyleSheet(dialog_stylesheet(self._theme, 'unused') + f'''
            QDialog {{ background: {p['window']}; }}
            QFrame#guideHero, QFrame#guideContentCard {{
                background: {p['hero']}; border: 1px solid {p['border']}; border-radius: 14px;
            }}
            QFrame#guideSidebar {{
                background: {p['sidebar']}; border: 1px solid {p['border']}; border-radius: 12px;
            }}
            QLabel#guideHeroTitle {{ color: {p['text']}; font-size: 22px; font-weight: 700; }}
            QLabel#guideHeroSubtitle, QLabel#guideSidebarTip, QLabel#guideResultCount {{
                color: {p['muted']}; font-weight: 400;
            }}
            QLabel#guideOfflineBadge {{
                color: {p['accent']}; background: {p['soft']}; border-radius: 14px;
                padding: 7px 12px; font-weight: 600;
            }}
            QLabel#guideSectionTitle {{ color: {p['text']}; font-size: 17px; font-weight: 700; }}
            QLineEdit#guideSearch, QComboBox#guideCategory {{
                color: {p['text']}; background: {p['input']}; border: 1px solid {p['border']};
                border-radius: 8px; padding: 8px 10px; min-height: 22px;
            }}
            QComboBox#guideCategory QAbstractItemView {{
                color: {p['text']}; background: {p['input']};
                selection-background-color: {p['soft']}; selection-color: {p['text']};
            }}
            QListWidget#guideContents {{ background: transparent; border: none; outline: none; }}
            QListWidget#guideContents::item {{ background: transparent; border: none; }}
            QFrame#guideNavItem {{
                background: transparent; border: 1px solid transparent; border-radius: 9px;
            }}
            QFrame#guideNavItem[selected="true"] {{
                background: {p['soft']}; border: 1px solid {p['accent']};
            }}
            QLabel#guideNavNumber {{
                color: {p['accent']}; background: {p['soft']}; border-radius: 17px; font-weight: 700;
            }}
            QLabel#guideNavTitle {{ color: {p['text']}; font-size: 13px; font-weight: 600; }}
            QLabel#guideNavCategory {{ color: {p['muted']}; font-size: 11px; font-weight: 400; }}
            QLabel#guideChapterMeta {{ color: {p['accent']}; font-size: 12px; font-weight: 700; }}
            QLabel#guideChapterTitle {{ color: {p['text']}; font-size: 24px; font-weight: 700; }}
            QTextBrowser#guideReader {{
                color: {p['text']}; background: {p['reader']}; border: none;
                border-top: 1px solid {p['border']}; padding: 14px 4px 8px 4px;
                font-size: 15px;
            }}
            QLabel#guidePosition {{ color: {p['muted']}; min-width: 90px; }}
            QPushButton#guideNavPrimary, QPushButton#guideNavSecondary {{
                min-width: 108px; padding: 8px 14px; border-radius: 8px; font-weight: 700;
            }}
            QPushButton#guideNavPrimary {{ background: {p['accent']}; color: {p['window']}; border: none; }}
            QPushButton#guideNavSecondary {{ color: {p['text']}; background: {p['input']}; border: 1px solid {p['border']}; }}
            QPushButton#guideNavPrimary:disabled, QPushButton#guideNavSecondary:disabled {{
                color: {p['muted']}; background: {p['sidebar']}; border: 1px solid {p['border']};
            }}
            QSplitter#guideSplitter::handle {{ background: transparent; }}
        ''')
        self.reader.document().setDefaultStyleSheet(f'''
            body {{ color: {p['text']}; line-height: 1.55; }}
            h2 {{ color: {p['accent']}; font-size: 20px; margin-top: 18px; margin-bottom: 10px; }}
            h3 {{ color: {p['text']}; font-size: 16px; margin-top: 16px; margin-bottom: 8px; }}
            p {{ margin-top: 7px; margin-bottom: 11px; }}
            li {{ margin-bottom: 7px; }}
            code {{ color: {p['accent']}; background: {p['code']}; padding: 2px 5px; }}
        ''')
        self._refresh_nav_selection()

    def filter(self, *_):
        query = self.search.text().strip().casefold()
        selected_category = self.category.currentText()
        previous = self.current_chapter
        self.matches = [
            index for index, (title, body) in enumerate(CHAPTERS)
            if (not query or query in (title + ' ' + body).casefold())
            and (selected_category == '全部章节' or
                 chapter_category(index) == selected_category)
        ]
        self.contents.blockSignals(True)
        self.contents.clear()
        for chapter_index in self.matches:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, chapter_index)
            item.setSizeHint(QSize(260, 62))
            self.contents.addItem(item)
            self.contents.setItemWidget(item, self._nav_card(chapter_index))
        self.contents.blockSignals(False)
        self.count.setText(f'显示 {len(self.matches)} / {len(CHAPTERS)} 节')
        if self.matches:
            row = self.matches.index(previous) if previous in self.matches else 0
            self.contents.setCurrentRow(row)
            self.show_chapter(row)
        else:
            self.chapter_meta.setText('没有匹配结果')
            self.chapter_title.setText('换一个关键词试试')
            self.reader.setHtml('<p>可搜索“API”“左转”“仿真”“编译”或清空搜索条件。</p>')
            self.position.setText('0 / 0')
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

    def _refresh_nav_selection(self):
        current = self.contents.currentRow()
        for row in range(self.contents.count()):
            card = self.contents.itemWidget(self.contents.item(row))
            if card is None:
                continue
            card.setProperty('selected', row == current)
            card.style().unpolish(card)
            card.style().polish(card)

    def show_chapter(self, row):
        if not 0 <= row < len(self.matches):
            return
        self.current_chapter = self.matches[row]
        title, body = CHAPTERS[self.current_chapter]
        self.chapter_meta.setText(
            f'{chapter_category(self.current_chapter)}  ·  第 {self.current_chapter + 1:02d} 节'
        )
        self.chapter_title.setText(title)
        self.reader.setMarkdown(body)
        cursor = self.reader.textCursor()
        cursor.setPosition(0)
        self.reader.setTextCursor(cursor)
        self.reader.verticalScrollBar().setValue(0)
        self.position.setText(f'{row + 1} / {len(self.matches)}')
        self.prev_button.setEnabled(row > 0)
        self.next_button.setEnabled(row + 1 < len(self.matches))
        self._refresh_nav_selection()

    def _step(self, delta):
        if not self.matches:
            return
        row = max(0, min(self.contents.count() - 1,
                         self.contents.currentRow() + delta))
        self.contents.setCurrentRow(row)
