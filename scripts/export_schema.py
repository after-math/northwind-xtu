"""Regenerate the course data dictionary from the connected MySQL schema."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.db import query
from config import BASE_DIR


def main():
    lines=['# 数据字典','','依据已导入的 DemoDB Northwind MySQL SQL 与 MySQL 8.0 information_schema 自动生成。原始字段类型、可空性、主外键均保留。','','## 字段说明','','金额使用原始 DECIMAL；折扣原始类型为 DOUBLE，业务金额计算时转为 DECIMAL(10,6)。订单日期原始类型为 TEXT，应用统一写入 ISO 日期字符串。Discontinued 原始类型为 TEXT，0 为在售，1 为停用。','']
    with create_app().app_context():
        tables=query("SELECT TABLE_NAME AS name,ENGINE AS engine,TABLE_COLLATION AS collation FROM information_schema.tables WHERE table_schema=DATABASE() AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
        for table in tables:
            name=table['name']
            rows=query('SELECT COLUMN_NAME AS name,COLUMN_TYPE AS type,IS_NULLABLE AS nullable,COLUMN_KEY AS colkey,COLUMN_DEFAULT AS default_value,EXTRA AS extra FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s ORDER BY ORDINAL_POSITION',(name,))
            fks=query('SELECT COLUMN_NAME AS col,REFERENCED_TABLE_NAME AS target,REFERENCED_COLUMN_NAME AS target_col FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=%s AND REFERENCED_TABLE_NAME IS NOT NULL',(name,))
            fkmap={r['col']:f"{r['target']}.{r['target_col']}" for r in fks}
            lines += [f'## {name}','',f"存储引擎：{table['engine']}；排序规则：{table['collation']}。",'','| 字段 | 实际类型 | 可空 | 键 | 默认值 | 说明 |','| --- | --- | --- | --- | --- | --- |']
            for r in rows:
                key='PK' if r['colkey']=='PRI' else r['colkey']
                if r['name'] in fkmap:
                    key += ' / FK → '+fkmap[r['name']]
                lines.append(f"| {r['name']} | {r['type']} | {r['nullable']} | {key or '—'} | {r['default_value'] if r['default_value'] is not None else 'NULL / 未指定'} | {r['extra'] or '—'} |")
            lines += ['']
        lines += ['## 索引','','| 表 | 索引 | 列顺序 | 唯一 |','| --- | --- | --- | --- |']
        indexes=query('SELECT TABLE_NAME AS t,INDEX_NAME AS name,GROUP_CONCAT(CONCAT(COLUMN_NAME,IF(SUB_PART IS NULL,"",CONCAT("(",SUB_PART,")"))) ORDER BY SEQ_IN_INDEX SEPARATOR ", ") AS cols,NON_UNIQUE AS non_unique FROM information_schema.statistics WHERE table_schema=DATABASE() GROUP BY TABLE_NAME,INDEX_NAME,NON_UNIQUE ORDER BY TABLE_NAME,INDEX_NAME')
        for r in indexes:
            lines.append(f"| {r['t']} | {r['name']} | {r['cols']} | {'否' if r['non_unique'] else '是'} |")
        lines += ['','## 检查约束','','| 表 | 约束名 | 表达式 |','| --- | --- | --- |']
        checks=query('SELECT t.TABLE_NAME AS t,c.CONSTRAINT_NAME AS name,c.CHECK_CLAUSE AS expr FROM information_schema.table_constraints t JOIN information_schema.check_constraints c ON c.CONSTRAINT_SCHEMA=t.CONSTRAINT_SCHEMA AND c.CONSTRAINT_NAME=t.CONSTRAINT_NAME WHERE t.TABLE_SCHEMA=DATABASE() AND t.CONSTRAINT_TYPE="CHECK" ORDER BY t.TABLE_NAME,c.CONSTRAINT_NAME')
        for r in checks:
            lines.append(f"| {r['t']} | {r['name']} | `{r['expr']}` |")
    (BASE_DIR/'docs/数据字典.md').write_text('\n'.join(lines)+'\n')
    print('已生成 docs/数据字典.md。')

if __name__=='__main__':
    main()
