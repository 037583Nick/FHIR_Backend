# FHIR Backend - AI 醫療診斷系統

[![CI/CD](https://github.com/037583Nick/FHIR_Backend/workflows/FHIR%20Backend%20CI/CD/badge.svg)](https://github.com/037583Nick/FHIR_Backend/actions)

這是一個基於 FastAPI 的 FHIR 後端系統，專門用於 AI 輔助心電圖 STEMI 診斷。

## 🚀 功能特色

- **STEMI 診斷**: AI 輔助心肌梗塞診斷
- **心律不整檢測**: 支援 13 種常見心律不整
- **FHIR 標準**: 完全符合 FHIR R4 標準
- **JWT 認證**: 安全的用戶認證系統
- **Docker 化**: 完整的容器化部署

## 🏗️ 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │───▶│  FHIR Backend   │───▶│  gRPC AI Server │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   FHIR Server   │
                       │   + Database    │
                       └─────────────────┘
```

## 📋 系統需求

- Python 3.10+
- Docker & Docker Compose
- PostgreSQL (外部)
- MongoDB (外部)
- gRPC AI 推論伺服器

## 快速開始

### 1. 複製專案

```bash
git clone git@github.com:037583Nick/FHIR_Backend.git
cd FHIR_Backend
```

### 2. 環境設定

```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯環境變數
nano .env
```

### 3. Docker 部署

#### 🐛 開發/Debug 模式 (推薦開發使用)
```bash
# 使用有 build 功能的版本，適合開發和調試
docker-compose -f docker-compose.fhir.yml up -d

# 特色：
# - 自動 build Docker 映像
# - 使用 debugServer.py (16 workers, 詳細日誌)
# - Volume 掛載，支援即時程式碼修改
# - 自動重載功能
```

#### 🚀 生產模式
```bash
# 使用預建映像版本，適合生產環境
docker-compose up -d

# 特色：
# - 使用預先建置的 Docker 映像
# - 使用 start_server.py (穩定模式)
# - 最佳化的生產配置
```

#### 🔧 自定義模式
```bash
# 使用範本模式，完全可配置
docker-compose -f docker-compose.template.yml up -d

# 可透過 .env 檔案自定義所有參數
```

### 4. 本地開發

#### 安裝依賴

```bash
pip install -r requirements_basic.txt
```

#### 啟動服務器 - 兩種模式選擇

##### 🌟 start_server.py (推薦)
```bash
# 友善介面，自動環境設置，適合日常開發
python start_server.py
```

##### 🐛 debugServer.py (高併發測試)
```bash
# 高併發模式，詳細日誌，適合效能測試
python debugServer.py
```

服務器將在 `http://localhost:8000` 啟動

### 5. 初始化資料庫

```bash
# 快速初始化 (推薦)
python quick_init.py

# 或使用互動式管理工具
python init_database.py
```

### 6. 測試登入功能

```bash
python test_login.py
```

## 🎯 啟動腳本詳細說明

### `start_server.py` - 通用啟動腳本 ⭐
- **用途**: 日常開發和生產環境
- **特色**: 
  - ✅ 友善的啟動訊息和 API 文檔連結
  - ✅ 自動設置環境變數預設值
  - ✅ 適合新手和生產環境
  - ✅ 單進程模式，穩定可靠
- **適用場景**: 本地開發、生產部署、初學者使用

### `debugServer.py` - Debug 專用腳本 🐛
- **用途**: 調試和高併發測試
- **特色**:
  - ⚡ 16 workers 高併發模式
  - 📝 自定義日誌格式，包含時間戳
  - 🔧 調整 uvicorn 日誌級別為 WARNING
  - 🔄 支援自動重載 (reload=True)
  - 🐳 適合 Docker 容器化部署
- **適用場景**: 效能測試、Docker 部署、Debug 調試

### Docker Compose 檔案對應關係

| 檔案 | 啟動腳本 | 埠號 | 用途 |
|------|----------|------|------|
| `docker-compose.fhir.yml` | `debugServer.py` | 8010/8011 | 🐛 開發+Build模式 |
| `docker-compose.yml` | `start_server.py` | 8010/8011 | 🚀 生產模式 |
| `docker-compose.template.yml` | 可配置 | 可配置 | 🔧 自定義模式 |

### 選擇建議

- **初學者/日常開發**: 使用 `start_server.py`
- **效能測試/Docker**: 使用 `debugServer.py`  
- **生產環境**: 使用 Docker Compose 生產模式
- **客製化需求**: 使用 template 版本

## 資料庫設定

預設資料庫設定：
- **主機**: 10.69.12.83
- **端口**: 8008  
- **帳號**: aicenter
- **密碼**: 1234qwer
- **資料庫**: hapifhir

### 資料表結構

系統會自動創建以下三張資料表：

1. **Account** - 用戶帳號表
   - id (主鍵)
   - username (用戶名)
   - password (密碼雜湊)
   - note (備註)
   - phone (電話)
   - enable (是否啟用)

2. **Resources** - FHIR 資源記錄表
   - res_id (主鍵)
   - res_type (資源類型)
   - user (用戶)
   - requester (請求者)
   - model (模型名稱)
   - status (狀態)
   - result (結果 JSON)
   - create_time (創建時間)
   - update_time (更新時間)
   - self_id (自身ID)

3. **hospital_info** - 醫院資訊表
   - id (主鍵)
   - hosp_id (醫院代碼)
   - hosp_name (醫院名稱)
   - create_time (創建時間)

## API 端點

### 認證相關
- `POST /login` - 用戶登入
- `POST /createUser` - 創建新用戶
- `POST /changePassword` - 修改密碼

### 管理功能
- `GET /admin/users` - 列出所有用戶
- `POST /admin/create-user` - 創建用戶 (管理員)
- `PUT /admin/users/{user_id}` - 更新用戶
- `DELETE /admin/users/{user_id}` - 刪除用戶
- `POST /admin/change-my-password` - 修改密碼

### STEMI 診斷
- `POST /STEMI/` - STEMI 診斷推論
- `GET /STEMI/{id}/` - 獲取診斷報告
- `GET /STEMI/ActivityDefinition/` - 獲取活動定義

## 預設帳號

系統會自動創建管理員帳號：
- **用戶名**: `admin`
- **密碼**: `admin123`

## API 文檔

服務器啟動後，可以訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 環境變數設定

### 核心環境變數

| 變數名稱 | 描述 | 預設值 | 必要性 |
|---------|------|--------|--------|
| `FHIR_SERVER_URL` | FHIR 伺服器位址 | `http://10.69.12.83:8080/` | ✅ 必要 |
| `GRPC_SERVER_ADDRESS` | AI 推論伺服器位址 | `10.21.98.80:8001` | ✅ 必要 |
| `HAPIFHIR_postgres` | PostgreSQL 資料庫 | `10.69.12.83:8008` | ✅ 必要 |
| `MONGO_MAINURI` | MongoDB 主要伺服器 | `10.65.51.240:27017` | ✅ 必要 |
| `MONGO_BACKUPURI` | MongoDB 備援伺服器 | `10.65.51.237:27017` | 🔶 建議 |

### 系統環境變數

| 變數名稱 | 描述 | 預設值 |
|---------|------|--------|
| `PYTHONUNBUFFERED` | Python 緩衝設定 | `1` |
| `TZ` | 時區設定 | `Asia/Taipei` |

### Docker 專用環境變數

| 變數名稱 | 描述 | 預設值 |
|---------|------|--------|
| `DOCKER_IMAGE` | Docker 映像名稱 | `10.18.27.131:17180/fhir/ai-fhir-backend:v2.1.3` |
| `APP_PORT` | 應用程式埠號 | `8010` |
| `NGINX_PORT` | Nginx 埠號 | `8011` |
| `LOGGER_IMAGE` | Audit Logger 映像 | `10.18.27.131:17180/aic/audit-logger:v1.0.0` |

### 環境設定範例

```bash
# PostgreSQL 資料庫 (FHIR 後端)
export HAPIFHIR_postgres="10.69.12.83:8008"

# FHIR 伺服器
export FHIR_SERVER_URL="http://10.69.12.83:8080/"

# AI 推論伺服器 (新增)
export GRPC_SERVER_ADDRESS="10.21.98.80:8001"

# MongoDB (主要)
export MONGO_MAINURI="10.65.51.240:27017"

# MongoDB (備援)  
export MONGO_BACKUPURI="10.65.51.237:27017"
```

## 資料庫管理

### 互動式管理工具

```bash
python init_database.py
```

提供以下功能：
1. 初始化資料庫
2. 創建新用戶
3. 列出所有用戶  
4. 新增醫院資訊
5. 列出所有醫院

### 快速初始化

```bash
python quick_init.py
```

自動完成資料庫和預設帳號的初始化。

## 📝 日誌管理

### Docker 日誌配置

系統包含完整的日誌管理機制：

#### 應用程式日誌
- **大小限制**: 20MB 每檔案
- **保留檔案**: 7 個
- **驅動**: json-file
- **自動輪替**: 是

#### Audit Logger 日誌
- **服務**: `10.18.27.131:17180/aic/audit-logger:v1.0.0`
- **大小限制**: 5MB 每檔案
- **保留檔案**: 2 個
- **掛載路徑**: `./logs:/var/log/minio-audit`

#### 日誌查看

```bash
# 查看應用程式日誌
docker-compose logs -f app

# 查看 nginx 日誌
docker-compose logs -f nginx

# 查看 audit logger 日誌
docker-compose logs -f logger

# 查看所有服務日誌
docker-compose logs -f
```

#### 本地日誌目錄
```
logs/
├── README.md          # 日誌說明
├── app/              # 應用程式日誌 (自動建立)
└── audit/            # Audit 日誌 (由 logger 服務建立)
```

## 開發說明

### 專案結構

```
app/
├── main.py              # FastAPI 主應用
├── models.py            # 資料庫模型
├── JWT.py               # JWT 認證
├── fhir_processor.py    # FHIR 處理
├── routers/
│   ├── STEMI.py         # STEMI API 路由
│   └── admin.py         # 管理功能 API
├── inference/
│   ├── __init__.py
│   └── stemi.py         # STEMI 推論邏輯
├── AI/
│   ├── __init__.py
│   ├── base.py          # AI 基礎類
│   ├── ECG_all.py       # ECG 整合處理
│   ├── ECG_STEMI.py     # STEMI 專用處理
│   ├── ECG.py           # 基本 ECG 處理
│   └── ECG_QT.py        # QT 間期處理
├── emptyDR/
│   └── stemi.dr.json    # STEMI DiagnosticReport 模板
└── emptyOBS/
    └── stemi.obs.json   # STEMI Observation 模板
```

### 注意事項

1. **AI 模型推論**: 需要 TensorRT 推理服務器運行，否則 AI 功能會報錯
2. **資料庫**: 會自動創建 PostgreSQL 資料表
3. **FHIR 伺服器**: 需要外部 FHIR 伺服器運行
4. **MongoDB**: 用於存儲 FHIR 資源

## 故障排除

### 1. 無法連接資料庫
檢查 PostgreSQL 是否運行，並確認連接字串正確。

### 2. AI 推論失敗
檢查 TensorRT 推理服務器是否運行在正確的地址。

### 3. FHIR 操作失敗
檢查 FHIR 伺服器是否可訪問。
