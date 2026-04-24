#!/usr/bin/env python3
"""自动部署脚本 - 本地 + 腾讯云 + 院服务器2

安全注意: 使用环境变量配置密码
"""
import subprocess
import sys
import time
from datetime import datetime
import paramiko
import os

# 使用环境变量读取密码
SERVERS = [
    {"host": "101.34.62.149", "user": "ubuntu", "password": os.environ.get("TENANT_CLOUD_PASSWORD", ""), "remote_dir": "/home/ubuntu/ProjectInsight", "name": "腾讯云"},
    {"host": "172.16.128.44", "user": "dev", "password": os.environ.get("YANYUAN_PASSWORD", ""), "remote_dir": "/home/dev/ProjectInsight", "name": "院内2"},
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def run_local(cmd, cwd=None):
    """执行本地命令"""
    log(f"本地执行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout:
        print(result.stdout.strip().encode('gbk', errors='replace').decode('gbk'))
    if result.returncode != 0 and result.stderr:
        print(f"[ERROR] {result.stderr.strip().encode('gbk', errors='replace').decode('gbk')}")
    return result.returncode == 0


def deploy_local():
    """部署本地环境"""
    log("=" * 50)
    log("开始本地部署")
    log("=" * 50)

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # 构建前端
    log("[1] 构建前端...")
    if not run_local("npm run build", cwd=os.path.join(project_dir, "frontend")):
        log("前端构建失败，检查依赖...")
        run_local("npm install", cwd=os.path.join(project_dir, "frontend"))
        if not run_local("npm run build", cwd=os.path.join(project_dir, "frontend")):
            log("前端构建仍失败")
            return False

    # 本地服务需要手动启动（后台运行）
    log("[2] 本地服务需手动启动:")
    log("    后端: uvicorn backend.app:app --reload --port 8000")
    log("    前端: cd frontend && npm run dev")

    log("本地部署完成")
    return True


def upload_dir(sftp, local, remote):
    """上传目录"""
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', '.claude'}
    for root, dirs, files in os.walk(local):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(root, local)
        rpath = remote if rel == "." else remote + "/" + rel.replace("\\", "/")
        try:
            sftp.stat(rpath)
        except FileNotFoundError:
            try:
                sftp.mkdir(rpath)
            except:
                pass
        for f in files:
            if f.endswith((".pyc", ".pyo", ".log", ".lock")):
                continue
            lf = os.path.join(root, f)
            rf = rpath + "/" + f
            try:
                sftp.put(lf, rf)
            except Exception as e:
                log(f"  上传失败 {lf}: {e}")


def deploy_remote(server):
    """部署到远程服务器"""
    host = server["host"]
    user = server["user"]
    pwd = server["password"]
    rdir = server["remote_dir"]
    name = server["name"]

    log("=" * 50)
    log(f"开始部署到 {name} ({host})")
    log("=" * 50)

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=pwd, timeout=30)
    except Exception as e:
        log(f"连接失败: {e}")
        return False

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # 上传后端代码
    log("[1] 上传后端代码...")
    sftp = client.open_sftp()
    upload_dir(sftp, os.path.join(project_dir, "backend"), rdir + "/backend")
    sftp.close()

    # 上传前端构建产物
    log("[2] 上传前端构建产物...")
    sftp = client.open_sftp()
    upload_dir(sftp, os.path.join(project_dir, "frontend", "dist"), rdir + "/frontend/dist")
    sftp.close()

    # 重启服务
    log("[3] 重启服务...")
    stdin, stdout, stderr = client.exec_command(f"echo '{pwd}' | sudo -S systemctl restart info-cocoon", timeout=30)
    stdout.read()
    stdin, stdout, stderr = client.exec_command(f"echo '{pwd}' | sudo -S systemctl reload nginx", timeout=30)
    stdout.read()
    time.sleep(2)

    # 验证服务
    log("[4] 验证服务...")
    stdin, stdout, stderr = client.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/", timeout=10)
    code = stdout.read().decode().strip()
    log(f"  后端状态码: {code}")

    client.close()
    log(f"{name} 部署完成")
    return True


def main():
    log("=" * 60)
    log("开始自动部署")
    log("=" * 60)

    results = []

    # 1. 本地部署
    results.append(("本地", deploy_local()))

    # 2. 远程服务器部署
    for server in SERVERS:
        success = deploy_remote(server)
        results.append((server["name"], success))

    # 汇总
    log("=" * 60)
    log("部署汇总")
    log("=" * 60)
    for name, success in results:
        status = "成功" if success else "失败"
        log(f"  {name}: {status}")

    return all(s for _, s in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
