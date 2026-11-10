"""Explicit, non-destructive MySQL import. Never called by application startup."""
import argparse
import getpass
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import Config,BASE_DIR
from app.db import connect


def statements(source):
    """Split trusted bundled SQL, respecting quotes and line/block comments."""
    buffer=[]
    quote=None
    index=0
    while index<len(source):
        char=source[index]
        nxt=source[index:index+2]
        if quote:
            buffer.append(char)
            if char=='\\' and quote!='`' and index+1<len(source):
                index+=1
                buffer.append(source[index])
            elif char==quote:
                if index+1<len(source) and source[index+1]==quote:
                    index+=1
                    buffer.append(source[index])
                else:
                    quote=None
        elif nxt=='--' and (index+2==len(source) or source[index+2].isspace()):
            end=source.find('\n',index)
            index=len(source) if end<0 else end
            buffer.append('\n')
        elif nxt=='/*':
            end=source.find('*/',index+2)
            if end<0:
                raise ValueError('SQL 注释未闭合')
            index=end+1
            buffer.append(' ')
        elif char in "'\"`":
            quote=char
            buffer.append(char)
        elif char==';':
            sql=''.join(buffer).strip()
            if sql:
                yield sql
            buffer=[]
        else:
            buffer.append(char)
        index+=1
    if quote:
        raise ValueError('SQL 字符串未闭合')
    if ''.join(buffer).strip():
        yield ''.join(buffer).strip()


def main():
    parser=argparse.ArgumentParser(description='仅向空库导入 Northwind，或仅应用幂等扩展')
    parser.add_argument('--extensions-only',action='store_true')
    parser.add_argument('--user',help='具有 DDL 权限的初始化账号；指定后交互输入密码')
    args=parser.parse_args()
    cfg={key:getattr(Config,key) for key in dir(Config) if key.startswith('DB_')}
    if args.user:
        cfg.update(DB_USER=args.user,DB_PASSWORD=getpass.getpass('初始化账号密码：'))
    with connect(cfg) as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION() AS version')
            version=cursor.fetchone()['version']
            if not version.startswith('8.0.'):
                raise SystemExit(f'要求 MySQL 8.0，当前为 {version}；未执行导入。')
            if not args.extensions_only:
                cursor.execute('SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=DATABASE()')
                if cursor.fetchone()['n']:
                    raise SystemExit('目标数据库不是空库，已拒绝重复导入。已有数据仅运行 --extensions-only。')
                paths=[BASE_DIR/'data/northwind.mysql.sql',BASE_DIR/'sql/extensions.sql']
            else:
                paths=[BASE_DIR/'sql/extensions.sql']
            for path in paths:
                for number,sql in enumerate(statements(path.read_text()),1):
                    try:
                        cursor.execute(sql)
                    except Exception as exc:
                        print(f'{path.name} 第 {number} 条失败，已停止。MySQL DDL 不可回滚；请检查空库导入状态。',file=sys.stderr)
                        raise exc
                print(f'{path.name} 已执行。')
            cursor.execute('SELECT COUNT(*) AS n FROM Orders')
            print(f'MySQL {version} · 订单数 {cursor.fetchone()["n"]}')

if __name__=='__main__':
    main()
