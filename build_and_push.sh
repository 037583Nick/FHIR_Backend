#!/bin/bash
# build_and_push.sh - 在 240 機器上建置並推送映像

echo "🚀 開始建置 FHIR Backend Docker 映像..."

# 建置映像
docker-compose -f docker-compose.build.yml build

# 檢查建置是否成功
if [ $? -eq 0 ]; then
    echo "✅ 映像建置成功"
    
    # 推送映像到註冊表
    echo "📤 推送映像到註冊表..."
    docker-compose -f docker-compose.build.yml push app
    
    if [ $? -eq 0 ]; then
        echo "✅ 映像推送成功"
        echo "🎯 映像標籤: 10.18.27.131:17180/fhir/ai-fhir-backend:v2.2.0"
        echo "📋 現在可以在 10.69.12.83 機器上執行:"
        echo "   docker-compose pull && docker-compose up -d"
    else
        echo "❌ 映像推送失敗"
        exit 1
    fi
else
    echo "❌ 映像建置失敗"
    exit 1
fi
