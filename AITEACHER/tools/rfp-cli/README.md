# rfp-cli (Renesas Flash Programmer 命令行版)

来源：Renesas Flash Programmer Package V3.19.00 官方安装包
（课程 Gitee 仓库 https://gitee.com/CoreMaker/RA4M2_MINI 内附的
`Renesas_Flash_Programmer_Package_V31900-doc.zip`），
安装后从安装目录提取的最小可运行集合：

- `rfp-cli.exe`   命令行主程序（Windows，.NET 8 自包含）
- `RFP.dll` / `Common.dll`  依赖库
- `Devices.xml` / `Messages.xml`  设备数据库与消息表
- `rfp-cli.md`    官方命令行手册
- `License_Agreement.txt`  官方许可协议

未包含 `JLinkARM.dll` 和 `Firmwares/`（仅 J-Link/Flasher 硬件需要，
串口 boot 烧录用不到）。

典型用法（BOOT 开关拨 ON 后上电）：

```
rfp-cli -device ra -port COM3 -a firmware.hex -run
```

注意：此目录下的 exe 仅限 Windows。RFP V3.19 官方另提供
macOS (Apple Silicon) 与 Linux 版 rfp-cli，可从瑞萨官网下载后
把原生二进制放进本目录，上位机会自动优先选用。
