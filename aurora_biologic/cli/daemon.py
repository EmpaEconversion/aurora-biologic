"""Daemon to send commands from non-interactive SSH terminal to interactive terminal.

aurora-biologic uses EC-lab with OLE-COM enabled to control Biologic potentiostats.
OLE-COM can only be used in an interactive terminal session.
So we cannot run scripts from a non-interative terminal, like through SSH.
Run this daemon in an interactive terminal session on the PC with EC-lab and OLE-COM enabled.
It will listen for commands on a socket and execute them in the interactive terminal.
Commands sent to the Daemon are exectued first-in, first-out with a queue.
This allows you to run commands from a non-interactive terminal, like through SSH.
"""

import contextlib
import logging
import queue
import socket
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)
logger.setLevel("INFO")
HOST = "127.0.0.1"
PORT = 48751  # Arbitrary

# Queue avoids OLE-COM commands being executed in parallel
command_queue = queue.Queue()


def recv_all(sock: socket.socket) -> bytes:
    """Receive all data from the socket until it is closed."""
    chunks = []
    while True:
        chunk = sock.recv(32768)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def send_command(command: list[str]) -> str:
    """Send a command to the Biologic daemon and print the response."""
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as sock:
            sock.sendall(" ".join(command).encode())
            response = recv_all(sock)
            return response.decode().strip()
    except ConnectionRefusedError:
        logger.exception(
            "Biologic daemon not running - run 'biologic daemon' "
            "in a GUI session on the PC with EC-lab and OLE-COM."
        )
        sys.exit(1)


def receive_command(conn: socket.socket, addr: tuple[str, int]) -> None:
    """Receive a command from the client and add it to the execution queue."""
    logger.debug("Connection from %s", addr)
    try:
        command = conn.recv(4096).decode()
        if not command.startswith("biologic"):
            logger.warning("Invalid command from %s: %s", addr, command)
            conn.sendall(b"Invalid command\n")
            conn.close()
            return

        logger.debug("Enqueuing command from %s: %s", addr, command)
        command_queue.put((command, conn, addr))

    except Exception as e:
        logger.exception("Failed to read command from %s", addr)
        with contextlib.suppress(Exception):
            conn.sendall(f"Error: {e}".encode())

        conn.close()


def command_worker() -> None:
    """Worker thread that processes commands from the queue one at a time."""
    while True:
        command, conn, addr = command_queue.get()
        try:
            logger.debug("Processing command from %s: %s", addr, command)
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                conn.sendall(result.stderr.encode())
            else:
                conn.sendall(result.stdout.encode())
        except Exception as e:
            logger.exception("Error executing command from %s", addr)
            with contextlib.suppress(Exception):
                conn.sendall(f"Execution error: {e}".encode())
        finally:
            conn.close()
            command_queue.task_done()


def start_daemon() -> None:
    """Start the Biologic daemon to listen for commands."""
    logger.critical(
        "Starting listener on %s:%s. Closing this terminal will kill the daemon.",
        HOST,
        PORT,
    )
    threading.Thread(target=command_worker, daemon=True).start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=receive_command, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    start_daemon()
