"""Validate DNS results and pin connections to a validated public IP."""

import asyncio
import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit, urlunsplit

from research_agent.tools.base import ToolError


def public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped or ip.sixtofour or ip.teredo:
            return False
    return ip.is_global and not ip.is_multicast


def validate_url(url: str) -> SplitResult:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme not in {"http", "https"}
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 80, 443}
            or "\\" in url
            or any(ord(c) < 33 for c in url)
            or host in {"localhost", "metadata.google.internal"}
            or host.endswith((".localhost", ".local", ".internal"))
        ):
            raise ValueError("unsafe")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not public_ip(host):
                raise ValueError("private_ip")
        return parsed
    except ValueError:
        raise ToolError("unsafe_url") from None


async def pinned_target(url: str) -> tuple[str, str, str]:
    parsed = validate_url(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise ToolError("dns_failure", transient=True) from None
    addresses = sorted({str(record[4][0]) for record in records})
    if not addresses or not all(public_ip(address) for address in addresses):
        raise ToolError("unsafe_dns")
    ip = addresses[0]
    authority = f"[{ip}]" if ":" in ip else ip
    target = urlunsplit(
        (parsed.scheme, f"{authority}:{port}", parsed.path or "/", parsed.query, "")
    )
    return target, parsed.netloc, host
