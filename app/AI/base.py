from io import BytesIO
from PIL import Image
import base64
import numpy as np
import requests
import os
import grpc

# 使用新版 tritonclient (舊版與新版 Triton Server 不兼容)
try:
    import tritonclient.grpc as grpcclient
    from tritonclient.utils import np_to_triton_dtype
    NEW_CLIENT = True
    # print("✅ 使用新版 tritonclient")
except ImportError:
    raise ImportError("❌ 需要安裝 tritonclient！")

def model_dtype_to_np(model_dtype):
    """轉換模型資料類型到 numpy 類型"""
    # 新版 tritonclient 使用字串表示類型
    dtype_map = {
        'BOOL': np.bool,
        'INT8': np.int8,
        'INT16': np.int16,
        'INT32': np.int32,
        'INT64': np.int64,
        'UINT8': np.uint8,
        'UINT16': np.uint16,
        'FP16': np.float16,
        'FP32': np.float32,
        'FP64': np.float64,
        'BYTES': np.dtype(object)
    }
    return dtype_map.get(model_dtype, None)

class ModelNotReadyException(Exception):
    pass

class ModernBasePreprocessor:
    """使用新版 tritonclient 的基礎預處理器"""
    
    def __init__(self, fn, model_name, server=None, torch=False, model_ver="1.0"):
        self.fn = fn
        self.image = self.load_image(fn)
        self.model_name = model_name
        self.output_list = []
        self.torch = torch
        self.model_ver = model_ver
        
        # 從環境變數讀取 gRPC 伺服器地址
        if server is None:
            server = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")
        self.server = server
        
        if not torch:
            self._init_new_client()
    
    def _init_new_client(self):
        """初始化新版 tritonclient"""
        try:
            self.grpc_client = grpcclient.InferenceServerClient(
                url=self.server,
                verbose=False
            )
            
            # 檢查服務器是否就緒
            if not self.grpc_client.is_server_ready():
                raise Exception("Triton server is not ready")
            
            # 檢查模型是否就緒
            if not self.grpc_client.is_model_ready(self.model_name):
                raise ModelNotReadyException(f"Model {self.model_name} is not ready")
            
            # 獲取模型配置
            self.model_config = self.grpc_client.get_model_config(self.model_name)
            # print(f"✅ 模型 {self.model_name} 已就緒")
            
        except Exception as e:
            print(f"❌ 新版客戶端初始化失敗: {e}")
            raise

    def get_image(self):
        return self.image

    def load_image(self, fn):
        # 這個方法需要在子類中實現
        raise NotImplementedError("load_image must be implemented by subclass")

    def infer_one(self, input_dataset):
        """推論單個數據集，完全模仿舊版邏輯"""
        if self.torch:
            # PyTorch 服務器推論
            byte_io = BytesIO()
            np.save(byte_io, input_dataset)
            url = f"http://{self.server}/predictions/{self.model_name}/{self.model_ver}/"
            r = requests.post(url, data=byte_io.getvalue())
            return r.json()
        
        # 使用新版 tritonclient
        return self._infer_one_new_client_compat(input_dataset)
    
    def _infer_one_new_client_compat(self, input_dataset):
        """使用新版 tritonclient，但完全模仿舊版的邏輯和設定"""
        try:
            inputs = []
            outputs = []
            
            # 正確訪問模型配置
            model_config = self.model_config.config
            
            # 準備輸入，模仿舊版方式
            for input_spec, data in zip(model_config.input, input_dataset):
                # 確保批次大小為 1
                if data.ndim == 2:  # 如果是 2D，添加批次維度
                    data = np.expand_dims(data, axis=0)
                
                input_obj = grpcclient.InferInput(
                    input_spec.name, 
                    data.shape, 
                    np_to_triton_dtype(data.dtype)
                )
                input_obj.set_data_from_numpy(data)
                inputs.append(input_obj)

            # 準備輸出
            for output_spec in model_config.output:
                outputs.append(grpcclient.InferRequestedOutput(output_spec.name))

            # 執行推論
            response = self.grpc_client.infer(
                model_name=self.model_name,
                inputs=inputs,
                outputs=outputs
            )

            # 收集結果，模仿舊版格式
            output_list = []
            for output_spec in model_config.output:
                result = response.as_numpy(output_spec.name)
                
                # 檢查是否有標籤檔案，如果有則需要轉換成 (label, value) 格式  
                if hasattr(output_spec, 'label_filename') and output_spec.label_filename:
                    # 🔧 新版 tritonclient 需要手動實現舊版 trtis 的標籤轉換功能
                    # print(f"🔍 模型 {self.model_name} 有 label_filename: {output_spec.label_filename}")
                    
                    if result.ndim > 1:
                        result = result.flatten()
                    
                    # 找到最高機率的索引和值
                    max_idx = np.argmax(result)
                    max_value = float(result[max_idx])
                    
                    # print(f"🔍 原始結果: 最高機率索引={max_idx}, 值={max_value}")
                    
                    # 🔧 根據您的 labels.txt 內容，手動實現標籤轉換
                    if self.model_name == "ecg_multicat12":
                        # 心律模型：使用您提供的 labels.txt 順序
                        labels_from_triton = [
                            'AFIB',     # 0 - labels.txt 第1行
                            'BIGEMINY', # 1 - labels.txt 第2行  
                            'EAR',      # 2 - labels.txt 第3行
                            'AFL',      # 3 - labels.txt 第4行
                            'CHB',      # 4 - labels.txt 第5行
                            'NSR',      # 5 - labels.txt 第6行 ← 這就是您要的！
                            'FRAV',     # 6 - labels.txt 第7行
                            'SECAV1',   # 7 - labels.txt 第8行
                            'VPB',      # 8 - labels.txt 第9行
                            'APB',      # 9 - labels.txt 第10行
                            'ST',       # 10 - labels.txt 第11行
                            'PSVT'      # 11 - labels.txt 第12行
                        ]
                        if max_idx < len(labels_from_triton):
                            label = labels_from_triton[max_idx]
                        else:
                            label = f'Class_{max_idx}'
                        
                        # print(f"🔍 標籤轉換: index {max_idx} -> {label}")
                        output_list.append((label, max_value))
                    else:
                        # 其他模型（包括 STEMI）：保持與舊版一致的 (label, value) 格式
                        if result.ndim > 1:
                            result = result.flatten()
                        max_idx = np.argmax(result)
                        max_value = float(result[max_idx])
                        
                        # 🔧 特殊處理：STEMI 模型直接使用 "STEMI" 標籤
                        if self.model_name == "ecg_stemi_by":
                            # STEMI 二元分類：不管 index 是什麼，都直接用 "STEMI" 標籤
                            # 這樣與舊版保持完全一致
                            label = "STEMI"
                            # print(f"🔍 STEMI 模型固定標籤: index {max_idx} -> {label} (值: {max_value})")
                        else:
                            # 其他模型使用通用標籤
                            label = f'Class_{max_idx}'
                            # print(f"🔍 模型 {self.model_name} 通用標籤轉換: index {max_idx} -> {label}")
                        
                        output_list.append((label, max_value))
                        
                else:
                    # 沒有標籤檔案，直接回傳原始結果
                    output_list.append(result)
            
            self.output_list = output_list  # 設定 output_list 屬性
            return output_list
            
        except Exception as e:
            print(f"❌ 推論失敗: {e}")
            raise

    def get_output_list(self):
        """獲取輸出列表，與舊版兼容"""
        return getattr(self, 'output_list', [])

    def inference_new_client(self, input_data, input_name="input_1", output_name="dense_1/Sigmoid"):
        """使用新版 tritonclient 進行推論"""
        try:
            # 準備輸入
            inputs = []
            inputs.append(grpcclient.InferInput(input_name, input_data.shape, np_to_triton_dtype(input_data.dtype)))
            inputs[0].set_data_from_numpy(input_data)

            # 準備輸出
            outputs = []
            outputs.append(grpcclient.InferRequestedOutput(output_name))

            # 執行推論
            response = self.grpc_client.infer(
                model_name=self.model_name,
                inputs=inputs,
                outputs=outputs
            )

            # 獲取結果
            result = response.as_numpy(output_name)
            return result
            
        except Exception as e:
            print(f"❌ 新版客戶端推論失敗: {e}")
            raise

    def inference_old_client(self, input_data, input_name="input_1", output_name="dense_1/Sigmoid"):
        """使用舊版 trtis 客戶端進行推論"""
        # 這裡保留舊版的推論邏輯
        # 由於太複雜，建議直接使用新版客戶端
        raise NotImplementedError("請安裝 tritonclient 使用新版客戶端")

    def inference(self, input_data, input_name="input_1", output_name="dense_1/Sigmoid"):
        """統一的推論接口"""
        return self.inference_new_client(input_data, input_name, output_name)

# 向後兼容的別名
BasePreprocessor = ModernBasePreprocessor
