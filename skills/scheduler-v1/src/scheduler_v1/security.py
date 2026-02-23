from __future__ import annotations

import ipaddress
import socket
from functools import lru_cache
from typing import Union
from urllib.parse import urlsplit


_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
}


def is_safe_public_http_url(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False

    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        return False
    return is_safe_public_host(host)


@lru_cache(maxsize=2048)
def is_safe_public_host(host: str) -> bool:
    if host in _BLOCKED_HOSTS:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False

    try:
        ip = ipaddress.ip_address(host)
        return _is_public_ip(ip)
    except ValueError:
        pass

    try:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        # If DNS lookup is temporarily unavailable, keep literal-IP safety checks
        # while allowing regular hostnames.
        return True

    if not records:
        return False

    for record in records:
        resolved_ip = record[4][0]
        try:
            ip = ipaddress.ip_address(resolved_ip)
        except ValueError:
            return False
        if not _is_public_ip(ip):
            return False

    return True


def _is_public_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
