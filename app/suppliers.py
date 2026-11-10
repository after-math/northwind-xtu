from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import query, execute, transaction
from .common import BusinessError, text, require_row, page_query, like

bp = Blueprint('suppliers', __name__, url_prefix='/partners')
KINDS = {
    'categories': dict(table='Categories', pk='CategoryID', title='商品分类', fields=(('CategoryName','分类名称'),('Description','描述'))),
    'suppliers': dict(table='Suppliers', pk='SupplierID', title='供应商', fields=(('CompanyName','公司名称'),('ContactName','联系人'),('ContactTitle','职务'),('Address','地址'),('City','城市'),('Region','地区'),('PostalCode','邮编'),('Country','国家'),('Phone','电话'),('Fax','传真'),('HomePage','主页')))
}


def kind_config(kind):
    if kind not in KINDS:
        from flask import abort
        abort(404)
    return KINDS[kind]


@bp.get('/<kind>')
def index(kind):
    cfg = kind_config(kind)
    search = request.args.get('q','').strip()
    first = cfg['fields'][0][0]
    where = f" WHERE t.{first} LIKE %s ESCAPE '!'" if search else ''
    args = (like(search),) if search else ()
    rows, pager = page_query(f"SELECT COUNT(*) AS n FROM {cfg['table']} t"+where,
        f"SELECT t.*,(SELECT COUNT(*) FROM Products p WHERE p.{cfg['pk']}=t.{cfg['pk']}) AS product_count FROM {cfg['table']} t"+where+f" ORDER BY t.{cfg['pk']}",args)
    return render_template('suppliers/index.html', kind=kind, cfg=cfg, rows=rows, pager=pager)


@bp.route('/<kind>/new',methods=['GET','POST'])
@bp.route('/<kind>/<int:record_id>/edit',methods=['GET','POST'])
def edit(kind,record_id=None):
    cfg = kind_config(kind)
    row = require_row(f"SELECT * FROM {cfg['table']} WHERE {cfg['pk']}=%s", (record_id,)) if record_id else {}
    error = None
    if request.method=='POST':
        try:
            data = [text(request.form,field,label,required=index==0,limit=2000 if field=='Description' else 255) for index,(field,label) in enumerate(cfg['fields'])]
            fields = [field for field,label in cfg['fields']]
            with transaction():
                if record_id:
                    execute(f"UPDATE {cfg['table']} SET "+','.join(f'{field}=%s' for field in fields)+f" WHERE {cfg['pk']}=%s", (*data,record_id))
                else:
                    execute(f"INSERT INTO {cfg['table']} ("+','.join(fields)+') VALUES ('+','.join(['%s']*len(fields))+')',data)
            flash(f"{cfg['title']}已保存。",'success')
            return redirect(url_for('suppliers.index',kind=kind))
        except BusinessError as exc:
            error,row = str(exc),request.form.to_dict()
    return render_template('suppliers/form.html',kind=kind,cfg=cfg,row=row,record_id=record_id,error=error), (400 if error else 200)


@bp.post('/<kind>/<int:record_id>/delete')
def delete(kind,record_id):
    cfg = kind_config(kind)
    with transaction():
        require_row(f"SELECT {cfg['pk']} FROM {cfg['table']} WHERE {cfg['pk']}=%s FOR UPDATE", (record_id,))
        if query(f"SELECT 1 FROM Products WHERE {cfg['pk']}=%s LIMIT 1",(record_id,),one=True):
            raise BusinessError(f"{cfg['title']}已被商品引用，不能删除。")
        execute(f"DELETE FROM {cfg['table']} WHERE {cfg['pk']}=%s", (record_id,))
    flash('记录已删除。','success')
    return redirect(url_for('suppliers.index',kind=kind))
