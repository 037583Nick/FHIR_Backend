from io import BytesIO
from PIL import Image
import base64
import numpy as np
import requests
import os
import grpc

# 使用新版 tritonclient
try:
    import tritonclient.grpc as grpcclient
    from tritonclient.utils import np_to_triton_dtype
    NEW_CLIENT = True
    print("✅ 使用新版 tritonclient")
except ImportError:
    # 如果新版不可用，回退到舊版
    import trtis.api_pb2 as api_pb2
    import trtis.grpc_service_pb2 as grpc_service_pb2
    import trtis.grpc_service_pb2_grpc as grpc_service_pb2_grpc
    import trtis.model_config_pb2 as model_config_pb2
    import trtis.server_status_pb2 as server_status_pb2
    import trtis.request_status_pb2 as request_status_pb2
    NEW_CLIENT = False
    print("⚠️  使用舊版 trtis 客戶端")

def model_dtype_to_np(model_dtype):
    """轉換模型資料類型到 numpy 類型"""
    if NEW_CLIENT:
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
    else:
        # 舊版使用枚舉
        if model_dtype == model_config_pb2.TYPE_BOOL:
            return np.bool
        elif model_dtype == model_config_pb2.TYPE_INT8:
            return np.int8
        elif model_dtype == model_config_pb2.TYPE_INT16:
            return np.int16
        elif model_dtype == model_config_pb2.TYPE_INT32:
            return np.int32
        elif model_dtype == model_config_pb2.TYPE_INT64:
            return np.int64
        elif model_dtype == model_config_pb2.TYPE_UINT8:
            return np.uint8
        elif model_dtype == model_config_pb2.TYPE_UINT16:
            return np.uint16
        elif model_dtype == model_config_pb2.TYPE_FP16:
            return np.float16
        elif model_dtype == model_config_pb2.TYPE_FP32:
            return np.float32
        elif model_dtype == model_config_pb2.TYPE_FP64:
            return np.float64
        elif model_dtype == model_config_pb2.TYPE_STRING:
            return np.dtype(object)
        return None

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
            if NEW_CLIENT:
                self._init_new_client()
            else:
                self._init_old_client()
    
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
            print(f"✅ 模型 {self.model_name} 已就緒")
            
        except Exception as e:
            print(f"❌ 新版客戶端初始化失敗: {e}")
            raise
    
    def _init_old_client(self):
        """初始化舊版 trtis 客戶端"""
        try:
            MAX_MESSAGE_LENGTH = 4194304 * 32
            channel = grpc.insecure_channel(
                self.server,
                options=[
                    ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
                    ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
                ],
            )
            self.grpc_stub = grpc_service_pb2_grpc.GRPCServiceStub(channel)
            status_request = grpc_service_pb2.StatusRequest(model_name=self.model_name)
            self.model_response = self.grpc_stub.Status(status_request)
            
            if self.model_response.request_status.code != request_status_pb2.SUCCESS:
                raise Exception(self.model_response.request_status.msg)
            if (
                self.model_response.server_status.ready_state
                != server_status_pb2.SERVER_READY
            ):
                raise Exception("Server not ready.")
            if (
                list(
                    self.model_response.server_status.model_status[
                        self.model_name
                    ].version_status.values()
                )[-1].ready_state
                != server_status_pb2.MODEL_READY
            ):
                raise ModelNotReadyException("Model not ready.")
                
        except Exception as e:
            print(f"❌ 舊版客戶端初始化失敗: {e}")
            raise

    def get_image(self):
        return self.image

    def load_image(self, fn):
        # 這個方法需要在子類中實現
        raise NotImplementedError("load_image must be implemented by subclass")

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
        if NEW_CLIENT:
            return self.inference_new_client(input_data, input_name, output_name)
        else:
            return self.inference_old_client(input_data, input_name, output_name)

# 向後兼容的別名
BasePreprocessor = ModernBasePreprocessor
