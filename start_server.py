#!/usr/bin/env python3
"""
FHIR Backend 啟動腳本
用於開發和測試環境
"""

import uvicorn
import os
import sys
from pathlib import Path
import logging

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# ====================================================================
# 新增的日誌配置部分
# ====================================================================

# 自定義過濾器來忽略特定路徑的日誌
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # 🚀 完全阻止所有 /docs 相關請求的日誌，不管狀態碼
        if "/docs" in message or "/health" in message or "/openapi.json" in message or "/redoc" in message:
            return False  # 完全過濾掉所有健康檢查相關的請求
        return True  # 其他請求正常記錄

# 獲取 Uvicorn 默認的日誌配置
LOGGING_CONFIG = uvicorn.config.LOGGING_CONFIG

# 為 uvicorn.access logger 添加自定義過濾器
LOGGING_CONFIG["filters"] = {
    "health_check_filter": {
        "()": __name__ + ".HealthCheckFilter" # 指向當前模塊中的 HealthCheckFilter 類
    }
}
LOGGING_CONFIG["loggers"]["uvicorn.access"]["filters"] = ["health_check_filter"]

# 確保 uvicorn.access 的級別為 INFO，這樣它才能接收到 INFO 級別的請求日誌
# 但因為有過濾器，成功的健康檢查會被過濾
LOGGING_CONFIG["loggers"]["uvicorn.access"]["level"] = "INFO"

# ====================================================================
# 結束日誌配置部分
# ====================================================================

def setup_environment():
    """設置環境變數"""
    env_vars = {
        "HAPIFHIR_postgres": "10.69.12.83:8008",
        "FHIR_SERVER_URL": "http://10.69.12.83:8080/fhir",
        "GRPC_SERVER_ADDRESS": "10.69.12.83:8006",
        "MONGO_MAINURI": "10.65.51.240:27017",
        "MONGO_BACKUPURI": "10.65.51.237:27017",
        "mongodb131name": "FHIR",
        "mongodb131coletion": "resources"
    }
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value

def main():
    """主函數"""
    setup_environment()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 🚀 開啟 reload，檔案變更時自動重載
        log_config=LOGGING_CONFIG # 使用我們上面定義的日誌配置字典
    )

if __name__ == "__main__":
    main()