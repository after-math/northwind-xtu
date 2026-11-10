#!/bin/zsh
set -eu
cd "$(dirname "$0")"
if [[ ! -f .env || ! -x .venv/bin/python ]]; then
  echo '请先按 README.md 完成环境配置。'
  read '?按回车退出'
  exit 1
fi
if [[ -f compose.yaml ]] && /usr/bin/grep -q '^DB_PORT=3307$' .env; then
  if ! docker info >/dev/null 2>&1; then
    echo '请先启动 Docker Desktop，等待就绪后再运行本文件。'
    read '?按回车退出'
    exit 1
  fi
  docker compose up -d --wait
fi
echo '本地地址：http://127.0.0.1:5000'
echo '管理员随机密码见 instance/local-admin.txt；关闭时按 Ctrl+C。'
exec .venv/bin/python app.py
