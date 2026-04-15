#!/usr/bin/env python3
"""
部署脚本 - 将项目部署到多台服务器
"""
import paramiko
import os
import sys
from pathlib import Path

# 多服务器配置
SERVERS = [
    {
        "host": "101.34.62.149",
        "user": "ubuntu",
        "password": "Wuxi,62047720",
        "remote_dir": "/home/ubuntu/ProjectInsight",
        "name": "腾讯云服务器"
    },
    {
        "host": "172.16.128.44",
        "user": "dev",
        "password": "dev@sass.",
        "remote_dir": "/home/dev/ProjectInsight",
        "name": "院服务器2"
    }
]

def create_ssh_client(host, user, password):
    """创建SSH连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
        return client
    except Exception as e:
        print(f"连接失败: {e}")
        return None

def run_command(client, cmd, show_output=True, sudo_password=None):
    """执行远程命令"""
    # 如果需要sudo且有密码，使用 -S 选项
    if sudo_password and 'sudo' in cmd:
        cmd = f"echo '{sudo_password}' | sudo -S {cmd.replace('sudo ', '', 1)}"

    print(f"[CMD] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_output:
        if out:
            # 过滤掉无法编码的字符
            try:
                print(out)
            except UnicodeEncodeError:
                print(out.encode('gbk', errors='replace').decode('gbk'))
        if err and '[sudo]' not in err:  # 过滤sudo密码提示
            try:
                print(f"[ERR] {err}")
            except UnicodeEncodeError:
                print(f"[ERR] {err.encode('gbk', errors='replace').decode('gbk')}")
    return out, err, stdout.channel.recv_exit_status()

def upload_directory(client, local_dir, remote_dir):
    """上传整个目录"""
    sftp = client.open_sftp()

    def mkdir_p(path):
        """递归创建目录"""
        try:
            sftp.stat(path)
        except FileNotFoundError:
            parent = '/'.join(path.split('/')[:-1])
            if parent and parent != path:
                mkdir_p(parent)
            try:
                sftp.mkdir(path)
            except:
                pass

    mkdir_p(remote_dir)

    # 需要跳过的目录名
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', '.claude'}

    for root, dirs, files in os.walk(local_dir):
        # 跳过不需要上传的目录（修改dirs列表会影响os.walk的遍历）
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        rel_path = os.path.relpath(root, local_dir)
        # 使用正斜杠作为远程路径分隔符
        if rel_path == '.':
            remote_path = remote_dir
        else:
            remote_path = remote_dir + '/' + rel_path.replace('\\', '/')
        mkdir_p(remote_path)

        for f in files:
            # 跳过不需要上传的文件
            if f.endswith(('.pyc', '.pyo', '.log', '.lock')):
                continue
            local_file = os.path.join(root, f)
            remote_file = remote_path + '/' + f
            print(f"[UPLOAD] {local_file} -> {remote_file}")
            try:
                sftp.put(local_file, remote_file)
            except Exception as e:
                print(f"[WARN] Failed to upload {local_file}: {e}")

    sftp.close()

def deploy_to_server(server_config):
    """部署到单个服务器"""
    host = server_config["host"]
    user = server_config["user"]
    password = server_config["password"]
    remote_dir = server_config["remote_dir"]
    name = server_config["name"]
    sudo_password = server_config.get("sudo_password", password)  # 默认使用登录密码

    def run_cmd(cmd, show_output=True):
        """带sudo密码支持的命令执行"""
        return run_command(client, cmd, show_output, sudo_password)

    print("=" * 60)
    print(f"开始部署到 {name}")
    print(f"服务器: {host}")
    print(f"用户: {user}")
    print("=" * 60)

    # 连接服务器
    print("\n[1] 连接服务器...")
    client = create_ssh_client(host, user, password)
    if client is None:
        print(f"连接 {name} 失败，跳过")
        return False
    print("连接成功!")

    # 检查系统环境
    print("\n[2] 检查系统环境...")
    run_cmd("cat /etc/os-release | head -3")
    run_cmd("python3 --version || python --version || echo 'Python not found'")

    # 安装必要软件
    print("\n[3] 安装依赖软件...")
    commands = [
        "sudo apt-get update -qq",
        "sudo apt-get install -y -qq python3 python3-pip python3-venv nodejs npm git",
    ]
    for cmd in commands:
        run_cmd(cmd)

    # 检查Node.js版本，如果太旧则安装新版本
    print("\n[4] 检查Node.js版本...")
    out, _, _ = run_cmd("node --version || echo 'none'", show_output=False)
    node_version = out.strip()
    print(f"Node版本: {node_version}")

    if node_version in ('none', ''):
        # 安装Node.js 18
        run_cmd("curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -")
        run_cmd("sudo apt-get install -y nodejs")

    # 创建项目目录
    print("\n[5] 创建项目目录...")
    run_cmd(f"mkdir -p {remote_dir}")

    # 上传项目文件
    print("\n[6] 上传项目文件...")
    local_dir = os.path.dirname(os.path.abspath(__file__))
    upload_directory(client, local_dir, remote_dir)

    # 安装Python依赖
    print("\n[7] 安装Python依赖...")
    run_cmd(f"cd {remote_dir} && pip3 install fastapi uvicorn numpy networkx pydantic python-multipart websockets scipy aiohttp")

    # 安装前端依赖并构建
    print("\n[8] 安装前端依赖...")
    run_cmd(f"cd {remote_dir}/frontend && npm install")

    print("\n[9] 构建前端...")
    run_cmd(f"cd {remote_dir}/frontend && npm run build")

    # 配置systemd服务
    print("\n[10] 配置后端服务...")
    backend_service = f"""[Unit]
Description=Info Cocoon Backend
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={remote_dir}
ExecStart=/usr/bin/python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    # 写入服务文件
    run_cmd(f"echo '{backend_service}' | sudo tee /etc/systemd/system/info-cocoon.service")
    run_cmd("sudo systemctl daemon-reload")
    run_cmd("sudo systemctl enable info-cocoon")
    run_cmd("sudo systemctl restart info-cocoon")

    # 配置nginx
    print("\n[11] 配置Nginx...")
    run_cmd("sudo apt-get install -y nginx")

    nginx_config = f"""server {{
    listen 80;
    server_name {host};

    # 前端静态文件
    location / {{
        root {remote_dir}/frontend/dist;
        try_files $uri $uri/ /index.html;
    }}

    # 后端API
    location /api/ {{
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    # WebSocket
    location /ws/ {{
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }}
}}"""
    run_cmd(f"echo '{nginx_config}' | sudo tee /etc/nginx/sites-available/info-cocoon")
    run_cmd("sudo rm -f /etc/nginx/sites-enabled/default")
    run_cmd("sudo ln -sf /etc/nginx/sites-available/info-cocoon /etc/nginx/sites-enabled/")
    run_cmd("sudo nginx -t && sudo systemctl restart nginx")

    # 检查服务状态
    print("\n[12] 检查服务状态...")
    run_cmd("sudo systemctl status info-cocoon --no-pager || true")
    run_cmd("sudo systemctl status nginx --no-pager || true")

    client.close()

    print("\n" + "=" * 60)
    print(f"{name} 部署完成!")
    print(f"访问地址: http://{host}")
    print("=" * 60)
    return True


def main():
    print("=" * 60)
    print("开始部署到多台服务器")
    print(f"服务器数量: {len(SERVERS)}")
    for s in SERVERS:
        print(f"  - {s['name']}: {s['host']}")
    print("=" * 60)

    results = []
    for server in SERVERS:
        success = deploy_to_server(server)
        results.append((server["name"], server["host"], success))

    print("\n" + "=" * 60)
    print("部署汇总")
    print("=" * 60)
    for name, host, success in results:
        status = "成功" if success else "失败"
        print(f"  {name} ({host}): {status}")
    print("=" * 60)

if __name__ == "__main__":
    main()
