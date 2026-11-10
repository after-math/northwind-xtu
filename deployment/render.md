# 十天展示

采用 Render 免费 Web Service + 已申请的腾讯云 MySQL 8.0 免费试用实例。保留 Flask、Jinja2、Bootstrap、PyMySQL 和原始 Northwind 数据，不使用本地文件保存业务数据。腾讯云试用到期时间为 2026-12-10 13:54（北京时间），本次预计展示 10 天，在试用期内。

## 上线记录

公网地址：[https://northwind-xtu-da7s.onrender.com](https://northwind-xtu-da7s.onrender.com)。2026-11-10 16:14（北京时间）上线，参考展示截止为 2026-11-20 16:14，未设置自动下线。实际页面已登录核对，云端 MySQL 的 31 项测试全部通过。

运行数据为 77 件商品、93 位客户、830 笔历史订单及 2,155 条明细，销售总额 1,265,793.0395。云端测试在临时库执行，测试库已清理。备份保存在本机忽略目录中。

账号 `admin`，密码见本机 `instance/cloud-access.txt`，不在源码和压缩包中。发布结果见 [部署记录](../docs/cloud-deployment-results.json)。

## 免费范围

Render 使用 `Free` 实例、新加坡地域、平台分配的 `onrender.com` 地址和 HTTPS。一个实例连续运行 10 天最多约 240 小时，工作区每月有 750 个免费实例小时（所有免费服务共享）。不购买域名、磁盘或付费数据库，不升级计算规格。

免费实例闲置 15 分钟后休眠，重新访问约需一分钟唤醒；流量与构建时间仍受工作区配额限制。Render 休眠时会对 `robots.txt` 返回禁止抓取，因此可直接分享网址，但不能保证 10 天内被搜索引擎收录。[官方免费限制](https://render.com/docs/free)

## 源码与发布

代码放入用户自己的私有 GitHub 仓库，Render 仅获得所需仓库权限。源码不得包含 `.env`、`instance/`、`backups/`、虚拟环境、日志或数据库凭据。

`render.yaml` 已声明免费 Python 服务，使用 `.python-version` 指定 Python 3.14 系列。构建命令 `pip install -r requirements.txt`；启动使用 Gunicorn 单进程、四线程。自动部署关闭，改动后手动发布。健康检查 `/health` 会实际连接 MySQL，只有数据库可连接才应视为整体发布成功。

环境变量：

| 名称 | 内容 |
| --- | --- |
| APP_ENV | production |
| SECRET_KEY | 为云端单独生成的至少 32 位随机值 |
| SESSION_COOKIE_SECURE | true |
| DB_HOST / DB_PORT | 腾讯云实例的实际外网域名与端口 |
| DB_NAME | northwind |
| DB_USER / DB_PASSWORD | 仅具备本库业务权限的应用账号 |
| DB_SSL_CA | certs/tencentdb-ca.pem（官方公开 CA 文件） |
| DB_SSL_MODE | VERIFY_CA（本次腾讯云证书不包含外网域名） |
| PUBLIC_BASE_URL | 通常不填，自动使用 RENDER_EXTERNAL_URL |

应用启动不会导入、清空或重建数据库。

## 数据库连接

Render 无法直接连接腾讯云 `172.16.*` 私网地址。需要启用腾讯云外网地址，在安全组中仅允许 Render 此服务 Connect → Outbound 显示的全部出口网段，以及本机管理来源。目前 Render 出口为 `74.220.52.0/24` 和 `74.220.60.0/24`，属于平台区域共享出口，后续以服务详情为准。不得将 MySQL 对 `0.0.0.0/0` 开放。

取得外网入口和初始化账号后，先检查 MySQL 版本与空库状态，再用 `scripts/init_db.py` 显式导入。已有业务数据时使用一致性备份恢复，避免覆盖。应用账号只授予 `northwind.*` 的 SELECT、INSERT、UPDATE、DELETE、SHOW VIEW；管理员密码独立保存，不公开在首页或仓库。本次已启用腾讯云 SSL。腾讯云服务器证书不包含外网域名，按官方 SSL 说明显式使用 VERIFY_CA：要求 TLS 并验证官方 CA 证书链；不校验外网域名。默认 VERIFY_IDENTITY 模式仍用于支持域名校验的数据库，不会静默回退或关闭证书校验。

## 页面入口

- `/`：公开的项目介绍、校徽与实际界面截图，不查询业务数据库。
- `/login`：管理员登录。
- `/dashboard`：经营仪表盘，其余业务路由同样需要登录。
- `/robots.txt` 与 `/sitemap.xml`：只为介绍首页提供抓取入口；登录、后台和接口均标记不索引。
- `/health`：实际数据库连通检查，不返回连接凭据。

## 上线验证

确认首页与登录页 HTTPS 可访问；未登录不能访问商品、客户和订单数据；登录后核对 77 件商品、93 位客户、830 笔历史订单及 2,155 条明细。云端检查下单、取消与库存恢复后，记录实际公网地址、发布时间、数据库连通状态和截图。未完成这些项目时，不应将“已准备配置”表述为“已上线”。

## 展示结束

10 天结束时，先导出业务数据备份，再停止 Render 服务、关闭数据库外网入口，按用户需要保留或释放试用数据库。删除资源前核对备份；本文不自动删除资源，也不自动续费。使用期限从实际发布成功之日计算。
