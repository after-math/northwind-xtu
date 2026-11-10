from datetime import date,timedelta
from flask import Blueprint,render_template,request
from .common import BusinessError,iso_date
from .services.analytics import sales_data,stock_alerts

bp = Blueprint('reports',__name__,url_prefix='/reports')


@bp.get('/')
def index():
    start=iso_date(request.args.get('start'),'起始日期')
    end=iso_date(request.args.get('end'),'结束日期')
    if start and end and start>end:
        raise BusinessError('起始日期不能晚于结束日期。')
    if end and end>='9999-12-31':
        raise BusinessError('结束日期超出支持范围。')
    exclusive_end=(date.fromisoformat(end)+timedelta(days=1)).isoformat() if end else None
    charts=sales_data(start,exclusive_end)
    return render_template('reports/index.html',charts=charts,alerts=stock_alerts())
