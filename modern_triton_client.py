"""
新版 Triton 客戶端代碼範例
用於替換舊版 trtis 代碼
"""

import tritonclient.grpc as grpcclient
import numpy as np
import os

class ModernTritonPreprocessor:
    def __init__(self, fn, model_name, server=None, model_ver="1"):
        self.fn = fn
        self.model_name = model_name
        self.model_ver = model_ver
        
        # 從環境變數讀取 gRPC 伺服器地址
        if server is None:
            server = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")
        self.server = server
        
        # 創建 Triton 客戶端
        try:
            self.triton_client = grpcclient.InferenceServerClient(
                url=server,
                verbose=False
            )
            
            # 檢查伺服器狀態
            if not self.triton_client.is_server_ready():
                raise Exception("Triton server not ready")
                
            # 檢查模型狀態
            if not self.triton_client.is_model_ready(model_name, model_ver):
                raise Exception(f"Model {model_name} not ready")
                
        except Exception as e:
            raise Exception(f"Failed to connect to Triton server: {e}")
    
    def infer(self, inputs, outputs):
        """執行推論"""
        try:
            # 準備輸入
            triton_inputs = []
            for input_name, input_data in inputs.items():
                triton_input = grpcclient.InferInput(
                    input_name, 
                    input_data.shape, 
                    "FP32"  # 或其他適當的數據類型
                )
                triton_input.set_data_from_numpy(input_data)
                triton_inputs.append(triton_input)
            
            # 準備輸出
            triton_outputs = []
            for output_name in outputs:
                triton_output = grpcclient.InferRequestedOutput(output_name)
                triton_outputs.append(triton_output)
            
            # 執行推論
            response = self.triton_client.infer(
                model_name=self.model_name,
                model_version=self.model_ver,
                inputs=triton_inputs,
                outputs=triton_outputs
            )
            
            # 獲取結果
            results = {}
            for output_name in outputs:
                results[output_name] = response.as_numpy(output_name)
            
            return results
            
        except Exception as e:
            raise Exception(f"Inference failed: {e}")
