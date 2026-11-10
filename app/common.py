import math
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from flask import request, abort, url_for
from .db import query


class BusinessError(ValueError):
    pass


def text(data, key, label, required=False, limit=255):
    value = str(data.get(key, '')).strip()
    if required and not value:
        raise BusinessError(f'{label}不能为空。')
    if len(value) > limit:
        raise BusinessError(f'{label}最多 {limit} 个字符。')
    return value or None


def integer(value, label, minimum=0, maximum=2147483647):
    try:
        result = int(str(value))
    except (ValueError, TypeError):
        raise BusinessError(f'{label}必须是整数。') from None
    if not minimum <= result <= maximum:
        raise BusinessError(f'{label}必须介于 {minimum} 和 {maximum} 之间。')
    return result


def decimal(value, label, maximum=Decimal('999.99'), places=2):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not Decimal(0) <= result <= maximum:
            raise ValueError
        if result != result.quantize(Decimal(10) ** -places):
            raise BusinessError(f'{label}最多 {places} 位小数。')
        return result
    except (InvalidOperation, ValueError, TypeError):
        raise BusinessError(f'{label}须为 0 到 {maximum} 之间的数字。') from None


def iso_date(value, label, required=False):
    if not value and not required:
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError):
        raise BusinessError(f'{label}须为有效日期。') from None


def require_row(sql, args=()):
    row = query(sql, args, one=True)
    if row is None:
        abort(404)
    return row


def page_query(count_sql, data_sql, args=(), per_page=15):
    total = int(query(count_sql, args, one=True)['n'])
    pages = max(1, math.ceil(total / per_page))
    page = request.args.get('page', 1, type=int) or 1
    page = min(max(page, 1), pages)
    rows = query(data_sql + ' LIMIT %s OFFSET %s', (*args, per_page, (page-1)*per_page))
    return rows, dict(total=total, page=page, pages=pages, per_page=per_page)


def page_url(page):
    args = request.args.to_dict()
    args['page'] = page
    return url_for(request.endpoint, **(request.view_args or {}), **args)


def like(value):
    # A literal search: ! escapes SQL LIKE metacharacters, independent of backslash mode.
    return '%' + value.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'


def business_today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()
