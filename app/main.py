from fastapi import FastAPI, Depends, HTTPException, status,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from sqlmodel import select
from datetime import timedelta, datetime
import time
import httpx
import json

from .models import get_session, Account,base_engine
# from .CTCAE_models import ctcae_engine,database_name,ctcae_metadata  # 暫時註解
from .JWT import (
    verify_password,
    create_access_token,
    get_user,
    get_password_hash,
    change_password,
)
from .routers import STEMI, admin
# from .routers import Ekghome, iSEPS, iAST, iASTv2, sepsis
# from .routers import CAD, CTCAE,ARDS,iIDeAS,NCCT,ARDS_infiltrate,PressureInjury,ICH,FlapDet,ARDS_new

from sqlalchemy_utils import create_database,database_exists
from sqlalchemy import exc
from sqlmodel import SQLModel
from fastapi.responses import JSONResponse

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import asyncpg
import os
import logging


app = FastAPI(root_path='/api/')  # root_path='/api/'
app.include_router(STEMI.router)
app.include_router(admin.router)
# 其他路由器暫時註解，因為只有 STEMI 功能
# app.include_router(iSEPS.router)
# app.include_router(iAST.router)
# app.include_router(iASTv2.router)
# app.include_router(sepsis.router)
# app.include_router(CAD.router)
# app.include_router(CTCAE.router)
# app.include_router(ARDS.router)
# app.include_router(iIDeAS.router)
# app.include_router(Ekghome.router)
# app.include_router(NCCT.router)
# app.include_router(ARDS_infiltrate.router)
# app.include_router(PressureInjury.router)
# app.include_router(ICH.router)
# app.include_router(FlapDet.router)
# app.include_router(ARDS_new.router)


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 增強的中間件：記錄日誌並發送到 audit logger
@app.middleware("http")
async def add_logwging(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # 🚀 定義需要過濾的路徑（健康檢查相關）
    ignored_paths = ["/docs", "/openapi.json", "/redoc", "/favicon.ico", "/health"]
    
    # 檢查是否為需要過濾的路徑
    should_log = True
    request_path = str(request.url.path)
    
    for ignored_path in ignored_paths:
        if ignored_path in request_path:
            should_log = False
            break
    
    # 🎯 只記錄真正的 API 請求（POST、GET 等業務操作）
    if should_log:
        # 本地日誌記錄
        logging.info(f"{request.client.host}:{request.client.port} - {request.method} {request.url} {response.status_code}")
        
        # 🚀 發送到 audit logger
        await send_audit_log(request, response, process_time)
    
    return response

async def send_audit_log(request: Request, response, process_time: float):
    """發送審計日誌到 audit logger 服務"""
    try:
        # 準備日誌資料 - 轉換為 JSON 字串，符合 logger 預期格式
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.url.query) if request.url.query else "",
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "content_type": request.headers.get("Content-Type", ""),
            "api": f"{request.method} {request.url.path}",  # 🔧 修正：改為字串而不是嵌套物件
            "project": "FHIR-Backend"
        }
        
        # 🔧 轉換為 JSON 字串發送（符合 logger 的 await request.body() 預期）
        log_json_string = json.dumps(log_data, ensure_ascii=False)
        
        # 異步發送到 audit logger
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://FHIR-backend-logger:8000/log",
                content=log_json_string,  # 發送純文字 JSON
                timeout=0.5,  # 🚀 500ms 超時保護，避免影響主服務性能
                headers={"Content-Type": "application/json"}
            )
            
    except Exception as e:
        # 發送失敗不影響主要功能，只記錄錯誤
        logging.warning(f"Failed to send audit log: {str(e)}")
        pass

@app.get("/")
async def root():
    return {"message": "FHIR Backend API is running", "status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )

async def check_and_create_database(database_name, user, password, host, port):
    # 使用 asyncpg 檢查資料庫是否存在
    conn = await asyncpg.connect(user=user, password=password, host=host, port=port)
    result = await conn.fetch(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'")
    
    # 如果資料庫不存在，創建它
    if not result:
        print(f'Creating database "{database_name}"')
        await conn.execute(f'CREATE DATABASE "{database_name}"')

    await conn.close()


# @app.get('/apitest')
# def apitest():
#     print('connected')
#     return{'connected': 'success'}

# class LoginInfo(BaseModel):
#     account: str
#     password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@app.post("/login", response_model=Token)
async def login(
    info: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect Account or Password",
    )
    account = info.username
    password = info.password
    statement = select(Account).where(Account.username == account)
    result = await db.execute(statement)
    result = result.scalars().one_or_none()
    # print(result)
    if result:
        if verify_password(password, result.password):
            if result.enable == False:
                credentials_exception.detail = (
                    "This Account is not enable, please contact with AI Center."
                )
                raise credentials_exception
            return {
                "access_token": create_access_token({"username": account}),
                "token_type": "bearer",
                "expires_in": timedelta(minutes=15).seconds
            }
    raise credentials_exception


class newUserInfo(BaseModel):
    username: str
    password: str
    note: str = None
    phone: str = None


@app.post("/createUser")
async def createUser(
    info: newUserInfo, user=Depends(get_user), db: AsyncSession = Depends(get_session)
):
    statement = select(Account).where(Account.username == info.username)
    result = await db.execute(statement)
    # print(dir(result.scalars()))
    result = result.scalars().one_or_none()
    # print(not(result))
    if not (result):
        account = Account(
            username=info.username,
            password=get_password_hash(info.password),
            note=info.note,
            phone=info.phone,
        )
        db.add(account)
        await db.commit()
        return True
    return False


class changePasswordInfo(BaseModel):
    username: str
    oldpassword: str
    newpassword: str


@app.post("/changePassword")
async def changePassword(
    info: changePasswordInfo,
    user=Depends(get_user),
    db: AsyncSession = Depends(get_session),
):
    if user == info.username:
        return await change_password(
            db, info.username, info.newpassword, info.oldpassword
        )
    return False



async def init_main_database():
    """初始化主要資料庫和資料表"""
    try:
        # 檢查表格是否已存在
        async with base_engine.begin() as conn:
            # 檢查表格是否存在的簡單方法 - 使用 PostgreSQL 語法
            try:
                # 檢查 PostgreSQL 中的表格
                result = await conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('account', 'resources', 'hospital_info')
                """))
                existing_tables = [row[0] for row in result.fetchall()]
                
                required_tables = ['account', 'resources', 'hospital_info']
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                if missing_tables:
                    # 只有在有缺少的表格時才創建
                    await conn.run_sync(SQLModel.metadata.create_all)
                    print(f"主要資料庫資料表創建成功 (新建表格: {', '.join(missing_tables)})")
                else:
                    # print("主要資料庫資料表已存在，跳過創建")
                    pass
                    
            except Exception as check_error:
                # 如果檢查失敗，可能是表格不存在，直接創建
                await conn.run_sync(SQLModel.metadata.create_all)
                print("主要資料庫資料表創建成功")
                
    except Exception as e:
        print(f"主要資料庫初始化失敗: {e}")

@app.on_event("startup")
async def on_startup():
    # 初始化主要資料庫
    await init_main_database()
    
    # CTCAE 相關功能暫時註解，因為只專注於 STEMI
    # 檢查並建立 CTCAE 資料庫 (如果需要的話)
    # try:
    #     await check_and_create_database(
    #         database_name=database_name, 
    #         user='postgres', 
    #         password='@CMUH_aicenter', 
    #         host='10.18.27.131', 
    #         port='35432'
    #     )

    #     # 非同步建立 CTCAE 資料表
    #     async with ctcae_engine.begin() as conn:
    #         # 使用 metadata.create_all() 方法创建所有表格
    #         await conn.run_sync(ctcae_metadata.create_all)
    # except Exception as e:
    #     print(f"CTCAE 資料庫初始化失敗 (可忽略): {e}")
