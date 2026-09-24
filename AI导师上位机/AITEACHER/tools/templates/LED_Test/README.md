# LED 点灯工程 — 给 AI 助手看的说明

最小的 RA 工程：用 GPIO 让板载 LED 闪烁。整个工程只有一个 `src/hal_entry.c`。

---

## 硬件外设

只有 **IOPORT（GPIO）**。**没有定时器、没有 I2C、没有串口** ——
学生要 PWM/舵机、OLED 屏、蓝牙，得先去 RASC 里加对应的模块，
改 C 代码是没用的（会编不过或者链接报 undefined）。

已配好的引脚：

| 引脚 | 用途 |
|---|---|
| P111 | 板载 LED，配成输出 |
| P108 / P300 | SWD 调试口，别动 |

---

## 改哪里

`hal_entry()` 里就那一个循环：

```c
while (1) {
    R_IOPORT_PinWrite(&IOPORT_CFG_CTRL, BSP_IO_PORT_01_PIN_11, BSP_IO_LEVEL_HIGH);
    R_BSP_SoftwareDelay(500, BSP_DELAY_UNITS_MILLISECONDS);   // ← 亮多久
    R_IOPORT_PinWrite(&IOPORT_CFG_CTRL, BSP_IO_PORT_01_PIN_11, BSP_IO_LEVEL_LOW);
    R_BSP_SoftwareDelay(500, BSP_DELAY_UNITS_MILLISECONDS);   // ← 灭多久
}
```

- "闪快一点 / 慢一点"：改两个延时。
- "亮的时间长一点"：只改第一个。
- 单位可以换成 `BSP_DELAY_UNITS_MICROSECONDS` / `_SECONDS`。
- **想做呼吸灯（渐亮渐暗）做不到** —— 那需要 PWM，这个工程没有定时器，
  得让学生先去 RASC 加一个 GPT。
