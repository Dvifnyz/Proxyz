"""Proxyx — pool: rotasi, sticky session, skor, dan statistik.

Perbedaan dari repo asli (ProxyPoolManager):
- Urutan pool berdasarkan skor + residential dulu (bukan sekadar urutan panen).
- Evict berbasis skor: proxy dibuang setelah 3 gagal beruntun, bukan
  sekali gagal (satu timeout belum tentu proxy mati).
- Statistik per proxy + metrik evicted/refilled untuk /api/stats.
"""
from __future__ import annotations

import threading
import time
from collections import Counter

from .models import Proxy

SESSION_TTL = 600  # sticky session 10 menit (seperti repo asli)


class Pool:
    def __init__(self, proxies: list[Proxy] | None = None, session_ttl: int = SESSION_TTL):
        self._lock = threading.Lock()
        self._proxies: list[Proxy] = []
        self._idx = 0
        self._sessions: dict[str, tuple[Proxy, float]] = {}
        self._fails: Counter = Counter()
        self.session_ttl = session_ttl
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.evicted = 0
        self.refilled = 0
        self.started_at = time.time()
        if proxies:
            self.add(proxies)

    # ------------------------------------------------------------------
    @staticmethod
    def _rank(p: Proxy) -> tuple:
        # residential dulu, lalu skor tertinggi, lalu latency terendah.
        return (0 if p.residential else 1, -(p.score or 0), p.ms or 99999)

    def add(self, proxies: list[Proxy]) -> int:
        """Tambah proxy baru (dedup). Kembalikan jumlah yang ditambahkan."""
        with self._lock:
            have = {p.hostport for p in self._proxies}
            n = 0
            for p in proxies:
                if p.hostport not in have:
                    have.add(p.hostport)
                    self._proxies.append(p)
                    n += 1
            self._proxies.sort(key=self._rank)
            self.refilled += n
            return n

    def __len__(self) -> int:
        with self._lock:
            return len(self._proxies)

    def snapshot(self) -> list[Proxy]:
        with self._lock:
            return list(self._proxies)

    def _cleanup_sessions(self) -> None:
        now = time.time()
        dead = [k for k, (_, exp) in self._sessions.items() if exp < now]
        for k in dead:
            del self._sessions[k]

    def next(self, session_id: str | None = None, country: str | None = None) -> Proxy | None:
        """Ambil proxy berikutnya: sticky session dulu, lalu filter negara,
        lalu round-robin dari pool yang sudah diurutkan skor."""
        with self._lock:
            self._cleanup_sessions()
            if not self._proxies:
                return None
            if session_id and session_id in self._sessions:
                proxy, _ = self._sessions[session_id]
                if proxy in self._proxies:
                    return proxy
            candidates = self._proxies
            if country:
                cc = [p for p in candidates if (p.country_code or "").upper() == country.upper()]
                if cc:
                    candidates = cc
            proxy = candidates[self._idx % len(candidates)]
            self._idx += 1
            if session_id:
                self._sessions[session_id] = (proxy, time.time() + self.session_ttl)
            return proxy

    def force_rotate(self) -> Proxy | None:
        with self._lock:
            if not self._proxies:
                return None
            self._idx += 1
            return self._proxies[self._idx % len(self._proxies)]

    # ------------------------------------------------------------------
    def mark_success(self, proxy: Proxy) -> None:
        with self._lock:
            self.total_requests += 1
            self.success_requests += 1
            self._fails[proxy.hostport] = 0

    def mark_failed(self, proxy: Proxy) -> None:
        """Gagal 3x beruntun -> buang dari pool (evict)."""
        with self._lock:
            self.total_requests += 1
            self.failed_requests += 1
            self._fails[proxy.hostport] += 1
            if self._fails[proxy.hostport] >= 3:
                self._proxies = [p for p in self._proxies if p.hostport != proxy.hostport]
                self._sessions = {k: v for k, v in self._sessions.items()
                                  if v[0].hostport != proxy.hostport}
                del self._fails[proxy.hostport]
                self.evicted += 1

    def prune(self, hostports: list[str]) -> int:
        """Buang daftar hostport mati sekaligus (dipakai healer)."""
        with self._lock:
            before = len(self._proxies)
            drop = set(hostports)
            self._proxies = [p for p in self._proxies if p.hostport not in drop]
            self.evicted += before - len(self._proxies)
            return before - len(self._proxies)

    # ------------------------------------------------------------------
    def stats(self) -> dict:
        with self._lock:
            total = self.total_requests or 1
            return {
                "pool": len(self._proxies),
                "http": sum(1 for p in self._proxies if p.protocol == "http"),
                "socks4": sum(1 for p in self._proxies if p.protocol == "socks4"),
                "socks5": sum(1 for p in self._proxies if p.protocol == "socks5"),
                "residential": sum(1 for p in self._proxies if p.residential),
                "total_requests": self.total_requests,
                "success_requests": self.success_requests,
                "failed_requests": self.failed_requests,
                "success_pct": round(100 * self.success_requests / total, 1),
                "evicted": self.evicted,
                "refilled": self.refilled,
                "uptime_sec": int(time.time() - self.started_at),
            }
