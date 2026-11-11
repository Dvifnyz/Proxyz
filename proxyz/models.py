"""Proxyz — model data proxy (satu bentuk untuk semua modul)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Proxy:
    protocol: str  # http | socks4 | socks5
    ip: str
    port: int
    username: str = ""
    password: str = ""
    ms: int | None = None          # latency saat dicek
    anonymity: str = ""            # elite | anonymous | transparent | tcp-ok
    country: str = ""
    country_code: str = ""
    city: str = ""
    isp: str = ""
    egress_ip: str = ""
    score: int = 0                 # 0-100, dihitung checker
    source: str = ""               # sumber panen / webshare / manual
    residential: bool = False

    @property
    def hostport(self) -> str:
        return f"{self.ip}:{self.port}"

    @property
    def auth(self) -> str:
        if self.username:
            return f"{self.username}:{self.password}@"
        return ""

    @property
    def url(self) -> str:
        """Format URL lengkap, siap dipakai requests/aiohttp/curl."""
        return f"{self.protocol}://{self.auth}{self.hostport}"

    def to_dict(self) -> dict:
        return {
            "protocol": self.protocol, "ip": self.ip, "port": self.port,
            "proxy": self.hostport, "url": self.url,
            "ms": self.ms, "anonymity": self.anonymity,
            "country": self.country, "country_code": self.country_code,
            "city": self.city, "isp": self.isp, "egress_ip": self.egress_ip,
            "score": self.score, "source": self.source,
            "residential": self.residential,
        }

    @classmethod
    def from_string(cls, text: str, source: str = "manual") -> Proxy | None:
        """Parse `proto://user:pass@ip:port`, `user:pass@ip:port`,
        atau `ip:port` polos (default http)."""
        text = text.strip()
        if not text or text.startswith("#"):
            return None
        m = re.match(
            r"(?:(?P<proto>https?|socks4|socks5)://)?"
            r"(?:(?P<user>[^:/@]+):(?P<pw>.+)@)?"  # .+ rakus: password boleh mengandung @
            r"(?P<ip>(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})"
            r":(?P<port>\d{2,5})\s*$",
            text, re.IGNORECASE,
        )
        if not m:
            return None
        port = int(m.group("port"))
        if not 1 <= port <= 65535:
            return None
        proto = (m.group("proto") or "http").lower()
        if proto == "https":
            proto = "http"
        return cls(protocol=proto, ip=m.group("ip"), port=port,
                   username=m.group("user") or "",
                   password=m.group("pw") or "", source=source)
