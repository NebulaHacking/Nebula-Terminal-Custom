"""Sources d'infos système pour la bannière de Nebula (datasources pures).

Extrait des lignes 484-545 de l'ancien main.py. Chaque fonction retourne une
string ; l'affichage est assemblé dans terminal/banner.py.
"""
import os
import platform
import shutil
import subprocess


def get_uptime() -> str:
    if platform.system() == "Windows":
        try:
            import ctypes
            lib = ctypes.windll.kernel32
            millis = lib.GetTickCount64()
            seconds = millis // 1000
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        except Exception:
            return "Unknown"
    try:
        uptime_seconds = float(os.popen("cat /proc/uptime").read().split()[0])
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{hours} hours, {minutes} minutes"
    except Exception:
        return "Unknown"


def get_packages() -> str:
    if platform.system() == "Linux":
        try:
            if shutil.which("dpkg"):
                return subprocess.check_output("dpkg -l | wc -l", shell=True).decode().strip()
            elif shutil.which("rpm"):
                return subprocess.check_output("rpm -qa | wc -l", shell=True).decode().strip()
            return "Unknown"
        except Exception:
            return "Unknown"
    return "N/A"


def get_resolution() -> str:
    try:
        if platform.system() == "Windows":
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            return f"{width}x{height}"
        res = subprocess.check_output("xdpyinfo | grep dimensions", shell=True).decode()
        return res.split()[1]
    except Exception:
        return "Unknown"


def get_gpu() -> str:
    try:
        if platform.system() == "Windows":
            # wmic est retiré des Windows 11 récents → CIM via PowerShell.
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController).Name"],
                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
            ).decode(errors="replace")
            return ", ".join(l.strip() for l in out.splitlines() if l.strip()) or "Unknown"
        gpu = subprocess.check_output("lspci | grep -i 'vga'", shell=True).decode().strip()
        return gpu
    except Exception:
        return "Unknown"