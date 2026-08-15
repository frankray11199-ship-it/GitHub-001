# -*- coding: utf-8 -*-
"""电脑体检：识别系统、硬件与相关软件，输出一份可直接粘贴回对话的报告。

只用 Python 标准库，不需要预装任何东西。

用法:
    python sysinfo.py
"""

import os
import platform
import shutil
import subprocess
import sys

if os.name == "nt":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

HERE = os.path.dirname(os.path.abspath(__file__))
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"


def sh(cmd, timeout=15):
    """跑一条命令，取首个非空输出行；失败返回 None。"""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             shell=isinstance(cmd, str))
        for line in (out.stdout or "").splitlines():
            if line.strip():
                return line.strip()
    except Exception:
        pass
    return None


def ver(exe, args=("--version",)):
    p = shutil.which(exe)
    if not p:
        return None
    return sh([p, *args]) or p


def human(n):
    if not n:
        return "未知"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f PB" % n


# ------------------------------------------------------------------ 硬件
def cpu_name():
    if IS_WIN:
        return (sh('wmic cpu get name /value')
                or sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"')
                or platform.processor())
    if IS_MAC:
        return sh(["sysctl", "-n", "machdep.cpu.brand_string"])
    try:
        for line in open("/proc/cpuinfo", encoding="utf-8", errors="ignore"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "未知"


def ram_bytes():
    if IS_WIN:
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys
        except Exception:
            return None
    if IS_MAC:
        v = sh(["sysctl", "-n", "hw.memsize"])
        return int(v) if v and v.isdigit() else None
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                return int(line.split()[1]) * 1024
    except Exception:
        return None


def gpu_name():
    if IS_WIN:
        return (sh('powershell -NoProfile -Command '
                   '"(Get-CimInstance Win32_VideoController).Name -join \', \'"')
                or sh("wmic path win32_VideoController get name"))
    if IS_MAC:
        return sh("system_profiler SPDisplaysDataType | grep 'Chipset Model'")
    return sh("lspci | grep -i 'vga\\|3d\\|display'") or "未知"


def cpu_counts():
    logical = os.cpu_count() or 0
    physical = None
    try:
        if IS_WIN:
            v = sh('powershell -NoProfile -Command '
                   '"(Get-CimInstance Win32_Processor).NumberOfCores"')
            physical = int(v) if v and v.strip().isdigit() else None
        elif IS_MAC:
            v = sh(["sysctl", "-n", "hw.physicalcpu"])
            physical = int(v) if v and v.isdigit() else None
        else:
            v = sh("lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l")
            physical = int(v) if v and v.isdigit() else None
    except Exception:
        pass
    return physical, logical


# ------------------------------------------------------------------ 报告
def main():
    print("=" * 64)
    print("电脑体检报告（把这一整段复制粘贴回对话即可）")
    print("=" * 64)

    print("\n【系统】")
    print("  操作系统   :", platform.platform())
    if IS_WIN:
        print("  Windows 版 :", sh("ver") or platform.version())
    print("  架构       :", platform.machine())
    print("  主机名     :", platform.node())

    print("\n【硬件】")
    phys, logi = cpu_counts()
    print("  CPU        :", cpu_name())
    print("  核心/线程  : %s 核 / %d 线程" % (phys or "未知", logi))
    print("  内存       :", human(ram_bytes()))
    print("  显卡       :", gpu_name())
    try:
        u = shutil.disk_usage(HERE)
        print("  磁盘(项目) : 共 %s，可用 %s" % (human(u.total), human(u.free)))
    except Exception:
        pass

    print("\n【出片必需】")
    print("  Python     : %s  (%s)" % (platform.python_version(), sys.executable))
    print("  pip        :", ver("pip") or ver("pip3") or "未找到（可用 python -m pip）")
    print("  ffmpeg     :", ver("ffmpeg", ("-version",)) or "未找到（run.py 会自动装 imageio-ffmpeg 顶上）")
    for mod, label in (("PIL", "pillow"), ("numpy", "numpy"),
                       ("sherpa_onnx", "sherpa-onnx")):
        try:
            m = __import__(mod)
            print("  %-11s: 已安装 %s" % (label, getattr(m, "__version__", "")))
        except ImportError:
            print("  %-11s: 未安装（run.py 会自动装）" % label)

    print("\n【中文字体】")
    try:
        sys.path.insert(0, HERE)
        import platform_support
        (rp, ri), (bp, bi) = platform_support.find_cjk_fonts()
        print("  常规       : %s (index=%d)" % (rp, ri))
        print("  粗体       : %s (index=%d)" % (bp, bi))
    except SystemExit as e:
        print("  探测失败   :", e)
    except Exception as e:
        print("  探测失败   : %s（请在项目目录下运行本脚本）" % e)

    print("\n【远程控制相关】")
    print("  git        :", ver("git") or "未找到")
    print("  node       :", ver("node") or "未找到")
    print("  claude CLI :", ver("claude") or "未找到（需装 Claude Code 才能手机远程控制）")

    print("\n【出片耗时预估】")
    if logi:
        # 实测：8 核云容器上 melo 合成约 1x 实时、渲染约 75 帧/秒
        synth = 534 / max(0.35, min(1.6, logi / 8.0))
        render = 13344 / max(25.0, 75.0 * min(1.0, logi / 8.0))
        print("  语音合成   : 约 %.0f 分钟（melo；换 --tts matcha 约快 3 倍）" % (synth / 60))
        print("  渲染+编码  : 约 %.0f 分钟" % (render / 60))
        print("  合计       : 约 %.0f 分钟（首次另加下载模型 167MB）" % ((synth + render) / 60))

    print("\n" + "=" * 64)


if __name__ == "__main__":
    main()
