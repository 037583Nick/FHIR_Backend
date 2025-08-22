from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional

from ..models import get_session, Account
from ..JWT import get_password_hash, verify_password, get_user

router = APIRouter(
    prefix="/admin",
    tags=["用戶管理"],
    responses={404: {"description": "Not found"}},
)

class CreateUserRequest(BaseModel):
    username: str
    password: str
    note: Optional[str] = None
    phone: Optional[str] = None
    enable: bool = True

class UpdateUserRequest(BaseModel):
    note: Optional[str] = None
    phone: Optional[str] = None
    enable: Optional[bool] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/create-user")
async def create_user(
    request: CreateUserRequest,
    current_user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session)
):
    """創建新用戶 (需要管理員權限)"""
    
    # 檢查用戶名是否已存在
    statement = select(Account).where(Account.username == request.username)
    result = await db.execute(statement)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶名已存在"
        )
    
    # 創建新用戶
    new_user = Account(
        username=request.username,
        password=get_password_hash(request.password),
        note=request.note,
        phone=request.phone,
        enable=request.enable
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "message": "用戶創建成功",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "note": new_user.note,
            "phone": new_user.phone,
            "enable": new_user.enable
        }
    }

@router.get("/users")
async def list_users(
    current_user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session)
):
    """列出所有用戶 (需要管理員權限)"""
    
    statement = select(Account)
    result = await db.execute(statement)
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "note": user.note,
                "phone": user.phone,
                "enable": user.enable
            }
            for user in users
        ]
    }

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session)
):
    """更新用戶資訊 (需要管理員權限)"""
    
    statement = select(Account).where(Account.id == user_id)
    result = await db.execute(statement)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 更新用戶資訊
    if request.note is not None:
        user.note = request.note
    if request.phone is not None:
        user.phone = request.phone
    if request.enable is not None:
        user.enable = request.enable
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "message": "用戶更新成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "note": user.note,
            "phone": user.phone,
            "enable": user.enable
        }
    }

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session)
):
    """刪除用戶 (需要管理員權限)"""
    
    statement = select(Account).where(Account.id == user_id)
    result = await db.execute(statement)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 不能刪除自己
    if user.username == current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能刪除自己的帳號"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "用戶刪除成功"}

@router.post("/change-my-password")
async def change_my_password(
    request: ChangePasswordRequest,
    current_user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session)
):
    """修改自己的密碼"""
    
    statement = select(Account).where(Account.username == current_user)
    result = await db.execute(statement)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 驗證舊密碼
    if not verify_password(request.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="舊密碼錯誤"
        )
    
    # 更新密碼
    user.password = get_password_hash(request.new_password)
    await db.commit()
    
    return {"message": "密碼修改成功"}
