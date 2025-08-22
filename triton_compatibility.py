"""
Triton 相容性層
將舊版 trtis 調用轉換為新版 tritonclient 調用
"""

import os
import sys

try:
    # 嘗試導入新版 tritonclient
    import tritonclient.grpc as grpcclient
    MODERN_TRITON = True
    print("使用新版 Triton 客戶端")
except ImportError:
    # 退回到舊版 trtis
    import trtis.grpc_service_pb2_grpc as grpc_service_pb2_grpc
    import trtis.grpc_service_pb2 as grpc_service_pb2
    import trtis.request_status_pb2 as request_status_pb2
    import trtis.server_status_pb2 as server_status_pb2
    import grpc
    MODERN_TRITON = False
    print("使用舊版 trtis 客戶端")

class CompatibilityTritonClient:
    """相容性客戶端，自動選擇適當的 Triton 協議"""
    
    def __init__(self, server_url, model_name, model_version="1"):
        self.server_url = server_url
        self.model_name = model_name
        self.model_version = model_version
        
        if MODERN_TRITON:
            self._init_modern_client()
        else:
            self._init_legacy_client()
    
    def _init_modern_client(self):
        """初始化新版客戶端"""
        try:
            self.client = grpcclient.InferenceServerClient(
                url=self.server_url,
                verbose=False
            )
            
            if not self.client.is_server_ready():
                raise Exception("Server not ready")
                
            if not self.client.is_model_ready(self.model_name, self.model_version):
                raise Exception(f"Model {self.model_name} not ready")
                
            print(f"✅ 新版 Triton 客戶端連接成功: {self.server_url}")
            
        except Exception as e:
            raise Exception(f"Modern Triton client failed: {e}")
    
    def _init_legacy_client(self):
        """初始化舊版客戶端"""
        try:
            MAX_MESSAGE_LENGTH = 4194304 * 32
            channel = grpc.insecure_channel(
                self.server_url,
                options=[
                    ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
                    ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
                ],
            )
            self.client = grpc_service_pb2_grpc.GRPCServiceStub(channel)
            
            # 檢查模型狀態
            status_request = grpc_service_pb2.StatusRequest(model_name=self.model_name)
            model_response = self.client.Status(status_request)
            
            if model_response.request_status.code != request_status_pb2.SUCCESS:
                raise Exception(model_response.request_status.msg)
                
            print(f"✅ 舊版 trtis 客戶端連接成功: {self.server_url}")
            
        except Exception as e:
            raise Exception(f"Legacy trtis client failed: {e}")
    
    def infer(self, inputs, outputs):
        """統一的推論介面"""
        if MODERN_TRITON:
            return self._infer_modern(inputs, outputs)
        else:
            return self._infer_legacy(inputs, outputs)
    
    def _infer_modern(self, inputs, outputs):
        """新版推論"""
        # 實作新版推論邏輯
        pass
    
    def _infer_legacy(self, inputs, outputs):
        """舊版推論"""
        # 實作舊版推論邏輯
        pass

# 測試函數
def test_triton_compatibility():
    """測試 Triton 相容性"""
    server = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")
    
    try:
        # 測試實際的模型名稱
        client = CompatibilityTritonClient(server, "ecg_stemi_by")
        print("🎉 Triton 客戶端初始化成功！")
        return True
    except Exception as e:
        print(f"❌ Triton 客戶端初始化失敗: {e}")
        return False

if __name__ == "__main__":
    test_triton_compatibility()
