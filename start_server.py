#!/usr/bin/env python3
"""
FHIR Backend 啟動腳本
用於開發和測試環境
"""

import uvicorn
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """設置環境變數"""
    # 設置預設的環境變數（如果沒有設置的話）
    env_vars = {
        "HAPIFHIR_postgres": "10.69.12.83:8008",  # 您的 FHIR 資料庫
        "FHIR_SERVER_URL": "http://10.69.12.83:8080/fhir",  # 您的 FHIR 伺服器（修正）
        "GRPC_SERVER_ADDRESS": "10.69.12.83:8006",  # 您的 gRPC 推論伺服器
        "MONGO_MAINURI": "10.65.51.240:27017",  # MongoDB 主要
        "MONGO_BACKUPURI": "10.65.51.237:27017",  # MongoDB 備援
        "mongodb131name": "FHIR",
        "mongodb131coletion": "resources"
    }
    
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            print(f"設置環境變數: {key} = {default_value}")

def main():
    """主函數"""
    print("=" * 50)
    print("FHIR Backend 啟動中...")
    print("=" * 50)
    
    # 設置環境變數
    setup_environment()
    
    # 啟動 FastAPI 應用
    # print("\n啟動 Web 服務器...")
    # print("API 文檔: http://localhost:8000/docs")
    # print("登入測試: http://localhost:8000/login")
    # print("按 Ctrl+C 停止服務器\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 開發模式，檔案變更時自動重載
        log_level="info"
    )

if __name__ == "__main__":
    main()
