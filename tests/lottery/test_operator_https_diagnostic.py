"""Offline tests of the phase-isolated, non-attesting official-site diagnostic."""
from unittest.mock import Mock, patch

import pytest

from lrei.lottery.operator_https_diagnostic import diagnose


def test_dns_failure_stops_before_tcp():
    with patch("lrei.lottery.operator_https_diagnostic.socket.getaddrinfo", side_effect=OSError("dns")):
        with patch("lrei.lottery.operator_https_diagnostic.socket.socket") as make_socket:
            result = diagnose()
    assert result["phases"]["dns"]["ok"] is False
    assert "tcp" not in result["phases"]
    make_socket.assert_not_called()
    assert result["source_provenance_verified"] is False
    assert result["dataset_promotion_approved"] is False


def test_tcp_connect_uses_resolved_sockaddr_and_never_reresolves():
    address = ("127.0.0.1", 443)
    sock = Mock()
    with patch("lrei.lottery.operator_https_diagnostic.socket.getaddrinfo", return_value=[(2, 1, 6, "", address)]) as dns:
        with patch("lrei.lottery.operator_https_diagnostic.socket.socket", return_value=sock) as factory:
            with patch("lrei.lottery.operator_https_diagnostic.ssl.create_default_context") as sslctx:
                tls = Mock()
                tls.recv.return_value = b"HTTP/1.1 405 Method Not Allowed\\r\\n"
                sslctx.return_value.wrap_socket.return_value = tls
                result = diagnose()
    dns.assert_called_once()
    factory.assert_called_once_with(2, 1, 6)
    sock.connect.assert_called_once_with(address)
    tls.sendall.assert_called_once()
    assert result["phases"]["dns"]["ok"] is True
    assert result["phases"]["tcp"]["ok"] is True
    assert result["phases"]["tls"]["ok"] is True
    assert result["phases"]["http_first_bytes"]["ok"] is True
    assert result["source_provenance_verified"] is False


def test_failed_tcp_connection_closes_socket():
    sock = Mock()
    sock.connect.side_effect = TimeoutError("timeout")
    with patch("lrei.lottery.operator_https_diagnostic.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
        with patch("lrei.lottery.operator_https_diagnostic.socket.socket", return_value=sock):
            result = diagnose()
    sock.close.assert_called_once()
    assert result["phases"]["tcp"]["ok"] is False
    assert "tls" not in result["phases"]


@pytest.mark.parametrize("bad", [0, -1, 16, "8", None])
def test_invalid_timeout_rejected(bad):
    with pytest.raises(ValueError):
        diagnose(timeout_seconds=bad)



def test_ip_families_are_independently_probed_without_download():
    from lrei.lottery.operator_https_diagnostic import diagnose_ip_families
    ipv4 = ("192.0.2.10", 443)
    ipv6 = ("2001:db8::10", 443, 0, 0)
    first = Mock()
    first.__enter__ = Mock(return_value=first)
    first.__exit__ = Mock(return_value=False)
    first.connect.side_effect = TimeoutError("ipv4 timeout")
    second = Mock()
    second.__enter__ = Mock(return_value=second)
    second.__exit__ = Mock(return_value=False)

    def resolve(host, port, *, family, type):
        assert port == 443
        return [(family, 1, 6, "", ipv4 if family == 2 else ipv6)]

    with patch("lrei.lottery.operator_https_diagnostic.socket.getaddrinfo", side_effect=resolve) as dns:
        with patch("lrei.lottery.operator_https_diagnostic.socket.socket", side_effect=[first, second]) as create:
            result = diagnose_ip_families(timeout_seconds=3)

    assert dns.call_count == 2
    assert create.call_count == 2
    first.settimeout.assert_called_once_with(3)
    second.settimeout.assert_called_once_with(3)
    first.connect.assert_called_once_with(ipv4)
    second.connect.assert_called_once_with(ipv6)
    assert result["families"]["ipv4"]["tcp_ok"] is False
    assert result["families"]["ipv4"]["tcp_error_type"] == "TimeoutError"
    assert result["families"]["ipv6"]["tcp_ok"] is True
    assert result["source_provenance_verified"] is False
    assert result["dataset_promotion_approved"] is False


def test_missing_ipv6_does_not_block_ipv4_diagnosis():
    from lrei.lottery.operator_https_diagnostic import diagnose_ip_families
    sock = Mock()
    sock.__enter__ = Mock(return_value=sock)
    sock.__exit__ = Mock(return_value=False)

    def resolve(host, port, *, family, type):
        if family == 10:
            raise OSError("IPv6 unavailable")
        return [(2, 1, 6, "", ("192.0.2.2", 443))]

    with patch("lrei.lottery.operator_https_diagnostic.socket.getaddrinfo", side_effect=resolve):
        with patch("lrei.lottery.operator_https_diagnostic.socket.socket", return_value=sock) as create:
            result = diagnose_ip_families()
    create.assert_called_once()
    assert result["families"]["ipv4"]["tcp_ok"] is True
    assert result["families"]["ipv6"]["dns_ok"] is False
    assert result["families"]["ipv6"]["tcp_ok"] is False


@pytest.mark.parametrize("bad", [0, -2, 20, True, None, "2"])
def test_bad_ip_family_timeout_rejected(bad):
    from lrei.lottery.operator_https_diagnostic import diagnose_ip_families
    with pytest.raises(ValueError):
        diagnose_ip_families(timeout_seconds=bad)
