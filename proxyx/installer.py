"""Proxyx — install-service: gateway jalan otomatis saat mesin nyala.

HANYA MEMBUAT FILE, tidak mengubah sistem: pengguna sendiri yang
menyalakan servicenya (perlu sudo/admin). Repo asli tidak punya ini —
gateway-nya cuma jalan selama terminal dibuka.
"""
from __future__ import annotations

import os


def systemd_unit(python_bin: str, workdir: str, port: int) -> str:
    return f"""[Unit]
Description=Proxyx Gateway (rotating proxy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={workdir}
ExecStart={python_bin} -m proxyx gateway --port {port}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def windows_task_xml(python_bin: str, workdir: str, port: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Actions><Exec>
    <Command>{python_bin}</Command>
    <Arguments>-m proxyx gateway --port {port}</Arguments>
    <WorkingDirectory>{workdir}</WorkingDirectory>
  </Exec></Actions>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries></Settings>
</Task>
"""


def windows_install_bat(workdir: str) -> str:
    return (f"@echo off\r\n"
            "REM Jalankan sebagai Administrator (klik kanan > Run as administrator)\r\n"
            f'schtasks /create /tn "Proxyx Gateway" /xml "{workdir}\\proxyx-task.xml" /f\r\n'
            "echo Selesai. Gateway Proxyx akan jalan tiap kali kamu login Windows.\r\n"
            "pause\r\n")


def generate(out_dir: str, python_bin: str, workdir: str, port: int) -> dict[str, str]:
    """Tulis 3 file ke out_dir. Kembalikan {nama: path}."""
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "proxyx.service": systemd_unit(python_bin, workdir, port),
        "proxyx-task.xml": windows_task_xml(python_bin, workdir, port),
        "install-service.bat": windows_install_bat(workdir),
    }
    paths = {}
    for name, content in files.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        paths[name] = path
    return paths
