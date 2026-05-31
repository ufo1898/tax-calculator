# 5090 全栈部署备份

**日期**: 2026-05-31
**状态**: 正常运行

## 架构

```
用户 → koudai.cool (Cloudflare) → 003 新加坡 (207.148.75.109)
    → nginx HTTPS 443
    → SSH 反向隧道 → 5090 AutoDL
        ├── Open WebUI :6006 (聊天界面)
        ├── server-5090 :6008 (API + 用户积分)
        └── llama-server :8080 (Qwen3.6-35B GGUF)
```

## 服务器

| 服务器 | SSH | 用途 |
|--------|-----|------|
| 5090 AutoDL | `ssh -p 37169 root@connect.westd.seetacloud.com` | GPU 推理 |
| 003 新加坡 | `ssh -i ~/.ssh/id_ed25519 root@207.148.75.109` | 反向代理 |

## 5090 关键配置

- **模型**: Qwen3.6-35B-A3B-Uncensored Q4_K_M (21GB) + mmproj (858MB)
- **GPU**: RTX 5090 32GB, VRAM 使用 ~25GB
- **上下文**: 131072 tokens
- **Open WebUI**: 版本 0.9.5, WEBUI_AUTH=true, ENABLE_SIGNUP=true
- **模型名**: 口袋AI (别名)
- **管理员**: 274889@qq.com

## 003 关键配置

- **nginx**: sites-enabled/koudai.cool (catch-all → 5090:6006, /5090/ → 5090:6008)
- **SSL**: Let's Encrypt (koudai.cool, www.koudai.cool)
- **SSH 隧道**: 5090 → 003 反向隧道 (16006→6006, 16008→6008)
- **UFW**: 22, 80, 443, 8706, 8765, 8766, 6006, 6008

## 恢复步骤

### 如果 5090 挂了:
```bash
# 1. SSH 连接
ssh -p 37169 root@connect.westd.seetacloud.com
# 密码见 CLAUDE.md

# 2. 恢复配置
cp backups/5090/start-all.sh /root/autodl-tmp/
cp backups/5090/start-openwebui.sh /root/autodl-tmp/
cp backups/5090/server-5090.py /root/autodl-tmp/

# 3. 一键启动
bash /root/autodl-tmp/start-all.sh
```

### 如果 003 挂了:
```bash
ssh -i ~/.ssh/id_ed25519 root@207.148.75.109
# 恢复 nginx 配置
cp backups/003/koudai.cool.conf /etc/nginx/sites-enabled/
nginx -t && nginx -s reload
```

## 文件清单

| 文件 | 说明 |
|------|------|
| 5090/start-all.sh | 全栈一键启动 |
| 5090/start-openwebui.sh | Open WebUI 启动 |
| 5090/server-5090.py | API 桥接 + 用户积分系统 |
| 5090/db_schema.json | Open WebUI 数据库结构 |
| 003/koudai.cool.conf | nginx 主站配置 |
| 003/stream.d/taxcalc-tunnel.conf | nginx stream 隧道代理 |
