import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from app.models import base_engine, Account, Resources, hospital_info
from app.JWT import get_password_hash
import os
from datetime import datetime

class DatabaseManager:
    """資料庫管理類別，負責資料庫的初始化和管理操作"""
    
    def __init__(self):
        self.db_host = "10.69.12.83"
        self.db_port = 8008
        self.db_user = "aicenter"
        self.db_password = "1234qwer"
        self.db_name = "hapifhir"
    
    async def check_and_create_database(self):
        """檢查並創建資料庫"""
        try:
            # 連接到 PostgreSQL 伺服器 (不指定資料庫)
            conn = await asyncpg.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                database="postgres"  # 連接到預設資料庫
            )
            
            # 檢查 hapifhir 資料庫是否存在
            result = await conn.fetch(f"SELECT 1 FROM pg_database WHERE datname = '{self.db_name}'")
            
            if not result:
                print(f"創建 {self.db_name} 資料庫...")
                await conn.execute(f'CREATE DATABASE "{self.db_name}"')
                print("資料庫創建成功！")
            else:
                print(f"{self.db_name} 資料庫已存在")
                
            await conn.close()
            return True
            
        except Exception as e:
            print(f"資料庫檢查/創建失敗: {e}")
            return False

    async def create_tables(self):
        """創建所有資料表"""
        try:
            print("創建資料表...")
            async with base_engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            print("所有資料表創建成功！")
            return True
        except Exception as e:
            print(f"資料表創建失敗: {e}")
            return False

    async def create_default_admin(self, username="T37583", password="T37583"):
        """創建預設管理員帳號"""
        try:
            from app.models import get_session
            from sqlmodel import select
            
            async for session in get_session():
                # 檢查是否已有此管理員帳號
                statement = select(Account).where(Account.username == username)
                result = await session.execute(statement)
                existing_admin = result.scalars().first()
                
                if not existing_admin:
                    admin_account = Account(
                        username=username,
                        password=get_password_hash(password),
                        note="Default admin account",
                        phone="",
                        enable=True
                    )
                    session.add(admin_account)
                    await session.commit()
                    print(f"預設管理員帳號創建成功！")
                    print(f"帳號: {username}")
                    print(f"密碼: {password}")
                    return True
                else:
                    print(f"管理員帳號 '{username}' 已存在")
                    return True
                    
        except Exception as e:
            print(f"創建預設帳號失敗: {e}")
            return False

    async def create_user(self, username, password, note=None, phone=None, enable=True):
        """創建新用戶"""
        try:
            from app.models import get_session
            from sqlmodel import select
            
            async for session in get_session():
                # 檢查用戶是否已存在
                statement = select(Account).where(Account.username == username)
                result = await session.execute(statement)
                existing_user = result.scalars().first()
                
                if existing_user:
                    print(f"用戶 '{username}' 已存在")
                    return False
                
                new_user = Account(
                    username=username,
                    password=get_password_hash(password),
                    note=note,
                    phone=phone,
                    enable=enable
                )
                session.add(new_user)
                await session.commit()
                print(f"用戶 '{username}' 創建成功！")
                return True
                
        except Exception as e:
            print(f"創建用戶失敗: {e}")
            return False

    async def list_users(self):
        """列出所有用戶"""
        try:
            from app.models import get_session
            from sqlmodel import select
            
            async for session in get_session():
                statement = select(Account)
                result = await session.execute(statement)
                users = result.scalars().all()
                
                print(f"\n總共 {len(users)} 個用戶:")
                print("-" * 80)
                print(f"{'ID':<5} {'用戶名':<15} {'啟用':<6} {'備註':<20} {'電話':<15}")
                print("-" * 80)
                
                for user in users:
                    print(f"{user.id:<5} {user.username:<15} {'是' if user.enable else '否':<6} {user.note or '':<20} {user.phone or '':<15}")
                
                return users
                
        except Exception as e:
            print(f"列出用戶失敗: {e}")
            return []

    async def add_hospital_info(self, hosp_id, hosp_name):
        """新增醫院資訊"""
        try:
            from app.models import get_session
            from sqlmodel import select
            
            async for session in get_session():
                # 檢查醫院是否已存在
                statement = select(hospital_info).where(hospital_info.hosp_id == hosp_id)
                result = await session.execute(statement)
                existing_hospital = result.scalars().first()
                
                if existing_hospital:
                    print(f"醫院 ID '{hosp_id}' 已存在")
                    return False
                
                new_hospital = hospital_info(
                    hosp_id=hosp_id,
                    hosp_name=hosp_name,
                    create_time=datetime.now()
                )
                session.add(new_hospital)
                await session.commit()
                print(f"醫院資訊創建成功: {hosp_id} - {hosp_name}")
                return True
                
        except Exception as e:
            print(f"新增醫院資訊失敗: {e}")
            return False

    async def list_hospitals(self):
        """列出所有醫院"""
        try:
            from app.models import get_session
            from sqlmodel import select
            
            async for session in get_session():
                statement = select(hospital_info)
                result = await session.execute(statement)
                hospitals = result.scalars().all()
                
                print(f"\n總共 {len(hospitals)} 家醫院:")
                print("-" * 60)
                print(f"{'ID':<5} {'醫院代碼':<15} {'醫院名稱':<30}")
                print("-" * 60)
                
                for hospital in hospitals:
                    print(f"{hospital.id:<5} {hospital.hosp_id:<15} {hospital.hosp_name:<30}")
                
                return hospitals
                
        except Exception as e:
            print(f"列出醫院失敗: {e}")
            return []

    async def init_database(self):
        """完整的資料庫初始化"""
        print("=" * 60)
        print("FHIR Backend 資料庫初始化開始...")
        print("=" * 60)
        
        success = True
        
        # 1. 檢查並創建資料庫
        if not await self.check_and_create_database():
            success = False
        
        # 2. 創建資料表
        if success and not await self.create_tables():
            success = False
        
        # 3. 創建預設管理員
        if success and not await self.create_default_admin():
            success = False
        
        if success:
            print("\n" + "=" * 60)
            print("資料庫初始化完成！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("資料庫初始化失敗！")
            print("=" * 60)
        
        return success

    async def cleanup(self):
        """清理資源"""
        try:
            await base_engine.dispose()
        except Exception as e:
            print(f"清理資源時發生錯誤: {e}")


async def main():
    """主函數 - 提供互動式操作選單"""
    db_manager = DatabaseManager()
    
    try:
        while True:
            print("\n" + "=" * 50)
            print("FHIR Backend 資料庫管理工具")
            print("=" * 50)
            print("1. 初始化資料庫")
            print("2. 創建新用戶")
            print("3. 列出所有用戶")
            print("4. 新增醫院資訊")
            print("5. 列出所有醫院")
            print("6. 退出")
            print("-" * 50)
            
            choice = input("請選擇操作 (1-6): ").strip()
            
            if choice == "1":
                await db_manager.init_database()
            
            elif choice == "2":
                username = input("用戶名: ").strip()
                password = input("密碼: ").strip()
                note = input("備註 (可選): ").strip() or None
                phone = input("電話 (可選): ").strip() or None
                enable_input = input("啟用? (y/n, 預設 y): ").strip().lower()
                enable = enable_input != 'n'
                
                await db_manager.create_user(username, password, note, phone, enable)
            
            elif choice == "3":
                await db_manager.list_users()
            
            elif choice == "4":
                hosp_id = input("醫院代碼: ").strip()
                hosp_name = input("醫院名稱: ").strip()
                await db_manager.add_hospital_info(hosp_id, hosp_name)
            
            elif choice == "5":
                await db_manager.list_hospitals()
            
            elif choice == "6":
                print("退出...")
                break
            
            else:
                print("無效選擇，請重新輸入")
    
    except KeyboardInterrupt:
        print("\n\n程式被中斷")
    
    finally:
        await db_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
