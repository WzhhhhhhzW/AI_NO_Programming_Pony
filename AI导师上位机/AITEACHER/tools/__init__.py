"""让 tools/ 下的脚本能被 import（project_manager 要用 fix_include_case）。

同时也是给 PyInstaller 的信号：有了这个文件，
``from tools.fix_include_case import ...`` 会被依赖分析跟进去一起打包。
"""
