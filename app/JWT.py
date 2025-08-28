import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
# import pandas as pd
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .models import get_session, Account

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if(os.path.exists('server.key') and os.path.exists('server.pub.key')):
    private_key = open('server.key', 'r').read()
    public_key = open('server.pub.key', 'r').read()
else:
    os.system('openssl genrsa -out server.key 2048')
    os.system(
        'openssl rsa -in server.key -pubout -out server.pub.key')
    private_key = open('server.key', 'r').read()
    public_key = open('server.pub.key', 'r').read()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# def getDBConnection():
#     connection = pg2.connect(
#         database="postgres",
#         user='postgres',
#         password='@CMUH_aicenter',
#         host='10.65.51.238',
#         port='5204'
#     )
#     cur = connection.cursor()
#     return connection, cur


#      ██╗██╗    ██╗████████╗
#      ██║██║    ██║╚══██╔══╝
#      ██║██║ █╗ ██║   ██║
# ██   ██║██║███╗██║   ██║
# ╚█████╔╝╚███╔███╔╝   ██║
#  ╚════╝  ╚══╝╚══╝    ╚═╝

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm="RS256")
    return encoded_jwt


async def get_user(token: str = Depends(oauth2_scheme), db:AsyncSession = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        username: str = payload.get("username")
        if username is None:
            print('username is None')
            raise credentials_exception
        statement = select(Account).where(Account.username == username)
        result = await db.execute(statement)
        result = result.scalars().one()
        if result:
            return username
        else:
            print('len(df) == 0')
            raise credentials_exception
        
    except JWTError as e:
        print(e)
        print(token)
        raise credentials_exception


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def change_password(db: AsyncSession, username, new_password, old_password):
    new_hash_password = get_password_hash(new_password)
    statement = select(Account).where(Account.username == username)
    result = await db.execute(statement)
    result = result.scalars().one()
    if result:
        if verify_password(old_password, result.password):
            result.password = new_hash_password
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return True
    return False