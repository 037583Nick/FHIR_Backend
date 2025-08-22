#!/usr/bin/env python3
"""
檢查 Triton Server 可用模型
"""

import requests
import json

def check_triton_models():
    """檢查 Triton Server 可用模型"""
    server = "10.69.12.83:8005"  # HTTP port
    
    print("=" * 50)
    print("🔍 檢查 Triton Server 可用模型")
    print("=" * 50)
    print(f"🌐 HTTP Server: {server}")
    
    try:
        # 檢查伺服器狀態
        status_url = f"http://{server}/v2/health/ready"
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Triton Server 已準備就緒")
        else:
            print(f"⚠️ Triton Server 狀態: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 無法連接到 Triton Server HTTP: {e}")
        return
    
    try:
        # 列出所有模型
        models_url = f"http://{server}/v2/models"
        response = requests.get(models_url, timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            print(f"\n📋 可用模型 ({len(models)} 個):")
            print("-" * 50)
            
            for model in models:
                model_name = model.get('name', 'Unknown')
                print(f"   📦 {model_name}")
                
                # 檢查每個模型的詳細狀態
                model_url = f"http://{server}/v2/models/{model_name}"
                try:
                    model_response = requests.get(model_url, timeout=5)
                    if model_response.status_code == 200:
                        model_info = model_response.json()
                        versions = model_info.get('versions', [])
                        print(f"      版本: {', '.join(versions)}")
                    else:
                        print(f"      狀態: {model_response.status_code}")
                except:
                    print(f"      狀態: 無法獲取")
                    
        else:
            print(f"❌ 無法獲取模型清單: {response.status_code}")
            print(f"回應: {response.text}")
            
    except Exception as e:
        print(f"❌ 檢查模型失敗: {e}")

if __name__ == "__main__":
    check_triton_models()
