import requests
import json

# Triton Server 設定
TRITON_HOST = "10.69.12.83"
TRITON_HTTP_PORT = 8005

def check_triton_endpoints():
    """檢查所有可能的 Triton Server 端點"""
    endpoints = [
        "/",
        "/v2",
        "/v2/health/ready",
        "/v2/health/live", 
        "/v2/models",
        "/api/v1/models",
        "/models",
        "/status",
        "/health"
    ]
    
    print("=" * 60)
    print("🔍 檢查 Triton Server 所有端點")
    print("=" * 60)
    print(f"🌐 Server: {TRITON_HOST}:{TRITON_HTTP_PORT}")
    print()
    
    for endpoint in endpoints:
        url = f"http://{TRITON_HOST}:{TRITON_HTTP_PORT}{endpoint}"
        try:
            print(f"📍 測試端點: {endpoint}")
            response = requests.get(url, timeout=10)
            print(f"   ✅ 狀態碼: {response.status_code}")
            
            # 顯示回應內容
            content_type = response.headers.get('content-type', 'unknown')
            print(f"   📄 內容類型: {content_type}")
            
            if 'json' in content_type.lower():
                try:
                    json_data = response.json()
                    print(f"   📊 JSON 內容: {json.dumps(json_data, indent=2)[:500]}...")
                except json.JSONDecodeError:
                    print(f"   📝 文字內容: {response.text[:200]}...")
            else:
                print(f"   📝 文字內容: {response.text[:200]}...")
            
            print()
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 連接失敗: {e}")
            print()

def check_specific_model():
    """檢查特定模型 ecg_stemi_by"""
    model_name = "ecg_stemi_by"
    endpoints = [
        f"/v2/models/{model_name}",
        f"/v2/models/{model_name}/ready",
        f"/api/v1/models/{model_name}",
        f"/models/{model_name}"
    ]
    
    print("=" * 60)
    print(f"🔍 檢查特定模型: {model_name}")
    print("=" * 60)
    
    for endpoint in endpoints:
        url = f"http://{TRITON_HOST}:{TRITON_HTTP_PORT}{endpoint}"
        try:
            print(f"📍 測試端點: {endpoint}")
            response = requests.get(url, timeout=10)
            print(f"   ✅ 狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print(f"   📊 模型資訊: {json.dumps(json_data, indent=2)}")
                except json.JSONDecodeError:
                    print(f"   📝 回應: {response.text}")
            else:
                print(f"   📝 回應: {response.text[:200]}...")
            
            print()
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 連接失敗: {e}")
            print()

if __name__ == "__main__":
    check_triton_endpoints()
    check_specific_model()
