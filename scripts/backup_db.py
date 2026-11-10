"""Dump MySQL including views; connection password is passed only to child environment."""
import argparse
from datetime import datetime
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import Config,BASE_DIR


def main():
    parser=argparse.ArgumentParser(description='一致性备份 northwind（需要 mysqldump 客户端）')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    binary=shutil.which('mysqldump')
    if not binary:
        parser.error('未找到 mysqldump，请安装 MySQL 8.0 客户端')
    path=args.output or BASE_DIR/'backups'/f'northwind-{datetime.now():%Y%m%d-%H%M%S}.sql'
    path.parent.mkdir(parents=True,exist_ok=True)
    command=[binary,'--host',Config.DB_HOST,'--port',str(Config.DB_PORT),'--user',Config.DB_USER,
        '--default-character-set=utf8mb4','--single-transaction','--no-tablespaces','--set-gtid-purged=OFF',
        '--column-statistics=0','--skip-add-locks','--skip-add-drop-table']
    if Config.DB_SSL_MODE not in {'VERIFY_IDENTITY', 'VERIFY_CA'}:
        parser.error('DB_SSL_MODE 仅支持 VERIFY_IDENTITY 或 VERIFY_CA')
    if Config.DB_SSL_MODE == 'VERIFY_CA' and not Config.DB_SSL_CA:
        parser.error('VERIFY_CA 必须配置可信 CA 文件')
    if Config.DB_SSL_CA:
        command += ['--ssl-ca',Config.DB_SSL_CA,'--ssl-mode='+Config.DB_SSL_MODE]
    command.append(Config.DB_NAME)
    env={**os.environ,'MYSQL_PWD':Config.DB_PASSWORD}
    # Exclusive creation avoids overwriting a previous backup; permissions protect hashes/data.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb') as output:
            with subprocess.Popen(command,env=env,stdout=subprocess.PIPE) as process:
                for line in process.stdout:
                    # Views are INVOKER views: remove only mysqldump's view DEFINER
                    # directive so restoration does not require the original account
                    # or SET_USER_ID privileges on a new cloud instance.
                    line=re.sub(rb'^(/\*!50013 )DEFINER=`(?:``|[^`])*`@`(?:``|[^`])*` (SQL SECURITY INVOKER \*/)',rb'\1\2',line)
                    output.write(line)
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode,command)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    print(f'备份已保存：{path.resolve()}')

if __name__=='__main__':
    main()
