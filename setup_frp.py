#!/usr/bin/env python3
"""
设置 frp 内网穿透 - 使用国内镜像加速
"""
import paramiko
import time

# 服务器配置
TENCENT_SERVER = {
    "host": "101.34.62.149",
    "user": "ubuntu",
    "password": "Wuxi,62047720",
}

CAMPUS_SERVER = {
    "host": "172.16.128.44",
    "user": "dev",
    "password": "dev@sass.",
}

FRP_VERSION = "0.61.1"

def create_ssh_client(host, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def run_cmd(client, cmd, sudo_pwd=None, show=True):
    if sudo_pwd and 'sudo' in cmd:
        cmd = f"echo '{sudo_pwd}' | sudo -S {cmd.replace('sudo ', '', 1)}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show and out:
        print(out[:500])
    if show and err and '[sudo]' not in err:
        print(f"[ERR] {err[:200]}")
    return out, stdout.channel.recv_exit_status()

def setup_frps():
    print("\n" + "=" * 60)
    print("Setting up frps on Tencent Cloud")
    print("=" * 60)

    client = create_ssh_client(TENCENT_SERVER["host"], TENCENT_SERVER["user"], TENCENT_SERVER["password"])
    if not client:
        return False

    # 使用 ghproxy 加速下载
    print("\n[1] Downloading frp...")
    urls = [
        f"https://mirror.ghproxy.com/https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_amd64.tar.gz",
        f"https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_amd64.tar.gz",
    ]

    for url in urls:
        print(f"Trying: {url[:60]}...")
        run_cmd(client, f"cd /tmp && rm -rf frp_* && wget -q --timeout=60 -O frp.tar.gz '{url}'")
        out, code = run_cmd(client, "ls -la /tmp/frp.tar.gz 2>/dev/null", show=False)
        if code == 0 and "frp.tar.gz" in out:
            print("Download OK")
            break
        print("Download failed, trying next...")
    else:
        print("All downloads failed")
        return False

    # 解压并安装
    print("\n[2] Installing...")
    run_cmd(client, "cd /tmp && tar -xzf frp.tar.gz")
    run_cmd(client, "sudo mkdir -p /opt/frp", TENCENT_SERVER["password"])
    run_cmd(client, "sudo cp /tmp/frp_*_linux_amd64/frps /opt/frp/", TENCENT_SERVER["password"])
    run_cmd(client, "sudo chmod +x /opt/frp/frps", TENCENT_SERVER["password"])

    # 配置
    print("\n[3] Configuring frps...")
    config = """[common]
bind_port = 7000
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = admin123
authentication_method = token
token = projectinsight2024
"""
    run_cmd(client, f"echo '{config}' | sudo tee /opt/frp/frps.toml", TENCENT_SERVER["password"])

    # Systemd 服务
    print("\n[4] Creating systemd service...")
    service = """[Unit]
Description=frp server
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    run_cmd(client, f"echo '{service}' | sudo tee /etc/systemd/system/frps.service", TENCENT_SERVER["password"])
    run_cmd(client, "sudo systemctl daemon-reload", TENCENT_SERVER["password"])
    run_cmd(client, "sudo systemctl enable frps", TENCENT_SERVER["password"])
    run_cmd(client, "sudo systemctl restart frps", TENCENT_SERVER["password"])

    # 防火墙
    print("\n[5] Opening firewall ports...")
    for port in ["7000", "7500", "8080", "8001", "2222"]:
        run_cmd(client, f"sudo ufw allow {port}", TENCENT_SERVER["password"], show=False)

    # 检查状态
    time.sleep(2)
    out, _ = run_cmd(client, "sudo systemctl status frps --no-pager | head -5", TENCENT_SERVER["password"])
    if "active (running)" in out:
        print(">>> frps is running")
    else:
        print(">>> frps failed to start")
        return False

    client.close()
    return True

def setup_frpc():
    print("\n" + "=" * 60)
    print("Setting up frpc on Campus Server 2")
    print("=" * 60)

    client = create_ssh_client(CAMPUS_SERVER["host"], CAMPUS_SERVER["user"], CAMPUS_SERVER["password"])
    if not client:
        return False

    # 下载
    print("\n[1] Downloading frp...")
    urls = [
        f"https://mirror.ghproxy.com/https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_amd64.tar.gz",
        f"https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_amd64.tar.gz",
    ]

    for url in urls:
        print(f"Trying: {url[:60]}...")
        run_cmd(client, f"cd /tmp && rm -rf frp_* && wget -q --timeout=60 -O frp.tar.gz '{url}'")
        out, code = run_cmd(client, "ls -la /tmp/frp.tar.gz 2>/dev/null", show=False)
        if code == 0 and "frp.tar.gz" in out:
            print("Download OK")
            break
        print("Download failed, trying next...")
    else:
        print("All downloads failed")
        return False

    # 安装
    print("\n[2] Installing...")
    run_cmd(client, "cd /tmp && tar -xzf frp.tar.gz")
    run_cmd(client, "sudo mkdir -p /opt/frp", CAMPUS_SERVER["password"])
    run_cmd(client, "sudo cp /tmp/frp_*_linux_amd64/frpc /opt/frp/", CAMPUS_SERVER["password"])
    run_cmd(client, "sudo chmod +x /opt/frp/frpc", CAMPUS_SERVER["password"])

    # 配置
    print("\n[3] Configuring frpc...")
    config = """[common]
server_addr = 101.34.62.149
server_port = 7000
token = projectinsight2024

[web]
type = tcp
local_ip = 127.0.0.1
local_port = 80
remote_port = 8080

[api]
type = tcp
local_ip = 127.0.0.1
local_port = 8000
remote_port = 8001

[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 2222
"""
    run_cmd(client, f"echo '{config}' | sudo tee /opt/frp/frpc.toml", CAMPUS_SERVER["password"])

    # Systemd 服务
    print("\n[4] Creating systemd service...")
    service = """[Unit]
Description=frp client
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frpc -c /opt/frp/frpc.toml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    run_cmd(client, f"echo '{service}' | sudo tee /etc/systemd/system/frpc.service", CAMPUS_SERVER["password"])
    run_cmd(client, "sudo systemctl daemon-reload", CAMPUS_SERVER["password"])
    run_cmd(client, "sudo systemctl enable frpc", CAMPUS_SERVER["password"])
    run_cmd(client, "sudo systemctl restart frpc", CAMPUS_SERVER["password"])

    # 检查状态
    time.sleep(2)
    out, _ = run_cmd(client, "sudo systemctl status frpc --no-pager | head -5", CAMPUS_SERVER["password"])
    if "active (running)" in out:
        print(">>> frpc is running")
    else:
        print(">>> frpc failed to start")
        return False

    client.close()
    return True

def main():
    print("=" * 60)
    print("FRP Tunnel Setup")
    print("=" * 60)
    print("""
Port Mapping:
  - Web (80)    -> Tencent:8080
  - API (8000)  -> Tencent:8001
  - SSH (22)    -> Tencent:2222
    """)

    if not setup_frps():
        print(">>> Tencent Cloud frps setup failed")
        return

    if not setup_frpc():
        print(">>> Campus Server frpc setup failed")
        return

    print("\n" + "=" * 60)
    print("FRP Setup Complete!")
    print("=" * 60)
    print("""
Access from home:
  - Web:     http://101.34.62.149:8080
  - API:     http://101.34.62.149:8001
  - API Doc: http://101.34.62.149:8001/docs
  - SSH:     ssh -p 2222 dev@101.34.62.149

Dashboard:
  - URL: http://101.34.62.149:7500
  - User: admin
  - Pass: admin123
    """)

if __name__ == "__main__":
    main()
