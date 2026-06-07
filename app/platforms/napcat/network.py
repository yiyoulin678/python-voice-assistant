from __future__ import annotations

import socket


def is_virtual_adapter_ip(host: str) -> bool:
    """过滤 WSL / Hyper-V / Docker 等虚拟网卡地址，避免 NapCat 连不上。"""
    text = host.strip().lower()
    if not text or is_loopback_host(text):
        return False
    if text.startswith("169.254."):
        return True
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return False
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    return False


def can_connect_local_service(host: str, port: int, *, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def normalize_connect_host(host: str, *, port: int) -> str:
    primary = primary_local_ipv4()
    candidate = host.strip()
    if candidate and not is_virtual_adapter_ip(candidate):
        if is_loopback_host(candidate):
            return candidate
        if primary and candidate == primary:
            return candidate
        if can_connect_local_service(candidate, port):
            return candidate
    if primary and not is_virtual_adapter_ip(primary):
        return primary
    return "127.0.0.1"


def is_unspecified_bind_host(host: str) -> bool:
    return host.strip().lower() in {"0.0.0.0", "::", "::0", ""}


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in {"127.0.0.1", "localhost", "::1"}


def primary_local_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def suggested_connect_hosts() -> list[str]:
    hosts: list[str] = []
    primary = primary_local_ipv4()
    if primary and not is_virtual_adapter_ip(primary):
        hosts.append(primary)
    if "127.0.0.1" not in hosts:
        hosts.append("127.0.0.1")
    return hosts
