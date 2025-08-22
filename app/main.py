from fastapi import FastAPI, Depends, HTTPException, status,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from sqlmodel import select
from datetime import timedelta

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



app = FastAPI()  # 移除 root_path 用於本地測試
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

# Custom logging middleware
@app.middleware("http")
async def add_logwging(request: Request, call_next):
    response = await call_next(request)
    logging.info(f"{request.client.host}:{request.client.port} - {request.method} {request.url} {response.status_code}")
    return response

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
