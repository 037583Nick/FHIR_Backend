import uvicorn
import logging
import os

# Configure Uvicorn logger to be higher than INFO
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Configure logging to include timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式包含时间戳
)

def setup_debug_environment():
    """設置調試環境變數"""
    debug_env_vars = {
        "HAPIFHIR_postgres": "10.69.12.83:8008",
        "FHIR_SERVER_URL": "http://10.69.12.83:8080/fhir",
        "GRPC_SERVER_ADDRESS": "10.69.12.83:8006",
        "MONGO_MAINURI": "10.18.27.131:27017",
        "MONGO_BACKUPURI": "10.65.51.237:27017",
        "mongodb131name": "FHIR",
        "mongodb131coletion": "resources"
    }
    
    for key, value in debug_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"🔧 Debug環境變數: {key} = {value}")

if __name__ == "__main__":
    print("🐛 === Debug Server 模式啟動 ===")
    
    # 設置調試環境
    setup_debug_environment()
    
    print("⚡ 高併發模式 (16 workers)")
    print("📝 詳細日誌輸出")
    print("🔄 自動重載: 啟用")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",  # 修正：正確的應用引用
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        workers=16 if not os.getenv("RELOAD_MODE") else 1,  # reload 模式不能用多 worker
        )
