"""Unit tests for daemon."""

import contextlib
import json
import socket
from unittest.mock import MagicMock, patch

from aurora_biologic.cli.daemon import command_queue, command_worker, receive_command


def test_receive_command_invalid() -> None:
    """`receieve_command` should reject non-biologic commands."""
    server, client = socket.socketpair()
    client.sendall(b"notbiologic foo")
    client.shutdown(socket.SHUT_WR)
    receive_command(server, ("127.0.0.1", 9999))  # runs synchronously
    response = json.loads(client.recv(1024).decode())
    assert response["returncode"] == 1
    assert "Invalid command" in response["stderr"]
    server.close()
    client.close()


def test_receive_command_error() -> None:
    """`receive_command` should send error response without stopping daemon when error raised."""
    conn = MagicMock(spec=socket.socket)
    conn.recv.side_effect = ValueError("couldn't decode command")
    receive_command(conn, ("127.0.0.1", 9999))
    conn.sendall.assert_called_once()
    response = json.loads(conn.sendall.call_args[0][0].decode())
    assert response["returncode"] == 1
    assert "Error:" in response["stderr"]
    conn.close.assert_called_once()


def test_command_worker_one_shot() -> None:
    """Run the daemon loop once, mock a valid command."""
    server, client = socket.socketpair()
    # Patch subprocess so it doesn't actually spawn a new process

    with patch("aurora_biologic.cli.daemon.subprocess.run") as mock_run:
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""})()
        command_queue.put(("biologic status", server, ("127.0.0.1", 0)))
        # Patch command_queue.get to only run once, then SystemExit
        # Otherwise the daemon loop would block the main thread infinitely
        original_get = command_queue.get
        calls: list = []

        def get_once(**kw):
            """Only run original_get once, then raise SystemExit."""
            if calls:
                raise SystemExit
            calls.append(1)
            return original_get(**kw)

        with (
            patch.object(command_queue, "get", side_effect=get_once),
            contextlib.suppress(SystemExit),
        ):
            command_worker()
    response = json.loads(client.recv(1024).decode())
    assert response["returncode"] == 0
    assert response["stdout"] == "ok\n"
    server.close()
    client.close()


def test_command_worker_one_shot_error() -> None:
    """Run the daemon loop once, mock a valid command."""
    server, client = socket.socketpair()
    # Patch subprocess so it doesn't actually spawn a new process

    with patch("aurora_biologic.cli.daemon.subprocess.run") as mock_run:
        mock_run.side_effect = ValueError("Something crashed")
        command_queue.put(("biologic status", server, ("127.0.0.1", 0)))
        # Patch command_queue.get to only run once, then SystemExit
        # Otherwise the daemon loop would block the main thread infinitely
        original_get = command_queue.get
        calls: list = []

        def get_once(**kw):
            """Only run original_get once, then raise SystemExit."""
            if calls:
                raise SystemExit
            calls.append(1)
            return original_get(**kw)

        with (
            patch.object(command_queue, "get", side_effect=get_once),
            contextlib.suppress(SystemExit),
        ):
            command_worker()
    response = json.loads(client.recv(1024).decode())
    assert response["returncode"] == 1
    assert "Execution error" in response["stderr"]
    server.close()
    client.close()
