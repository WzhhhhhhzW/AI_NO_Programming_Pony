"""有界 C AST 执行器。只实现白名单 FSP 外设，不执行本机 C 程序。"""
import ast
import math
import operator
import re
import time
from pathlib import Path

from pycparser import c_ast as C, c_parser


class SimulationError(Exception):
    pass


class EndRun(Exception):
    pass


class Return(Exception):
    def __init__(self, value=0):
        self.value = value


class Break(Exception):
    pass


class Continue(Exception):
    pass


class Cell:
    def __init__(self, value=0, kind="int"):
        self.kind = kind
        self.set(value)

    def set(self, value):
        if isinstance(value, (int, float)):
            if self.kind in ("float", "double"):
                value = float(value)
            else:
                value = int(value)
                bits = {"uint8_t": 8, "u8": 8, "unsigned char": 8, "__uint8_t": 8,
                        "uint16_t": 16, "u16": 16, "uint32_t": 32, "u32": 32,
                        "uint64_t": 64, "unsigned int": 32}.get(self.kind)
                if bits:
                    value %= 1 << bits
        self.value = value


class Ref:
    def __init__(self, cell):
        self.cell = cell


OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul,
       "<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge,
       "==": operator.eq, "!=": operator.ne, "&": operator.and_, "|": operator.or_,
       "^": operator.xor, "<<": operator.lshift, ">>": operator.rshift}


def binary(op, a, b):
    if op == "/":
        return a / b if isinstance(a, float) or isinstance(b, float) else int(a / b)
    if op == "%":
        return a - int(a / b) * b
    if op == "&&":
        return int(bool(a) and bool(b))
    if op == "||":
        return int(bool(a) or bool(b))
    return OPS[op](a, b)


def strip_comments(text):
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: "\n" * m[0].count("\n") if m[0].startswith(("//", "/*")) else m[0], text)


STUB = """
typedef unsigned char uint8_t; typedef unsigned char __uint8_t;
typedef unsigned short uint16_t; typedef unsigned short __uint16_t;
typedef unsigned int uint32_t; typedef unsigned int __uint32_t;
typedef unsigned long long uint64_t; typedef int int32_t; typedef int int16_t;
typedef int bool; typedef int size_t; typedef int fsp_err_t;
typedef int bsp_warm_start_event_t; typedef int i2c_master_event_t;
typedef struct { int event; int data; } uart_callback_args_t;
typedef struct { int event; } i2c_master_callback_args_t;
typedef struct { uint32_t period_counts; } timer_info_t;
"""


def load_sources(root, overrides=None):
    root = Path(root)
    if not (root / "src").is_dir():
        raise SimulationError("工程缺少 src 目录，请打开 Dog 工程或使用内置实例。")
    texts = {}
    for folder in ("src", "ra_gen"):
        for path in (root / folder).rglob("*"):
            if path.suffix.lower() in (".c", ".h"):
                try:
                    texts[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    texts[path.relative_to(root).as_posix()] = path.read_text(encoding="gb18030")
    texts.update(overrides or {})
    return texts


class Preprocessor:
    def __init__(self, sources):
        self.sources = sources
        self.macros = {"FSP_CPP_HEADER": "", "FSP_CPP_FOOTER": "", "BSP_CMSE_NONSECURE_ENTRY": "",
                       "BSP_TZ_SECURE_BUILD": "0", "BSP_FEATURE_FLASH_LP_VERSION": "0",
                       "BSP_CFG_SDRAM_ENABLED": "0"}
        self.included = set()

    def expand(self, text):
        for _ in range(12):
            new = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\b[A-Za-z_]\w*\b',
                         lambda m: self.macros.get(m[0], m[0]), text)
            if new == text:
                return text
            text = new
        raise SimulationError("宏展开超过限制")

    def condition(self, expr):
        expr = re.sub(r"defined\s*\(?\s*(\w+)\s*\)?", lambda m: str(int(m[1] in self.macros)), expr)
        expr = self.expand(expr)
        expr = re.sub(r"\b[A-Za-z_]\w*\b", "0", expr)
        node = c_parser.CParser().parse("int value = " + expr + ";").ext[0].init
        def calc(n):
            if isinstance(n, C.Constant): return int(re.sub(r"[uUlL]+$", "", n.value), 0)
            if isinstance(n, C.BinaryOp): return binary(n.op, calc(n.left), calc(n.right))
            if isinstance(n, C.UnaryOp):
                return {"!": lambda x: not x, "-": operator.neg, "+": operator.pos, "~": operator.invert}[n.op](calc(n.expr))
            raise SimulationError("不支持的预处理表达式")
        return bool(calc(node))

    def process(self, name):
        if name in self.included: return ""
        self.included.add(name)
        text = strip_comments(self.sources[name])
        result = [f'#line 1 "{name}"']
        active = True
        levels = []
        for line_no, line in enumerate(text.splitlines(), 1):
            match = re.match(r"\s*#\s*(\w+)\s*(.*)", line)
            if not match:
                result.append(self.expand(line) if active else "")
                continue
            directive, arg = match.groups()
            if directive in ("if", "ifdef", "ifndef"):
                yes = (arg.strip() in self.macros) if directive != "if" else (self.condition(arg) if active else False)
                if directive == "ifndef": yes = not yes
                levels.append((active, yes)); active = active and yes
            elif directive == "else":
                parent, yes = levels[-1]; active = parent and not yes
            elif directive == "elif":
                parent, yes = levels[-1]; new = parent and not yes and self.condition(arg)
                levels[-1] = (parent, yes or new); active = new
            elif directive == "endif":
                active = levels.pop()[0]
            elif active and directive == "define":
                m = re.match(r"(\w+)(.*)", arg)
                if m and not m[2].startswith("("):
                    self.macros[m[1]] = m[2].strip() or "1"
            elif active and directive == "undef": self.macros.pop(arg.strip(), None)
            elif active and directive == "include":
                include = arg.strip('<>" ')
                # FSP 由虚拟外设实现；只预处理学生 src 中的本地头文件。
                candidates = [p for p in self.sources if p.startswith("src/") and Path(p).name.casefold() == include.casefold()]
                if candidates:
                    result.append(self.process(candidates[0]))
                    result.append(f'#line {line_no + 1} "{name}"')
                    continue
                if include not in ("hal_data.h", "stdlib.h", "stdint.h", "stdbool.h", "math.h", "assert.h", "stdio.h", "string.h"):
                    raise SimulationError(f"{name}:{line_no} 缺少可仿真的头文件 {include}")
            elif active and directive == "error": raise SimulationError(arg)
            result.append("")
        return "\n".join(result) + "\n"


class Runtime:
    def __init__(self, sources, seconds=12, commands=((1.0, "2"),), cancelled=lambda: False):
        self.sources = sources
        self.limit_ms = max(100, min(60000, seconds * 1000))
        self.cancelled = cancelled
        self.clock = 0.0
        self.steps = 0
        self.allocated = 0
        self.started = time.monotonic()
        self.functions = {}
        self.globals = {}
        self.stack = []
        self.boundaries = [0]
        self.trace = []
        self.warnings = []
        self.events = []
        self.commands = sorted((max(0, t * 1000), ord(ch)) for t, ch in commands)
        self.rx = None
        self.uart_open = False
        self.in_callback = False
        self.duties = {name: None for name in ("R_Front", "L_Front", "R_Rear", "L_Rear", "Tail")}
        self.oled = [0] * 1024
        self.oled_page = 0
        self.oled_col = 0
        self.oled_on = True
        self.oled_inverse = False
        self.oled_segment = 0xA1
        self.oled_scan = 0xC0
        self.timers = self.read_timers()
        self.parse()

    def warn(self, text):
        if text not in self.warnings: self.warnings.append(text)

    def read_timers(self):
        text = self.sources.get("ra_gen/hal_data.c", "")
        clocks = self.sources.get("ra_gen/bsp_clock_cfg.h", "")
        def number(pattern, default):
            m = re.search(pattern, clocks)
            return float(m[1]) if m else default
        xtal = number(r"BSP_CFG_XTAL_HZ\s+\((\d+)", 12000000)
        pll_div = number(r"BSP_CFG_PLL_DIV.*?PLL_DIV_(\d+)", 2)
        pll_mul = number(r"BSP_CFG_PLL_MUL\s+BSP_CLOCKS_PLL_MUL\((\d+)", 30)
        peripheral_div = number(r"BSP_CFG_PCLKD_DIV.*?DIV_(\d+)", 2)
        hz = xtal / pll_div * pll_mul / peripheral_div
        if "BSP_CLOCKS_SOURCE_CLOCK_PLL" not in clocks:
            raise SimulationError("当前仅支持 Dog 的主晶振→PLL→PCLKD 时钟配置，不能可靠换算此工程的 PWM。")
        out = {}
        for m in re.finditer(r"const timer_cfg_t\s+(\w+)_cfg\s*=\s*\{(.*?)\};", text, re.S):
            body = strip_comments(m[2])
            count = re.search(r"\.period_counts\s*=\s*(?:\([^)]*\)\s*)?(0x[\da-fA-F]+|\d+)", body)
            div = re.search(r"\.source_div\s*=\s*(?:\([^)]*\)\s*)?(\d+)", body)
            if not count or not div: raise SimulationError("无法读取定时器配置：" + m[1])
            counts = int(count[1], 0)
            duty = re.search(r"\.duty_cycle_counts\s*=\s*(0x[\da-fA-F]+|\d+)", body)
            extend = re.search(r"const gpt_extended_cfg_t\s+"+re.escape(m[1])+r"_extend\s*=\s*(.*?);",text,re.S)
            pins = {}
            for pin,number_ in (("a",0),("b",1)):
                flag = re.search(r"\.gtioc"+pin+r"\s*=\s*\{\s*\.output_enabled\s*=\s*(true|false)",extend[1] if extend else "")
                pins[number_] = bool(flag and flag[1]=="true")
            out[m[1]] = {"counts": counts, "period_ms": counts * 2 ** int(div[1]) / hz * 1000,
                         "initial_counts": int(duty[1],0) if duty else counts//2,
                         "pins":pins,"compare":{},"open": False, "start": False}
        if not out: raise SimulationError("未找到 ra_gen/hal_data.c 的 GPT 配置，请先生成 FSP 配置。")
        return out

    def parse(self):
        pre = Preprocessor(self.sources)
        code = STUB + "\n" + "\n".join(pre.process(name) for name in sorted(self.sources) if name.startswith("src/") and name.endswith(".c"))
        try: tree = c_parser.CParser().parse(code)
        except Exception as exc: raise SimulationError("C 语法解析失败：" + str(exc)) from exc
        constants = {"NULL": 0, "true": 1, "false": 0, "FSP_SUCCESS": 0,
                     "BSP_DELAY_UNITS_MILLISECONDS": 1, "BSP_DELAY_UNITS_MICROSECONDS": 0,
                     "BSP_DELAY_UNITS_SECONDS": 2, "GPT_IO_PIN_GTIOCA": 0, "GPT_IO_PIN_GTIOCB": 1,
                     "UART_EVENT_RX_COMPLETE": 1, "UART_EVENT_RX_CHAR": 2,
                     "I2C_MASTER_EVENT_TX_COMPLETE": 1, "I2C_MASTER_EVENT_ABORTED": 0,
                     "I2C_MASTER_ADDR_MODE_7BIT": 0}
        for key, value in constants.items(): self.globals[key] = Cell(value)
        for name in [*self.timers, "OLED", "Blue_Tooth"]:
            for suffix in ("_ctrl", "_cfg"):
                self.globals[name + suffix] = Cell(name)
        for node in tree.ext:
            if isinstance(node, C.FuncDef): self.functions[node.decl.name] = node
        for node in tree.ext:
            if isinstance(node, C.Decl) and not isinstance(node.type, C.FuncDecl) and "extern" not in node.storage:
                self.declare(node, self.globals)

    def tick(self, node):
        self.steps += 1
        if self.steps % 1024 == 0:
            if self.cancelled(): raise EndRun()
            if self.steps > 5000000 or time.monotonic() - self.started > 25:
                raise SimulationError("执行超出限制：检查死循环，或缩短仿真时长。")
        self.coord = str(getattr(node, "coord", "") or "")

    def lookup(self, name):
        for scope in reversed(self.stack[self.boundaries[-1]:]):
            if name in scope: return scope[name]
        if name in self.globals: return self.globals[name]
        raise SimulationError("未定义变量：" + name)

    def kind(self, typ):
        if isinstance(typ, C.TypeDecl): return self.kind(typ.type)
        if isinstance(typ, C.IdentifierType): return " ".join(typ.names)
        return "int"

    def make_value(self, typ, init):
        if isinstance(typ, C.ArrayDecl):
            exprs = init.exprs if isinstance(init, C.InitList) else []
            size = int(self.eval(typ.dim)) if typ.dim else len(exprs)
            if size < 0 or size > 100000: raise SimulationError("数组长度超过仿真限制")
            self.allocated += size
            if self.allocated > 300000:raise SimulationError("数组分配超过仿真内存限制")
            return [Cell(self.make_value(typ.type, exprs[i] if i < len(exprs) else None), self.kind(typ.type)) for i in range(size)]
        if init is not None: return self.eval(init)
        if self.kind(typ) == "timer_info_t": return {"period_counts": Cell(0, "uint32_t")}
        return 0

    def declare(self, node, scope=None):
        if not node.name or isinstance(node.type, C.FuncDecl): return
        scope = scope if scope is not None else self.stack[-1]
        scope[node.name] = Cell(self.make_value(node.type, node.init), self.kind(node.type))

    def ref(self, node):
        if isinstance(node, C.ID): return self.lookup(node.name)
        if isinstance(node, C.ArrayRef):
            array, idx = self.eval(node.name), int(self.eval(node.subscript))
            if isinstance(array, Ref): array = [array.cell]
            if idx < 0 or idx >= len(array):
                self.warn(f"{node.coord} 数组越界 [{idx}]；仿真已隔离该访问，实机可能损坏内存。")
                return Cell()
            return array[idx]
        if isinstance(node, C.StructRef):
            value = self.eval(node.name)
            if isinstance(value, Ref): value = value.cell.value
            return value[node.field.name]
        if isinstance(node, C.UnaryOp) and node.op == "*":
            pointer = self.eval(node.expr)
            if isinstance(pointer, list):
                if not pointer: raise SimulationError('指针超出数组范围')
                return pointer[0]
            return pointer.cell
        raise SimulationError("不支持的左值：" + type(node).__name__)

    def eval(self, node):
        if node is None: return 0
        self.tick(node)
        if isinstance(node, C.Constant):
            if node.type == "string": return [Cell(ord(c), "uint8_t") for c in ast.literal_eval(node.value) + "\0"]
            if node.type == "char": return ord(ast.literal_eval(node.value))
            value = re.sub(r"[uUlLfF]+$", "", node.value) if not node.value.lower().startswith("0x") else re.sub(r"[uUlL]+$", "", node.value)
            if node.type in ("float", "double"): return float(value)
            return int(value, 8 if len(value) > 1 and value.startswith("0") and not value.lower().startswith("0x") else 0)
        if isinstance(node, (C.ID, C.ArrayRef, C.StructRef)): return self.ref(node).value
        if isinstance(node, C.BinaryOp):
            a = self.eval(node.left)
            if node.op == "&&" and not a: return 0
            if node.op == "||" and a: return 1
            return binary(node.op, a, self.eval(node.right))
        if isinstance(node, C.UnaryOp):
            op = node.op
            if op == "&": return Ref(self.ref(node.expr))
            if op == "*": return self.ref(node).value
            if op in ("p++", "p--", "++", "--"):
                cell = self.ref(node.expr); old = cell.value
                if isinstance(old, list):
                    if '-' in op: raise SimulationError('暂不支持数组指针向前递减')
                    if not old: raise SimulationError('指针超出数组范围')
                    cell.set(old[1:])
                else:
                    cell.set(old + (1 if "+" in op else -1))
                return old if op.startswith("p") else cell.value
            value = self.eval(node.expr)
            if op == "sizeof": return len(value) if isinstance(value, list) else 4
            return {"!": lambda x: int(not x), "~": operator.invert, "-": operator.neg, "+": operator.pos}[op](value)
        if isinstance(node, C.Cast):
            return Cell(self.eval(node.expr), self.kind(node.to_type.type)).value
        if isinstance(node, C.Assignment):
            cell = self.ref(node.lvalue); value = self.eval(node.rvalue)
            cell.set(value if node.op == "=" else binary(node.op[:-1], cell.value, value)); return cell.value
        if isinstance(node, C.TernaryOp): return self.eval(node.iftrue if self.eval(node.cond) else node.iffalse)
        if isinstance(node, C.FuncCall):
            if not isinstance(node.name, C.ID): raise SimulationError("暂不支持函数指针调用")
            return self.call(node.name.name, [self.eval(a) for a in (node.args.exprs if node.args else [])], str(node.coord))
        if isinstance(node, C.ExprList):
            result = 0
            for item in node.exprs: result = self.eval(item)
            return result
        raise SimulationError("暂不支持 C 表达式：" + type(node).__name__)

    def execute(self, node):
        if node is None: return
        self.tick(node)
        if isinstance(node, C.Compound):
            self.stack.append({})
            try:
                for item in node.block_items or []: self.execute(item)
            finally: self.stack.pop()
        elif isinstance(node, C.Decl): self.declare(node)
        elif isinstance(node, C.DeclList):
            for decl in node.decls: self.declare(decl)
        elif isinstance(node, C.If): self.execute(node.iftrue if self.eval(node.cond) else node.iffalse)
        elif isinstance(node, (C.For, C.While, C.DoWhile)):
            self.stack.append({})
            try:
                if isinstance(node, C.For): self.execute(node.init)
                first = True
                while (first and isinstance(node, C.DoWhile)) or node.cond is None or self.eval(node.cond):
                    first = False
                    try: self.execute(node.stmt)
                    except Continue: pass
                    except Break: break
                    if isinstance(node, C.For): self.eval(node.next)
            finally: self.stack.pop()
        elif isinstance(node, C.Switch):
            value = self.eval(node.cond); cases = node.stmt.block_items or []
            start = next((i for i,c in enumerate(cases) if isinstance(c,C.Case) and self.eval(c.expr)==value), None)
            if start is None: start = next((i for i,c in enumerate(cases) if isinstance(c,C.Default)), len(cases))
            try:
                for case in cases[start:]:
                    for stmt in case.stmts or []: self.execute(stmt)
            except Break: pass
        elif isinstance(node, C.Return): raise Return(self.eval(node.expr))
        elif isinstance(node, C.Break): raise Break()
        elif isinstance(node, C.Continue): raise Continue()
        elif isinstance(node, (C.EmptyStatement, C.Typedef)): pass
        else: self.eval(node)

    def call(self, name, args, coord=""):
        result, handled = self.peripheral(name, args, coord)
        if handled: return result
        fn = self.functions.get(name)
        if fn is None: raise SimulationError(f"{coord} 尚未支持此函数/外设：{name}，未生成假动作。")
        if len(self.stack) > 80: raise SimulationError("调用层级超过限制")
        params = fn.decl.type.args.params if fn.decl.type.args else []
        scope = {}
        for param, value in zip(params, args):
            if getattr(param, "name", None): scope[param.name] = Cell(value, self.kind(param.type))
        self.boundaries.append(len(self.stack))
        self.stack.append(scope)
        try: self.execute(fn.body)
        except Return as ret: return ret.value
        finally:
            self.stack.pop()
            self.boundaries.pop()
        return 0

    def snapshot(self, coord=""):
        if len(self.trace)>5000 or len(self.events)>20000:
            raise SimulationError("输出事件过密，请缩短仿真时长，或检查循环中是否缺少合适的延时。")
        frame = {"t": round(self.clock, 3), "duty": dict(self.duties), "oled": list(self.oled),
                 "oled_on": self.oled_on, "inverse": self.oled_inverse, "source": coord,
                 "flip_x": self.oled_segment == 0xA0, "flip_y": self.oled_scan == 0xC8}
        if self.trace and self.trace[-1]["t"] == frame["t"]: self.trace[-1] = frame
        else: self.trace.append(frame)

    def advance(self, amount):
        if amount < 0: raise SimulationError("延时不能为负数")
        end = min(self.clock + amount, self.limit_ms)
        while self.commands and self.commands[0][0] <= end and not self.in_callback:
            when, char = self.commands.pop(0)
            self.clock = max(self.clock, when)
            if self.rx is not None and self.uart_open:
                dest = self.rx; self.rx = None
                (dest[0] if isinstance(dest, list) else dest.cell).set(char)
                self.events.append({"t": self.clock, "text": f"UART 收到字符 {chr(char)}"})
                self.in_callback = True
                try: self.call("Blue_Tooth_Callback", [Ref(Cell({"event": Cell(1), "data": Cell(char)}))])
                finally: self.in_callback = False
            else: self.warn(f"{when/1000:g}s 的串口字符 {chr(char)} 未接收：串口未打开或未重新调用 Read。")
        self.clock = end
        if self.clock >= self.limit_ms: raise EndRun()

    def peripheral(self, name, args, coord):
        value = lambda a: a.cell.value if isinstance(a, Ref) else a
        if name == "R_BSP_SoftwareDelay":
            unit = args[1]; self.advance(args[0] * ({0: .001, 1: 1, 2: 1000}[unit])); return 0, True
        if name in ("R_GPT_Open", "R_GPT_Start", "R_GPT_Stop", "R_GPT_InfoGet", "R_GPT_DutyCycleSet", "R_GPT_PeriodSet"):
            timer_name = value(args[0]); timer = self.timers[timer_name]
            if name == "R_GPT_Open": timer["open"] = True
            elif name == "R_GPT_Start":
                timer["start"] = True
                self.peripheral("R_GPT_DutyCycleSet",[args[0],timer["initial_counts"],0],coord)
                if timer_name == "Front_Foot":
                    self.peripheral("R_GPT_DutyCycleSet",[args[0],timer["initial_counts"],1],coord)
            elif name == "R_GPT_Stop":
                timer["start"] = False
                affected = {"Front_Foot":["R_Front","L_Front"],"R_Rear_Foot":["R_Rear"],"L_Rear_Foot":["L_Rear"],"Tail":["Tail"]}.get(timer_name,[])
                for joint in affected: self.duties[joint]=None
                self.snapshot(coord)
            elif name == "R_GPT_InfoGet": value(args[1])["period_counts"].set(timer["counts"])
            elif name == "R_GPT_PeriodSet":
                if args[1]<=0:raise SimulationError("GPT 周期计数必须大于 0")
                timer["period_ms"] *= args[1] / timer["counts"]; timer["counts"] = args[1]
                for pin,counts in list(timer["compare"].items()):
                    self.peripheral("R_GPT_DutyCycleSet",[args[0],counts,pin],coord)
            else:
                if not timer["open"] or not timer["start"]:
                    self.warn(f"{timer_name} 尚未 Open/Start，PWM 输出未生效。")
                    return 1, True
                if not timer["pins"].get(args[2],False):
                    self.warn(f"{timer_name} 的 GTIOC{'A' if args[2]==0 else 'B'} 输出未启用。")
                    return 1, True
                timer["compare"][args[2]]=args[1]
                joint = {("Front_Foot", 1): "R_Front", ("Front_Foot", 0): "L_Front",
                         ("R_Rear_Foot", 0): "R_Rear", ("L_Rear_Foot", 0): "L_Rear", ("Tail", 0): "Tail"}.get((timer_name, args[2]))
                if joint is None: raise SimulationError("GPT 输出未绑定到模型关节：" + timer_name)
                duty = 100 * (1 - args[1] / timer["counts"])
                pulse = timer["period_ms"] * duty / 100
                if not .5 <= pulse <= 2.5:
                    response = "尾舵机保持上一目标角度（上电为装配零位）" if joint == "Tail" else "实时物理模式不提供此路驱动力"
                    self.warn(f"{joint} 脉宽 {pulse:.2f}ms 超出 0.5–2.5ms 校准范围；{response}，请检查 PWM 参数。")
                self.duties[joint] = {"percent": round(duty, 5), "pulse_ms": round(pulse, 5)}
                self.events.append({"t": self.clock, "text": f"{joint} = {duty:.2f}% / {pulse:.3f}ms", "source": coord})
                self.snapshot(coord)
            return 0, True
        if name == "R_SCI_UART_Open": self.uart_open = True; return 0, True
        if name == "R_SCI_UART_Read": self.rx = args[1]; return 0, True
        if name == "R_IIC_MASTER_Write":
            data = args[1]; count = args[2]
            vals = [c.value for c in data[:count]] if isinstance(data, list) else [value(data)]
            if vals and vals[0] == 0x00:
                for cmd in vals[1:]:
                    if 0xB0 <= cmd <= 0xB7: self.oled_page = cmd - 0xB0
                    elif 0 <= cmd <= 0x0F: self.oled_col = (self.oled_col & 0xF0) | cmd
                    elif 0x10 <= cmd <= 0x1F: self.oled_col = (self.oled_col & 15) | ((cmd & 15) << 4)
                    elif cmd == 0xAE: self.oled_on = False
                    elif cmd == 0xAF: self.oled_on = True
                    elif cmd == 0xA6: self.oled_inverse = False
                    elif cmd == 0xA7: self.oled_inverse = True
                    elif cmd in (0xA0, 0xA1): self.oled_segment = cmd
                    elif cmd in (0xC0, 0xC8): self.oled_scan = cmd
            elif vals and vals[0] == 0x40:
                for byte in vals[1:]:
                    if self.oled_col < 128: self.oled[self.oled_page * 128 + self.oled_col] = int(byte) & 255
                    self.oled_col += 1
                self.snapshot(coord)
            if "OLED_callback" in self.functions:
                self.call("OLED_callback", [Ref(Cell({"event": Cell(1)}))])
            return 0, True
        if name in ("R_IIC_MASTER_Open", "R_IIC_MASTER_SlaveAddressSet"): return 0, True
        if name == "assert":
            if not args[0]: raise SimulationError(f"{coord} assert 失败")
            return 0, True
        if name in ("abs", "fabs", "sin", "cos", "sqrt", "pow"):
            return ({"abs": abs, "fabs": abs, "sin": math.sin, "cos": math.cos, "sqrt": math.sqrt, "pow": pow}[name](*args)), True
        return 0, False

    def run(self):
        self.snapshot()
        try: self.call("hal_entry", [])
        except EndRun: pass
        except SimulationError: raise
        except Exception as exc: raise SimulationError(f"{getattr(self, 'coord', '')} 执行失败：{type(exc).__name__}: {exc}") from exc
        self.snapshot()
        return {"frames": self.trace, "events": self.events, "warnings": self.warnings,
                "duration": self.clock, "steps": self.steps, "timers": self.timers}
