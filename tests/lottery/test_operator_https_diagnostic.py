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
