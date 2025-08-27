@echo off
REM build_and_push.bat - Windows 版本的建置腳本

echo 🚀 開始建置 FHIR Backend Docker 映像...

REM 建置映像
docker-compose -f docker-compose.build.yml build

if %errorlevel% equ 0 (
    echo ✅ 映像建置成功
    
    REM 推送映像到註冊表
    echo 📤 推送映像到註冊表...
    docker-compose -f docker-compose.build.yml push app
    
    if %errorlevel% equ 0 (
        echo ✅ 映像推送成功
        echo 🎯 映像標籤: 10.18.27.131:17180/fhir/ai-fhir-backend:v2.2.0
        echo 📋 現在可以在 10.69.12.83 機器上執行:
        echo    docker-compose pull ^&^& docker-compose up -d
    ) else (
        echo ❌ 映像推送失敗
        exit /b 1
    )
) else (
    echo ❌ 映像建置失敗
    exit /b 1
)
