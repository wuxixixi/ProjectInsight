#!/usr/bin/env python3
"""Unified deployment entrypoint for ProjectInsight."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import paramiko


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"


@dataclass(frozen=True)
class ServerConfig:
    key: str
    name: str
    host: str
    user: str
    password_env: str
    remote_dir: str
    backend_service: str = "info-cocoon"
    web_service: str = "nginx"

    @property
    def password(self) -> str:
        return os.getenv(self.password_env, "").strip()


SERVERS: tuple[ServerConfig, ...] = (
    ServerConfig(
        key="tencent",
        name="Tencent Cloud",
        host="101.34.62.149",
        user="root",
        password_env="TENANT_CLOUD_PASSWORD",
        remote_dir="/root/ProjectInsight",
    ),
    ServerConfig(
        key="yanyuan",
        name="Server 2",
        host="172.16.128.44",
        user="dev",
        password_env="YANYUAN_PASSWORD",
        remote_dir="/home/dev/ProjectInsight",
    ),
)


def log(message: str) -> None:
    print(message, flush=True)


def run_local(args: list[str], cwd: Path | None = None) -> None:
    log(f"[local] {' '.join(args)}")
    # On Windows, need shell=True to find npm in PATH
    subprocess.run(args, cwd=cwd, check=True, shell=True)


def create_client(server: ServerConfig) -> paramiko.SSHClient:
    if not server.password:
        raise RuntimeError(f"missing password env: {server.password_env}")
    client = paramiko.SSHClient()
    # Security: Use WarningPolicy instead of AutoAddPolicy to reduce MITM risk
    # In production, consider using known_hosts file: client.load_host_keys('~/.ssh/known_hosts')
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    try:
        client.connect(server.host, username=server.user, password=server.password, timeout=30)
    except paramiko.ssh_exception.SSHException as e:
        # Fallback to AutoAddPolicy for development environments only (with warning)
        import warnings
        warnings.warn(
            f"Host key verification failed for {server.host}. "
            "Using AutoAddPolicy as fallback. Consider adding host key to known_hosts.",
            UserWarning
        )
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server.host, username=server.user, password=server.password, timeout=30)
    return client


def run_remote(
    client: paramiko.SSHClient,
    command: str,
    *,
    timeout: int = 300,
    check: bool = True,
) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if check and code != 0:
        raise RuntimeError(f"remote command failed ({code}): {command}\n{out}\n{err}")
    return code, out, err


def mkdir_p(sftp: paramiko.SFTPClient, path: str) -> None:
    todo: list[str] = []
    current = path.rstrip("/")
    while current and current != "/":
        todo.append(current)
        current = current.rsplit("/", 1)[0] if "/" in current else ""
    for item in reversed(todo):
        try:
            sftp.stat(item)
        except FileNotFoundError:
            sftp.mkdir(item)


def upload_file(sftp: paramiko.SFTPClient, local_path: Path, remote_path: str) -> None:
    mkdir_p(sftp, remote_path.rsplit("/", 1)[0])
    sftp.put(str(local_path), remote_path)


def upload_tree(
    sftp: paramiko.SFTPClient,
    local_dir: Path,
    remote_dir: str,
    *,
    skip_dirs: Iterable[str] = (),
    skip_suffixes: Iterable[str] = (),
) -> None:
    skip_dir_set = set(skip_dirs)
    skip_suffix_tuple = tuple(skip_suffixes)
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in skip_dir_set]
        rel = os.path.relpath(root, local_dir)
        current_remote = remote_dir if rel == "." else f"{remote_dir}/{rel.replace(os.sep, '/')}"
        mkdir_p(sftp, current_remote)
        for name in files:
            if skip_suffix_tuple and name.endswith(skip_suffix_tuple):
                continue
            local_path = Path(root) / name
            upload_file(sftp, local_path, f"{current_remote}/{name}")


def build_local_frontend() -> None:
    run_local(["npm", "run", "build"], cwd=FRONTEND_DIR)


def sync_frontend(sftp: paramiko.SFTPClient, server: ServerConfig) -> None:
    remote_frontend = f"{server.remote_dir}/frontend"
    upload_file(sftp, FRONTEND_DIR / "package.json", f"{remote_frontend}/package.json")
    upload_file(sftp, FRONTEND_DIR / "package-lock.json", f"{remote_frontend}/package-lock.json")
    upload_file(sftp, FRONTEND_DIR / "vite.config.js", f"{remote_frontend}/vite.config.js")
    upload_tree(
        sftp,
        FRONTEND_DIR / "src",
        f"{remote_frontend}/src",
        skip_dirs={"__pycache__"},
        skip_suffixes=(".map",),
    )
    upload_tree(sftp, FRONTEND_DIR / "public", f"{remote_frontend}/public")
    upload_tree(sftp, FRONTEND_DIR / "dist", f"{remote_frontend}/dist")


def sync_backend(sftp: paramiko.SFTPClient, server: ServerConfig) -> None:
    upload_tree(
        sftp,
        BACKEND_DIR,
        f"{server.remote_dir}/backend",
        skip_dirs={"__pycache__"},
        skip_suffixes=(".pyc", ".pyo"),
    )
    upload_file(sftp, PROJECT_ROOT / "requirements.txt", f"{server.remote_dir}/requirements.txt")


def verify_remote(server: ServerConfig, client: paramiko.SSHClient) -> None:
    _, backend_out, _ = run_remote(
        client,
        "curl -s http://127.0.0.1:8000/ | head -c 200",
        timeout=60,
    )
    _, web_out, _ = run_remote(
        client,
        "curl -I -s http://127.0.0.1/ | head -20",
        timeout=60,
    )
    log(f"[{server.key}] backend: {backend_out.strip()}")
    log(f"[{server.key}] web:\n{web_out.strip()}")


def deploy_server(server: ServerConfig, *, frontend_only: bool) -> None:
    log(f"[{server.key}] connect {server.user}@{server.host}")
    client = create_client(server)
    try:
        sftp = client.open_sftp()
        try:
            sync_frontend(sftp, server)
            if not frontend_only:
                sync_backend(sftp, server)
        finally:
            sftp.close()

        remote_frontend = f"{server.remote_dir}/frontend"
        if not frontend_only:
            run_remote(
                client,
                f"cd {server.remote_dir} && python3 -m pip install -r requirements.txt",
                timeout=900,
            )
        run_remote(client, f"cd {remote_frontend} && npm install", timeout=600)
        run_remote(client, f"cd {remote_frontend} && npm run build", timeout=600)
        run_remote(client, f"systemctl restart {server.backend_service}", timeout=120)
        run_remote(client, f"systemctl reload {server.web_service}", timeout=120)
        time.sleep(2)
        verify_remote(server, client)
    finally:
        client.close()


def selected_servers(keys: list[str]) -> list[ServerConfig]:
    if not keys:
        return list(SERVERS)
    wanted = set(keys)
    return [server for server in SERVERS if server.key in wanted]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy ProjectInsight")
    parser.add_argument(
        "--server",
        action="append",
        choices=[server.key for server in SERVERS],
        help="Deploy only the selected server key. Repeatable.",
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Sync and rebuild frontend only.",
    )
    parser.add_argument(
        "--skip-local-build",
        action="store_true",
        help="Skip local frontend build before remote deployment.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    servers = selected_servers(args.server or [])
    if not servers:
        log("no servers selected")
        return 1

    if not args.skip_local_build:
        build_local_frontend()

    for server in servers:
        deploy_server(server, frontend_only=args.frontend_only)

    log("deployment completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
