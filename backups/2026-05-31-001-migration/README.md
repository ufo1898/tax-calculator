# 001 香港迁移备份

**日期**: 2026-05-31
**变更**: 代理从 003 新加坡迁移到 001 香港

## 架构

```
用户 → Cloudflare → 001 香港 (47.83.156.11)
    → aa_nginx :443
    → SSH 反向隧道 → 5090 AutoDL
        ├── Open WebUI :6006 (口袋AI)
        ├── server-5090 :6008 (API)
        └── llama-server :8080 (Qwen 推理)
```

## 关键改动

| 项目 | 之前 | 之后 |
|------|------|------|
| 代理 | 003 新加坡 | **001 香港** |
| 延迟 | 2-3s | **1-1.5s** |
| DNS | 207.148.75.109 | **47.83.156.11** (Cloudflare代理) |
| nginx | 标准 /etc/nginx | **aa_nginx** (/etc/aa_nginx) |
| SSL | Let's Encrypt | 从003复制的真实证书 |

## 恢复步骤

### 5090 挂了的恢复
1. SSH: `ssh -p 37169 root@connect.westd.seetacloud.com`
2. `bash /root/autodl-tmp/start-llama.sh` (先启 llama)
3. 等30秒 GPU 加载
4. `bash /root/autodl-tmp/start-all.sh` (启 OWUI)

### 001 挂了的恢复
1. SSH: `ssh -i ~/.ssh/id_ed25519 root@47.83.156.11`
2. 恢复 `/etc/aa_nginx/conf.d/koudai.cool.conf` 
3. `nginx -t && pkill -HUP nginx`

### SSH 隧道重建 (5090→001)
```bash
# 在 5090 上执行
ssh -f -N -T -o StrictHostKeyChecking=no     -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes     -R 127.0.0.1:16006:127.0.0.1:6006     -R 127.0.0.1:16008:127.0.0.1:6008     root@47.83.156.11
```

## 003 备份
003 (207.148.75.109) 所有配置保留，可随时切回。
