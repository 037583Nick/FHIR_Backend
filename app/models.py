from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, Session, select, JSON, Column, Integer
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, Dict, AsyncGenerator
from sqlmodel import SQLModel, Field
import pymongo
import pandas as pd
from datetime import datetime
import json
import os
import logging
from pymongo import MongoClient, errors

# PostgreSQL 資料庫連接設定
HAPIFHIR_IP = os.environ.get("HAPIFHIR_postgres", "10.69.12.83:8008")
sqlite_url = f"postgresql+asyncpg://aicenter:1234qwer@{HAPIFHIR_IP}/hapifhir"

# MongoDB 連線設定
MONGO_MAINURI = os.environ.get("MONGO_MAINURI", "10.65.51.240:27017")
MONGO_BACKUPURI = os.environ.get("MONGO_BACKUPURI", "10.65.51.237:27017")
MONGO_DATABASE = os.environ.get("mongodb131name", "FHIR")
MONGO_COLLECTION = os.environ.get("mongodb131coletion", "resources")

# 創建資料庫引擎
base_engine = create_async_engine(
    sqlite_url,
    json_serializer=lambda x: json.dumps(x, ensure_ascii=False),
)

# 資料庫會話生成器
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(base_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

# ===== 資料庫模型 =====

class Account(SQLModel, table=True):
    """用戶帳號表"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    note: Optional[str]
    phone: Optional[str]
    enable: Optional[bool] = Field(default=False)

class Resources(SQLModel, table=True):
    """FHIR 資源記錄表"""
    res_id: int = Field(primary_key=True)
    res_type: str
    user: str
    requester: str
    model: str
    status: str
    result: Optional[Dict] = Field(sa_column=Column(JSON))
    create_time: datetime
    update_time: Optional[datetime]
    self_id: int 

class hospital_info(SQLModel, table=True):
    """醫院資訊表"""
    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    hosp_id: str
    hosp_name: str
    create_time: datetime

# ===== 工具函數 =====

def datetimeConverter(item):
    """FHIR 資源的日期時間轉換器"""
    if isinstance(item, dict):
        for k, v in item.items():
            if isinstance(v, dict):
                item[k] = datetimeConverter(v)
            elif isinstance(v, list):
                item[k] = datetimeConverter(v)
            elif isinstance(v, str):
                try:
                    # 检查是否为符合特定格式的 ISO 8601 字符串
                    if len(v) >= 20 and len(v) <= 30 and '+' in v and 'T' in v:
                        # 忽略已经带时区的 ISO 8601 字符串
                        pass
                    elif len(v) >= 20 and len(v) <= 30:
                        datetimeValue = pd.to_datetime(v)
                        item[k] = datetimeValue
                except Exception as e:
                    pass
    elif isinstance(item, list):
        if len(item) < 10:
            for i, v in enumerate(item):
                if isinstance(v, dict):
                    item[i] = datetimeConverter(v)
                elif isinstance(v, list):
                    item[i] = datetimeConverter(v)
                elif isinstance(v, str):
                    try:
                        if len(v) >= 20 and len(v) <= 30 and '+' in v and 'T' in v:
                            pass
                        elif len(v) >= 20 and len(v) <= 30:
                            datetimeValue = pd.to_datetime(v)
                            item[i] = datetimeValue
                    except Exception as e:
                        pass
    return item

def get_tryExcept_Moreinfo(e):
    """錯誤信息詳細記錄"""
    import inspect
    frame_info = inspect.trace()[-1]
    file_name = frame_info[0].f_code.co_filename
    line_number = frame_info[0].f_lineno
    print(f"An exception occurred in file '{file_name}' at line {line_number}: {e}")

# ===== MongoDB 連線管理 =====

# 全域變數
_mongo_client = None
_mongo_col = None

# 設置 pymongo 日誌級別
logging.getLogger("pymongo").setLevel(logging.WARNING)

def get_mongo_client(database, collection):
    """獲取 MongoDB 客戶端 (支援主備切換)"""
    global _mongo_client, _mongo_col
    if _mongo_client is None:
        try:
            # 嘗試連接到主要 MongoDB
            _mongo_client = MongoClient(
                f"mongodb://aicenter:1234qwer@{MONGO_MAINURI}/", 
                retryWrites=False, 
                maxPoolSize=10, 
                serverSelectionTimeoutMS=5000
            )
            _mongo_client.admin.command('ping')  # 測試主要連線
            _mongo_col = _mongo_client[database][collection]
        except errors.ServerSelectionTimeoutError as e:
            try:
                # 嘗試連接到備援 MongoDB
                _mongo_client = MongoClient(
                    f"mongodb://aicenter:1234qwer@{MONGO_BACKUPURI}/", 
                    retryWrites=False, 
                    maxPoolSize=10, 
                    serverSelectionTimeoutMS=5000
                )
                _mongo_client.admin.command('ping')  # 測試備援連線
                _mongo_col = _mongo_client[database][collection]
            except errors.ServerSelectionTimeoutError as e:
                raise  # 如果都無法連線則拋出異常
    return _mongo_col

async def save_to_mongo(data):
    """保存資料到 MongoDB"""
    try:
        mongo_col = get_mongo_client(MONGO_DATABASE, MONGO_COLLECTION)
        mongo_col.insert_one(data)
    except Exception as e:
        get_tryExcept_Moreinfo(e)
        logging.error(f"Failed to insert document into MongoDB: {e}")

# ===== 相容性支援 (為了 STEMI 功能) =====

# 為了相容 STEMI.py 中的導入
mongo_client = MongoClient(f"mongodb://aicenter:1234qwer@{MONGO_MAINURI}/", serverSelectionTimeoutMS=5000)
mongo_client2 = MongoClient(f"mongodb://aicenter:1234qwer@{MONGO_BACKUPURI}/", serverSelectionTimeoutMS=5000)