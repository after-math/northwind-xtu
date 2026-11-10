# 本地部署

## 环境

Python 3.11 及以上、MySQL 8.0.16 及以上的 8.0 系列、MySQL 客户端。项目本次实测环境为 Python 3.14.7、MySQL 8.0.46。数据库采用 InnoDB、utf8mb4，数据库名称 `northwind`。浏览器和 Flask 位于本机，应用默认监听 `127.0.0.1:5000`。

项目附带全部数据与静态资源。首次安装依赖和获取 MySQL 镜像需要联网，完成准备后可离线使用。

## 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

将生成的随机值填入 `.env` 的 `SECRET_KEY`，配置数据库账号密码。`.env` 仅保留在本机，权限设置为 `chmod 600 .env`。如果当前工作区已完成初始化，保留现有 `.env`，不用重新复制。

## MySQL 8.0

### 已有本地服务

使用管理员登录 MySQL 后执行下列 SQL；将示例密码改为自己的随机密码。创建应用账号时，host 取实际来源地址。原生本地服务一般为 `localhost`。

```sql
CREATE DATABASE northwind CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'northwind_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, SHOW VIEW ON northwind.* TO 'northwind_app'@'localhost';
```

`.env` 中设置 `DB_HOST=127.0.0.1`、`DB_PORT=3306`、`DB_NAME=northwind`。导入阶段使用有建表、索引、视图权限的数据库管理员，运行阶段使用上述应用账号。

### 隔离容器

当前电脑原有 MySQL 为 8.4，本项目已使用 `compose.yaml` 隔离运行 MySQL 8.0.46，没有修改原有数据库。

在 `.env` 增加随机 `MYSQL_ROOT_PASSWORD`，设置 `DB_PORT=3307`，然后执行：

```bash
docker compose up -d
docker compose ps
```

容器仅映射 `127.0.0.1:3307`。数据保存在 `mysql_data` 卷，正常停止使用 `docker compose stop`，恢复使用 `docker compose start`。不要删除数据卷。镜像初始化时为 `DB_USER` 授予本库权限，完成导入后建议由 root 收敛为上述 DML 与 SHOW VIEW 权限。容器内来源地址由 Docker 网络转发，账号 host 可为 `%`，连接范围由本机端口绑定及 Docker 网络隔离限定。

## 首次导入

目标库必须为空。以下命令交互输入数据库管理员密码，管理员只用于显式导入：

```bash
source .venv/bin/activate
python scripts/init_db.py --user root
```

该脚本先验证 MySQL 8.0，再导入 13 张原始业务表及辅助表，最后执行扩展 SQL。非空数据库会拒绝重复导入。MySQL DDL 会隐式提交；导入中断时先检查 `_demodb_import` 标记和错误，不要继续使用半成品库。保留已有数据，另建空库重新导入并核对后再切换配置。

也可直接使用客户端。数据库已经存在，MySQL 8.0 客户端不需要 8.4 特有的 `--skip-commands` 参数：

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 northwind < data/northwind.mysql.sql
mysql -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 northwind < sql/extensions.sql
```

容器方案将端口换成 3307。已有数据只应用扩展时：

```bash
python scripts/init_db.py --extensions-only --user root
```

应用启动只建立按需连接，始终不会自动导入、清库或重放历史订单。

## 管理员与启动

```bash
python scripts/init_admin.py --username admin
python app.py
```

浏览器访问 [本地登录页](http://127.0.0.1:5000)。管理员密码至少 12 位，通过 Werkzeug scrypt 哈希保存。重置已有账号使用 `python scripts/init_admin.py --username admin --reset`，不会改变业务数据。

当前工作区已初始化的随机管理员密码保存在 `instance/local-admin.txt`，该文件和 `.env` 均被版本控制排除。部署到云端时重新创建管理员，避免复制本地凭据。

## 核对

```sql
SELECT VERSION();
SELECT * FROM _demodb_import;
SELECT COUNT(*) FROM Products;
SELECT COUNT(*) FROM Customers;
SELECT COUNT(*) FROM Orders;
SELECT COUNT(*) FROM `Order Details`;
SELECT MIN(OrderDate), MAX(OrderDate) FROM Orders;
SELECT SUM(SalesAmount) FROM v_order_amounts;
```

原始快照应为 77、93、830、2,155；日期为 2016-07-04 至 2018-05-06；不含运费的折后销售额为 1,265,793.0395。界面显示两位小数 1,265,793.04。新增业务记录后，行数和统计随之变化。

## 测试

```bash
python -m pip install -r requirements-dev.txt
RUN_MYSQL_TESTS=1 python -m pytest -q
```

测试使用单独创建的 `northwind_test_随机后缀` 空数据库，导入同一份原始 SQL，结束后删除该临时库。默认通过 `.env` 的 `MYSQL_ROOT_PASSWORD` 取得本地容器管理员密码；其他环境通过 `TEST_DB_ADMIN_USER`、`TEST_DB_ADMIN_PASSWORD` 配置有临时建库权限的测试账号。不要使用生产管理员执行测试。

## 备份恢复

一致性备份包含原表、扩展表、视图及数据，使用 MySQL 客户端 `mysqldump`：

```bash
python scripts/backup_db.py
```

备份落在被忽略的 `backups/` 目录，文件权限 600。脚本使用 `--single-transaction --no-tablespaces --set-gtid-purged=OFF`，不在命令行参数中放密码。定期复制到受控存储并验证恢复。备份期间避免执行 DDL。

恢复首先创建独立空库，使用具有 DDL 权限的维护账号导入；检查行数、视图和销售总额后，在维护窗口切换 `DB_NAME`。示例：

```sql
CREATE DATABASE northwind_restore CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p northwind_restore < backups/northwind-YYYYmmdd-HHMMSS.sql
```

备份脚本会移除本项目 INVOKER 视图的 DEFINER 指令，使目标维护账号可以重建视图而无需保留原账号。使用其他工具产生的备份时，先审核 DEFINER；必要时由云端维护账号重建 `sql/extensions.sql` 中的视图。账号授权不属于库级备份，需按目标环境重新设置。
