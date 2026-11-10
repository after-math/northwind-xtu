# Northwind 商务管理

基于 Flask 与 MySQL 的商品销售及订单管理系统，用于《数据库原理与技术》课程设计。采用 Flask Blueprint、PyMySQL、Jinja2、Bootstrap 5、ECharts，保留完整 Northwind 真实历史数据。本地 MySQL 8.0 应用已验证；腾讯云免费数据库已申请，正在准备 Render 免费公开展示。云端发布状态见部署记录。

## 当前工作区

已准备 Python 虚拟环境、隔离的 MySQL **8.0.46**（本机端口 **3307**）、完整数据库、随机管理员和本地静态资源。未修改电脑原有 MySQL 8.4。数据为 77 件商品、93 位客户、830 笔订单、2,155 条明细，历史日期为 2016-07-04 至 2018-05-06。

双击项目根目录的 `启动系统.command`，或在此目录执行：

```bash
docker compose up -d
source .venv/bin/activate
python app.py
```

访问 [项目介绍](http://127.0.0.1:5000) 或 [管理工作台](http://127.0.0.1:5000/dashboard)。账号 `admin`，本次随机密码见 `instance/local-admin.txt`。可以用 `python scripts/init_admin.py --username admin --reset` 设置自己的密码。停止 Flask 使用终端 Ctrl+C；停止项目数据库使用 `docker compose stop`。

## 全新环境

需要 Python 3.11+ 和 MySQL **8.0.16+ 的 8.0 系列**。首次安装依赖、获取 MySQL 镜像需要网络；准备完成后系统可离线使用。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

将随机值填入 `.env` 的 `SECRET_KEY`，配置数据库连接。创建 utf8mb4 的空数据库 `northwind`，再执行：

```bash
python scripts/init_db.py --user 数据库维护账号
python scripts/init_admin.py --username admin
python app.py
```

导入脚本要求空库和 MySQL 8.0，应用启动不会导入或清空数据。容器方案和最小权限配置见 [本地部署](deployment/local.md)。

## 界面

已按湘潭大学课程项目重新设计登录、仪表盘、商品与订单页面，加入用户提供的校徽，统一藏青配色、字体、表格、按钮和表单。支持手机端导航、密码显隐与减少动画设置，校徽和全部样式资源均保存在本地。

[设计说明](docs/界面设计.md) · [登录页](docs/screenshots/01-login.png) · [仪表盘](docs/screenshots/02-dashboard.png) · [手机端](docs/screenshots/12-mobile-dashboard.png)

## 功能

- 管理员登录、退出、哈希密码、Session、CSRF。
- 仪表盘：商品/客户/有效订单/累计销售额、趋势、分类分布、近期订单、库存预警。
- 商品：新增、编辑、删除、名称搜索、分类与供应商筛选、库存校验、历史关联商品停用。
- 客户：新增、编辑、删除保护、名称与国家筛选、客户订单与有效累计消费。
- 订单：分页、编号/客户/日期/状态筛选、明细、运费、多商品下单、取消与库存恢复。
- 基础资料：分类与供应商增改查删、商品关联查看、引用保护。
- 报表：日期筛选、月度销售额、分类销售、商品销售额与销量排行、客户消费排名、当前库存预警。
- 教学：15 组 SQL 示例（覆盖 13 类操作）、视图、索引和实际 EXPLAIN 结果。

订单服务使用显式事务、固定顺序行锁和 Decimal；仅本系统 active 订单允许取消，历史库存保留原始快照。销售金额为成交单价 × 数量 × (1 − 折扣)，排除取消订单，运费单列。价格最大 999.99、运费最大 9999.99，依据原始 DECIMAL 字段。

## 验证

已在真实 MySQL 8.0.46 上通过 31 项测试，涵盖 CRUD、权限与 CSRF、库存不足、并发下单、并发取消和中途失败回滚。已验证逻辑备份恢复，已保存实际界面截图。

```bash
python -m pip install -r requirements-dev.txt
RUN_MYSQL_TESTS=1 python -m pytest -q
```

测试单独创建并清理随机后缀临时库。测试账号需要临时建库权限；默认读取本地容器的 `MYSQL_ROOT_PASSWORD`，亦可设置 `TEST_DB_ADMIN_USER`、`TEST_DB_ADMIN_PASSWORD`。详见 [测试用例](docs/测试用例.md)。

## 腾讯云

已申请腾讯云 MySQL 8.0 免费试用实例。本次 10 天展示使用 [Render 免费部署](deployment/render.md)。长期使用可按 [腾讯云部署](deployment/cloud.md) 配置同地域、同 VPC 的 CVM + 云数据库 MySQL 8.0。仅修改 `.env` 中的地址、端口、账号及可选 CA 证书路径，业务代码共用。应用仍在本机时可通过 SSH 隧道访问云库。

已提供 Gunicorn/systemd 与 Nginx 配置。数据库仅允许授权来源，外部入口使用 HTTPS。账号和密码留在 `.env`，不写进源码、报告或截图。原始数据导入与后续业务数据迁移步骤分别说明，避免覆盖已有记录。

## 文件

```text
app.py / config.py / wsgi.py   应用入口及配置
app/                          Blueprint、服务、模板、本地静态资源
data/                         原始 SQL、许可、校验清单
sql/                          幂等扩展、视图、教学 SQL
scripts/                      导入、管理员、备份、数据字典导出
compose.yaml                  可选本地 MySQL 8.0
deployment/                   本地与腾讯云步骤、systemd、Nginx
docs/                         报告、E-R 图、字典、测试、实际截图
tests/                        真实 MySQL 核心集成测试
```

[实验报告](docs/实验报告.md) · [E-R 图](docs/ER图.md) · [数据字典](docs/数据字典.md) · [索引分析](docs/索引分析.md) · [截图清单](docs/截图清单.md)

数据库业务日期及连接会话采用北京时间（Asia/Shanghai / UTC+8）。静态文件已保存在 `app/static/vendor`，运行不依赖 CDN。数据来源与完整 MIT 归属保留在 [数据说明](data/数据来源与许可说明.md) 及原始 SQL 头部。
