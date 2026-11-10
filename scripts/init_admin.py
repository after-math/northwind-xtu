"""Create/update an administrator without embedding a password in source or arguments."""
import argparse
import getpass
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import query,execute,transaction


def main():
    parser=argparse.ArgumentParser(description='创建管理员；已有账号需加 --reset 才能重置密码')
    parser.add_argument('--username',default='admin')
    parser.add_argument('--reset',action='store_true')
    args=parser.parse_args()
    if not args.username.strip() or len(args.username)>64:
        parser.error('账号须为 1 至 64 个字符')
    password=os.getenv('ADMIN_PASSWORD')
    if not password:
        password=getpass.getpass('管理员密码（至少 12 位）：')
        if password!=getpass.getpass('再次输入：'):
            parser.error('两次密码不一致')
    if len(password)<12:
        parser.error('密码至少 12 位')
    app=create_app()
    with app.app_context(),transaction():
        user=query('SELECT id FROM admin_user WHERE username=%s',(args.username,),one=True)
        if user and not args.reset:
            parser.error('账号已存在；重置时使用 --reset')
        hashed=generate_password_hash(password)
        if user:
            execute('UPDATE admin_user SET password_hash=%s WHERE id=%s',(hashed,user['id']))
        else:
            execute('INSERT INTO admin_user (username,password_hash) VALUES (%s,%s)',(args.username,hashed))
    print('管理员已保存。密码未写入源码。')

if __name__=='__main__':
    main()
