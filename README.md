# SimonDPhotograph

SimonDPhotograph 的公开前台网站源码。

![SimonDPhotograph Preview](./thumbs/DSC_0399.JPG)

当前 GitHub 仓库只保留公开前台部分：

- 首页：`https://simond.photo/`
- 摄影作品页：`https://simond.photo/cheungchau.html`

服务器上的后台页面、API 和部署配置继续正常运行，但不放在这个公开仓库里。

## 目录说明

- `index.html`
  - 首页
- `cheungchau.html`
  - 长洲摄影作品页
- `cheungchaw/`
  - 原图目录
- `thumbs/`
  - 缩略图目录
- `vendor/leaflet/`
  - 地图前端依赖

## 本地开发

如果只需要改公开前台页面，直接编辑这些文件即可：

- `index.html`
- `cheungchau.html`

## 部署说明

当前线上站点：

- SSH Host: `Tokyo`
- Domain: `simond.photo`

### 常用文件上传

```powershell
scp .\index.html Tokyo:/var/www/html/index.html
scp .\cheungchau.html Tokyo:/var/www/html/cheungchau.html
```

### 上传静态资源

```powershell
scp -r .\thumbs Tokyo:/var/www/html/
scp -r .\cheungchaw Tokyo:/var/www/html/
scp -r .\vendor Tokyo:/var/www/html/
```

### 检查线上状态

```powershell
ssh Tokyo "curl -I -s https://simond.photo/"
ssh Tokyo "curl -I -s https://simond.photo/cheungchau.html"
```

### 典型发布流程

```powershell
git status
git add .
git commit -m "your message"
git push

scp .\index.html Tokyo:/var/www/html/index.html
scp .\cheungchau.html Tokyo:/var/www/html/cheungchau.html
```

## Git 工作流

```powershell
git status
git add .
git commit -m "your message"
git push
```

当前默认分支：

- `main`

## 备注

- `backups/` 不纳入 Git 版本库
- 后台页面、API 与服务器部署文件不纳入这个公开 GitHub 仓库
- `remote-*.conf` 为临时远端配置副本，不纳入 Git 版本库
- 当前仓库地址：`https://github.com/SimonD0711/simond-photo.git`

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE).
