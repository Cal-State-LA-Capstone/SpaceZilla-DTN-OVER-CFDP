"""
SpaceZilla Receiver Setup Script
---------------------------------
Run this on the RECEIVER machine before starting ION.
Detects your OS and configures the firewall for incoming CFDP transfers (UDP 1114).

Usage:
    python3 receiver_setup.py

Supported: Linux (native), macOS, WSL2
"""

import os
import platform
import socket
import subprocess
import sys


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _get_wsl2_ip() -> str | None:
    try:
        result = subprocess.run(
            ["ip", "addr", "show", "eth0"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet ") and "/" in line:
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return None


def _get_lan_ip() -> str | None:
    try:
        with socket.create_connection(("8.8.8.8", 80), timeout=2) as s:
            return s.getsockname()[0]
    except OSError:
        return None


def _run(cmd: list[str], check: bool = True) -> bool:
    try:
        subprocess.run(cmd, check=check)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_linux() -> None:
    print("[Linux] Opening UDP port 1114 on firewall...")

    if _run(["which", "ufw"], check=False):
        if _run(["sudo", "ufw", "allow", "1114/udp"]):
            print("  ufw: port 1114/udp allowed.")
            return

    if _run(["which", "firewall-cmd"], check=False):
        _run(["sudo", "firewall-cmd", "--permanent", "--add-port=1114/udp"])
        _run(["sudo", "firewall-cmd", "--reload"])
        print("  firewalld: port 1114/udp allowed.")
        return

    if _run(["which", "iptables"], check=False):
        if _run(["sudo", "iptables", "-A", "INPUT", "-p", "udp", "--dport", "1114", "-j", "ACCEPT"]):
            print("  iptables: port 1114/udp allowed.")
            return

    print("  Could not detect firewall manager. Manually open UDP port 1114.")


def setup_macos() -> None:
    print("[macOS] On macOS, ION binds directly to the port.")
    print("  If transfers fail, go to System Settings > Network > Firewall")
    print("  and allow incoming UDP connections on port 1114.")


def setup_wsl2() -> None:
    wsl_ip = _get_wsl2_ip()
    lan_ip = _get_lan_ip()

    print("[WSL2] Detected WSL2 environment.")
    print()

    if wsl_ip:
        print(f"  Your WSL2 internal IP: {wsl_ip}")
    else:
        print("  Could not detect WSL2 IP. Run: ip addr show eth0 | grep 'inet '")
        wsl_ip = "<WSL2_IP>"

    print()
    print("  WSL2 does not receive UDP from the network automatically.")
    print("  You must run the following in Windows PowerShell (leave it open while transferring):")
    print()
    print("  ---- COPY THIS INTO WINDOWS POWERSHELL ----")
    print(f"""python -c "
import socket
src = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
src.bind(('0.0.0.0', 1114))
print('Forwarding UDP 1114 -> {wsl_ip}:1114')
while True:
    data, addr = src.recvfrom(65535)
    fwd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fwd.sendto(data, ('{wsl_ip}', 1114))
    fwd.close()
" """)
    print("  -------------------------------------------")
    print()
    print("  Also run this in PowerShell as Administrator (one time only):")
    print('  netsh advfirewall firewall add rule name="ION LTP 1114" dir=in action=allow protocol=UDP localport=1114')


def print_router_instructions(lan_ip: str | None) -> None:
    ip_str = lan_ip or "<your LAN IP>"
    print()
    print("=" * 60)
    print("ROUTER PORT FORWARDING (required for WAN transfers)")
    print("=" * 60)
    print(f"  Forward UDP port 1114 -> {ip_str} on your router.")
    print("  Steps vary by router — log into your router admin page")
    print("  (usually 192.168.1.1 or 192.168.0.1) and look for")
    print("  'Port Forwarding' or 'Virtual Server'.")
    print()
    print("  Setting:")
    print("    Protocol : UDP")
    print("    External port : 1114")
    print(f"    Internal IP   : {ip_str}")
    print("    Internal port : 1114")
    print()
    print("  NOTE: LAN transfers do not need port forwarding.")
    print("=" * 60)


def main() -> None:
    print("SpaceZilla Receiver Setup")
    print("-" * 40)

    lan_ip = _get_lan_ip()
    if lan_ip:
        print(f"Detected LAN IP: {lan_ip}")
    print()

    if _is_wsl():
        wsl_ip = _get_wsl2_ip()
        setup_wsl2()
        print_router_instructions(lan_ip or wsl_ip)
    elif platform.system() == "Darwin":
        setup_macos()
        print_router_instructions(lan_ip)
    elif platform.system() == "Linux":
        setup_linux()
        print_router_instructions(lan_ip)
    else:
        print(f"Unsupported OS: {platform.system()}")
        print("Manually open UDP port 1114 on your firewall.")
        print_router_instructions(lan_ip)

    print()
    print("Once setup is complete, start ION:")
    print("  mkdir -p ~/received_files && cd ~/received_files")
    print("  ionstart -I receiver.rc")
    print()
    print("Received files will appear in ~/received_files/")


if __name__ == "__main__":
    main()
