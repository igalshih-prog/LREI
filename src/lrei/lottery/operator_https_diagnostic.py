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
    if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 15:
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
    def open_tcp():
        # Use the exact DNS result; create_connection() would resolve again.
        candidate = socket.socket(family, kind, proto)
        try:
            candidate.settimeout(timeout_seconds)
            candidate.connect(sockaddr)
            return candidate
        except BaseException:
            candidate.close()
            raise
    sock = run_phase("tcp", open_tcp)
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



def diagnose_ip_families(*, timeout_seconds: float = 5.0) -> dict:
    """Probe at most one DNS-returned TCP address per family, never fetch CSV."""
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 0 < timeout_seconds <= 15
    ):
        raise ValueError("timeout_seconds must be in (0, 15]")
    _safe_official_url(OFFICIAL_CSV_URL)
    host = urlsplit(OFFICIAL_CSV_URL).hostname
    result = {
        "schema_version": 1,
        "status": "ip_family_connectivity_only_NOT_source_attestation",
        "source_host": host,
        "source_provenance_verified": False,
        "dataset_promotion_approved": False,
        "families": {},
    }
    for family, name in ((socket.AF_INET, "ipv4"), (socket.AF_INET6, "ipv6")):
        outcome = {"dns_ok": False, "tcp_ok": False}
        result["families"][name] = outcome
        started = time.monotonic()
        try:
            addresses = socket.getaddrinfo(
                host, 443, family=family, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            outcome["dns_error_type"] = type(exc).__name__
            continue
        outcome["dns_elapsed_ms"] = round((time.monotonic() - started) * 1000)
        if not addresses:
            outcome["dns_error_type"] = "NoAddresses"
            continue
        outcome["dns_ok"] = True
        af, kind, proto, _, sockaddr = addresses[0]
        started = time.monotonic()
        try:
            with socket.socket(af, kind, proto) as sock:
                sock.settimeout(timeout_seconds)
                sock.connect(sockaddr)
            outcome["tcp_ok"] = True
        except OSError as exc:
            outcome["tcp_error_type"] = type(exc).__name__
        outcome["tcp_elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result


def main() -> None:
    report = diagnose()
    # Independent IPv4/IPv6 TCP diagnosis; no download or source attestation.
    families = diagnose_ip_families()
    report["ip_family_diagnostic"] = families
    print(json.dumps(report, sort_keys=True))
    # IPv6 is optional on some runners; report it, but do not require it.
    # Still fail closed if the primary check fails or neither family connects.
    if any(not phase["ok"] for phase in report["phases"].values()) or not any(
        f["tcp_ok"] for f in families["families"].values()
    ):
        sys.exit(2)


if __name__ == "__main__":
    main()
