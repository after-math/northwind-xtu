# 数据库证书

`tencentdb-ca.pem` 来自本次腾讯云 MySQL 实例控制台“数据安全 → SSL → 下载”的官方 CA 压缩包，仅包含公开 CA 证书，不包含私钥。

本次实例的服务器证书没有域名扩展，证书主题为 `TencentDB ROOT SERVER-CA`，不能通过外网域名验证。Render 显式使用腾讯云官方文档支持的 `VERIFY_CA` 模式：必须加密连接并验证 CA 证书链，不校验外网域名。应用账号同时要求 SSL，安全组仅允许已授权来源。

默认配置仍为 `VERIFY_IDENTITY`。更换支持域名校验的数据库后，使用对应 CA 并保持默认模式。更新或关闭/重新开启腾讯云 SSL 后重新核对证书。

[腾讯云 SSL 官方说明](https://cloud.tencent.com/document/product/236/76511)
