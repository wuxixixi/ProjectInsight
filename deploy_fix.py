#!/usr/bin/env python3
"""Deploy fixed frontend to both servers.

安全注意: 使用环境变量配置密码
"""
import paramiko
import os

# 使用环境变量读取密码
SERVERS = [
    {"host": "101.34.62.149", "user": "ubuntu", "password": os.environ.get("TENANT_CLOUD_PASSWORD", ""), "remote_dir": "/home/ubuntu/ProjectInsight", "name": "腾讯云"},
    {"host": "172.16.128.44", "user": "dev", "password": os.environ.get("YANYUAN_PASSWORD", ""), "remote_dir": "/home/dev/ProjectInsight", "name": "院服务器2"},
]

LOCAL_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
LOCAL_APP_VUE = os.path.join(os.path.dirname(__file__), "frontend", "src", "App.vue")


def upload_dir(sftp, local, remote):
    for root, dirs, files in os.walk(local):
        dirs[:] = [d for d in dirs if d not in {"node_modules", "__pycache__"}]
        rel = os.path.relpath(root, local)
        rpath = remote if rel == "." else remote + "/" + rel.replace("\\", "/")
        try:
            sftp.stat(rpath)
        except FileNotFoundError:
            sftp.mkdir(rpath)
        for f in files:
            if f.endswith((".pyc", ".log")):
                continue
            lf = os.path.join(root, f)
            rf = rpath + "/" + f
            sftp.put(lf, rf)
            print(f"  {rf}")


def deploy(server):
    host = server["host"]
    user = server["user"]
    pwd = server["password"]
    rdir = server["remote_dir"]
    name = server["name"]
    print(f"\n{'='*50}")
    print(f"Deploying to {name} ({host})")
    print(f"{'='*50}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=pwd, timeout=10)

    # Upload dist
    print("[1] Uploading frontend/dist...")
    sftp = client.open_sftp()
    upload_dir(sftp, LOCAL_DIST, rdir + "/frontend/dist")
    sftp.put(LOCAL_APP_VUE, rdir + "/frontend/src/App.vue")
    sftp.close()

    # Restart services
    print("[2] Restarting services...")
    client.exec_command(f"echo '{pwd}' | sudo -S systemctl restart info-cocoon")
    client.exec_command(f"echo '{pwd}' | sudo -S systemctl reload nginx")
    time.sleep(3)

    # Verify
    print("[3] Checking services...")
    for svc in ["info-cocoon", "nginx"]:
        stdin, stdout, stderr = client.exec_command(
            f"echo '{pwd}' | sudo -S systemctl status {svc} --no-pager | head -3"
        )
        out = stdout.read().decode("utf-8", errors="replace")
        print(f"  {svc}: {out.strip()[:100]}")

    # Test API
    print("[4] Testing API...")
    stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8000/ | head -c 100")
    out = stdout.read().decode("utf-8", errors="replace")
    print(f"  Backend: {out[:80]}")

    client.close()
    print(f"{name}: done")


for s in SERVERS:
    deploy(s)

print("\nAll done!")
