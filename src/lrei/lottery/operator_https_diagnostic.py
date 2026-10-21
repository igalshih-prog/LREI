"""Non-attesting, bounded network phase diagnostics for the official Lotto CSV host.

This tool NEVER verifies source content, changes datasets or reports source provenance.
It reports only DNS/TCP/TLS/HTTP phases; TLS verification stays enabled.
"""
from __future__ import annotations

import json
import socket
import ssl
import sys
import time
from urllib.parse import urlsplit

from .official_draw_source import OFFICIAL_CSV_URL, _safe_official_url


def diagnose(*, timeout_seconds: float = 8.0) -> dict:
    if not 0 < timeout_seconds <= 15:
        raise ValueError("timeout_seconds must be in (0, 15]")
    _safe_official_url(OFFICIAL_CSV_URL)
    parsed = urlsplit(OFFICIAL_CSV_URL)
    host = parsed.hostname
    result = {
        "schema_version": 1, "source_host": host,
        "status": "diagnostic_only_NOT_source_attestation",
        "source_provenance_verified": False,
        "dataset_promotion_approved": False,
        "phases": {},
    }
    def run_phase(name, operation):
        start = time.monotonic()
        try:
            value = operation()
            result["phases"][name] = {
                "ok": True, "elapsed_ms": round((time.monotonic() - start) * 1000),
            }
            return value
        except (OSError, ssl.SSLError, ValueError) as exc:
            result["phases"][name] = {
                "ok": False, "elapsed_ms": round((time.monotonic() - start) * 1000),
                "error_type": type(exc).__name__,
            }
            return None
    addresses = run_phase("dns", lambda: socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
    if not addresses:
        return result
    # A single bounded connection, not an open-ended address fallback.
    family, kind, proto, _, sockaddr = addresses[0]
    sock = run_phase("tcp", lambda: socket.create_connection(sockaddr, timeout=timeout_seconds))
    if sock is None:
        return result
    try:
        sock.settimeout(timeout_seconds)
        context = ssl.create_default_context()
        tls = run_phase("tls", lambda: context.wrap_socket(sock, server_hostname=host))
        if tls is None:
            return result
        try:
            request = (
                f"HEAD {parsed.path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "User-Agent: LREI-connectivity-diagnostic/1.0\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            def http_headers():
                tls.sendall(request)
                return tls.recv(512)
            response = run_phase("http_first_bytes", http_headers)
            if response is not None:
                # HTTP response code only; never accept content or claim authenticity.
                first = response.split(b"\r\n", 1)[0]
                result["http_status_line"] = first.decode("ascii", errors="replace")[:100]
        finally:
            tls.close()
    finally:
        sock.close()
    return result


def main() -> None:
    report = diagnose()
    print(json.dumps(report, sort_keys=True))
    if any(not phase["ok"] for phase in report["phases"].values()):
        sys.exit(2)


if __name__ == "__main__":
    main()
