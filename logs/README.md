# Logs Directory

此目錄用於存放應用程式和 audit logger 的日誌檔案。

## 日誌輪替設定

- **應用程式日誌**: 最大 20MB，保留 7 個檔案
- **Audit Logger**: 最大 5MB，保留 2 個檔案

## 目錄結構

```
logs/
├── README.md          # 此檔案
├── app/              # 應用程式日誌 (自動建立)
└── audit/            # Audit 日誌 (由 logger 服務建立)
```

## 注意事項

- 此目錄會被 Docker 容器掛載
- 日誌檔案會自動輪替，無需手動清理
- 在 .gitignore 中應排除 *.log 檔案
