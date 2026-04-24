#!/usr/bin/env python3
"""上传项目文件到服务器"""
import paramiko
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.environ.get("UPLOAD_SERVER_HOST", "101.34.62.149")
SERVER_USER = os.environ.get("UPLOAD_SERVER_USER", "root")
SERVER_PASS = os.environ.get("UPLOAD_SERVER_PASSWORD", "")
REMOTE_DIR = os.environ.get("UPLOAD_REMOTE_DIR", "/root/ProjectInsight")
LOCAL_DIR = os.environ.get("UPLOAD_LOCAL_DIR", PROJECT_ROOT)

def main():
    if not SERVER_PASS:
        raise RuntimeError("UPLOAD_SERVER_PASSWORD is not set")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)

    sftp = client.open_sftp()

    def mkdir_p(remote_path):
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            parts = remote_path.split('/')
            current = ''
            for part in parts:
                if not part:
                    continue
                current += '/' + part
                try:
                    sftp.mkdir(current)
                except:
                    pass

    mkdir_p(REMOTE_DIR)

    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'reports'}
    skip_exts = {'.pyc', '.pyo', '.log', '.tmp'}

    count = 0
    for root, dirs, files in os.walk(LOCAL_DIR):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        rel_path = os.path.relpath(root, LOCAL_DIR)
        if rel_path == '.':
            remote_path = REMOTE_DIR
        else:
            remote_path = REMOTE_DIR + '/' + rel_path.replace(chr(92), '/')

        mkdir_p(remote_path)

        for f in files:
            if any(f.endswith(ext) for ext in skip_exts):
                continue

            local_file = os.path.join(root, f)
            remote_file = remote_path + '/' + f

            try:
                sftp.put(local_file, remote_file)
                count += 1
                if count % 20 == 0:
                    print(f'Uploaded {count} files...')
            except Exception as e:
                print(f'Failed: {local_file} -> {e}')

    print(f'Upload complete: {count} files')
    sftp.close()
    client.close()

if __name__ == '__main__':
    main()
