#!/usr/bin/env python3
"""
快速資料庫初始化腳本
用於初始化 FHIR Backend 資料庫和預設帳號
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from init_database import DatabaseManager

async def quick_init():
    """快速初始化資料庫"""
    print("=" * 60)
    print("FHIR Backend 快速初始化")
    print("=" * 60)
    
    db_manager = DatabaseManager()
    
    try:
        # 執行完整初始化
        success = await db_manager.init_database()
        
        if success:
            print("\n✅ 初始化成功！")
            print("\n預設管理員帳號:")
            print("  帳號: T37583")
            print("  密碼: T37583")
            print("\n🚀 現在可以啟動服務器:")
            print("  python start_server.py")
        else:
            print("\n❌ 初始化失敗！")
            print("請檢查資料庫連接設定")
            
    except Exception as e:
        print(f"\n❌ 初始化過程中發生錯誤: {e}")
    
    finally:
        await db_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(quick_init())
