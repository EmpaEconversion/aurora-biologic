"""Unit tests for daemon."""

import contextlib
import socket
from unittest.mock import patch

from aurora_biologic.cli.daemon import command_queue, command_worker, receive_command


def test_receive_command_invalid() -> None:
    """`receieve_command` should reject non-biologic commands."""
    server, client = socket.socketpair()
    client.sendall(b"notbiologic foo")
    client.shutdown(socket.SHUT_WR)
    receive_command(server, ("127.0.0.1", 9999))  # runs synchronously
    response = client.recv(1024)
    assert b"Invalid command" in response
    server.close()
    client.close()


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
    assert client.recv(1024).strip() == b"ok"
    server.close()
    client.close()
