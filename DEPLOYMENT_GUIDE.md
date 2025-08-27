# 統一 Nginx 部署指引

## 目錄結構
```
/home/aicenter/docker_server/
├── nginx/
│   ├── docker-compose.yml         # Nginx 服務配置
│   └── nginx.conf                 # 統一路由配置
└── FHIR-AI-Backend/
    ├── docker-compose.yml         # 後端服務配置（不含 Nginx）
    └── logs/                      # 應用日誌
```

## 部署步驟

### 1. 設置統一 Nginx
```bash
# 在服務器上創建目錄
sudo mkdir -p /home/aicenter/docker_server/nginx

# 複製配置檔案
sudo cp unified-nginx.conf /home/aicenter/docker_server/nginx/nginx.conf
sudo cp unified-nginx-docker-compose.yml /home/aicenter/docker_server/nginx/docker-compose.yml

# 啟動統一 Nginx
cd /home/aicenter/docker_server/nginx
sudo docker-compose up -d
```

### 2. 部署 FHIR 專案
```bash
# 確保 FHIR 專案已移除內部 Nginx
cd /home/aicenter/docker_server/FHIR-AI-Backend
sudo docker-compose down  # 停止舊版本
sudo docker-compose up -d  # 啟動新版本（只有後端）
```

### 3. 驗證部署
```bash
# 檢查服務狀態
sudo docker ps

# 測試訪問
curl http://localhost/health
curl http://localhost/api/STEMI/test
```

## 管理命令

### 查看 Nginx 日誌
```bash
cd /home/aicenter/docker_server/nginx
sudo docker-compose logs -f nginx
```

### 重載 Nginx 配置
```bash
cd /home/aicenter/docker_server/nginx
sudo docker-compose exec nginx nginx -s reload
```

### 添加新專案
1. 在 nginx.conf 中添加新的 upstream
2. 添加新的 location 規則
3. 重載配置

## 優勢
- ✅ 統一管理所有路由
- ✅ 減少資源使用
- ✅ 簡化 SSL 配置
- ✅ 統一日誌管理
- ✅ 更好的負載均衡
