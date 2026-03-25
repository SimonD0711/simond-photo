# SimonDPhotograph

SimonDPhotograph 的网站源码与部署文件。

当前包含：

- 首页：`https://simond.photo/`
- 摄影作品页：`https://simond.photo/cheungchau.html`
- 站主统计页：`https://simond.photo/admin-stats.html`
- 摄影站 API：`https://simond.photo/api/...`
- Gemini 子站反代相关配置

## 目录说明

- `index.html`
  - 首页
- `cheungchau.html`
  - 长洲摄影作品页
- `admin-stats.html`
  - 站主专用统计页
- `api_server.py`
  - 点赞、评论、站主登录、统计、地图代理等接口
- `cheungchau-api.service`
  - systemd 服务配置
- `nginx-default.conf`
  - Nginx 站点配置
- `cheungchaw/`
  - 原图目录
- `thumbs/`
  - 缩略图目录
- `vendor/leaflet/`
  - 地图前端依赖

## 站主功能

站主权限现已统一到 `simond.photo` 根域名下，主要接口包括：

- `/api/admin/status`
- `/api/admin/login`
- `/api/admin/logout`
- `/api/admin/stats`
- `/api/admin/server-status`

站主登录后可在首页、作品页和统计页共用登录状态。

## 部署说明

当前线上服务器：

- Host: `Tokyo`
- Domain: `simond.photo`

常用部署方式：

```powershell
scp .\index.html Tokyo:/var/www/html/index.html
scp .\cheungchau.html Tokyo:/var/www/html/cheungchau.html
scp .\admin-stats.html Tokyo:/var/www/html/admin-stats.html
scp .\api_server.py Tokyo:/var/www/html/api_server.py
ssh Tokyo "systemctl restart cheungchau-api"
```

## Git 工作流

```powershell
git status
git add .
git commit -m "your message"
git push
```

## 备注

- `backups/` 不纳入 Git 版本库
- `remote-*.conf` 为临时远端配置副本，不纳入 Git 版本库
