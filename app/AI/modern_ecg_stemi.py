import numpy as np
import xmltodict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import os

class ModernECG_STEMIPreprocessor:
    """現代化的 ECG STEMI 預處理器，延遲導入 tritonclient"""
    
    def __init__(self, fn, server=None):
        self.fn = fn
        self.model_name = "ecg_stemi_by"
        self.image = self.load_image(fn)
        
        # gRPC 服務器地址
        if server is None:
            server = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")
        self.server = server
        
        # 延遲初始化 Triton 客戶端
        self.grpc_client = None
        self._init_triton_client()

    def _init_triton_client(self):
        """延遲初始化 Triton 客戶端"""
        try:
            # 設置環境變數
            os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
            
            # 在這裡才導入 tritonclient
            import tritonclient.grpc as grpcclient
            from tritonclient.utils import np_to_triton_dtype
            
            # 存儲導入的模組
            self.grpcclient = grpcclient
            self.np_to_triton_dtype = np_to_triton_dtype
            
            self.grpc_client = grpcclient.InferenceServerClient(
                url=self.server,
                verbose=False
            )
            
            # 檢查服務器和模型狀態
            if not self.grpc_client.is_server_ready():
                raise Exception("Triton server is not ready")
            
            if not self.grpc_client.is_model_ready(self.model_name):
                raise Exception(f"Model {self.model_name} is not ready")
            
            print(f"✅ 模型 {self.model_name} 已就緒")
            
        except Exception as e:
            print(f"❌ Triton 客戶端初始化失敗: {e}")
            raise

    def load_image(self, fn):
        """從 XML 載入 ECG 波形資料"""
        fn.seek(0)
        x = fn.read()
        xd = xmltodict.parse(x)

        wavedata = dict()
        
        # 檢查 Waveform 結構
        waveforms = xd["RestingECG"]["Waveform"]
        if isinstance(waveforms, list):
            # 如果是列表，使用第二個元素（索引1）
            lead_data_source = waveforms[1]["LeadData"] if len(waveforms) > 1 else waveforms[0]["LeadData"]
        else:
            # 如果是單個物件，直接使用
            lead_data_source = waveforms["LeadData"]
        
        # 確保 LeadData 是列表
        if not isinstance(lead_data_source, list):
            lead_data_source = [lead_data_source]

        for w in lead_data_source:
            wavedata[w["LeadID"]] = np.frombuffer(
                base64.b64decode(w["WaveFormData"]), dtype=np.int16
            ) * (float(w["LeadAmplitudeUnitsPerBit"]) / 1000)

        # 計算 augmented leads
        if "I" in wavedata and "II" in wavedata:
            wavedata["AVR"] = -1 * ((wavedata["I"] + wavedata["II"]) / 2)
            wavedata["AVL"] = wavedata["I"] - wavedata["II"] / 2
            wavedata["AVF"] = wavedata["II"] - wavedata["I"] / 2
            wavedata["III"] = wavedata["II"] - wavedata["I"]

        return wavedata

    def preprocess_image(self):
        """預處理 ECG 資料為模型輸入格式"""
        # 12導程順序
        ecg_leads = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        
        # 收集所有導程的資料
        ecg_matrix = []
        for lead in ecg_leads:
            if lead in self.image:
                lead_data = self.image[lead]
                # 確保長度為 5000
                if len(lead_data) >= 5000:
                    ecg_matrix.append(lead_data[:5000])
                else:
                    # 如果資料不足，填充零
                    padded_data = np.zeros(5000)
                    padded_data[:len(lead_data)] = lead_data
                    ecg_matrix.append(padded_data)
            else:
                # 如果導程資料缺失，填充零
                ecg_matrix.append(np.zeros(5000))
        
        # 轉換為 numpy 陣列 [5000, 12]
        ecg_array = np.array(ecg_matrix).T  # 轉置以得到 [5000, 12]
        
        # 添加 batch 維度 [1, 5000, 12]
        ecg_array = np.expand_dims(ecg_array, axis=0).astype(np.float32)
        
        return ecg_array

    def infer_one(self, input_data):
        """使用新版 tritonclient 執行推論"""
        try:
            # 準備輸入
            inputs = []
            inputs.append(self.grpcclient.InferInput(
                "input_1", 
                input_data.shape, 
                self.np_to_triton_dtype(input_data.dtype)
            ))
            inputs[0].set_data_from_numpy(input_data)

            # 準備輸出
            outputs = []
            outputs.append(self.grpcclient.InferRequestedOutput("dense_1/Sigmoid"))

            # 執行推論
            response = self.grpc_client.infer(
                model_name=self.model_name,
                inputs=inputs,
                outputs=outputs
            )

            # 獲取結果
            result = response.as_numpy("dense_1/Sigmoid")
            
            # 返回格式：[(label, probability)]
            probability = float(result[0][0])
            label = "STEMI" if probability > 0.5 else "非STEMI"
            
            return [(label, probability)]
            
        except Exception as e:
            print(f"❌ 推論失敗: {e}")
            raise

    def postprocess_image(self):
        """生成傳統醫療級 12-lead ECG 圖像（base64 編碼）"""
        try:
            wavedata = self.image
            X_MM = 268
            Y_MM = 129
            M_X_INCH = float(X_MM) / 25.4
            M_Y_INCH = float(Y_MM) / 25.4
            THIN_WIDTH = 0.04
            FAT_WIDTH = 0.2
            f = plt.figure(figsize=(M_X_INCH, M_Y_INCH), dpi=150)
            axes = f.add_axes((0, 0, 1, 1), frame_on=False)
            axes.set_xlim(-0.5, X_MM - 0.5)
            axes.set_ylim(-0.5, Y_MM - 0.5)

            def get_line_width(i):
                if i % 5 == 0:
                    return FAT_WIDTH
                else:
                    return THIN_WIDTH

            # 繪製 ECG 網格
            for i in range(0, X_MM):
                if i == (X_MM - 1):
                    axes.axvline(x=i, linewidth=FAT_WIDTH, color="red")
                else:
                    axes.axvline(x=i, linewidth=get_line_width(i), color="red")
            for i in range(0, Y_MM):
                if i == (Y_MM - 1):
                    axes.axhline(y=i, linewidth=FAT_WIDTH, color="red")
                else:
                    axes.axhline(y=i, linewidth=get_line_width(i), color="red")
            axes.set_xticks([])
            axes.set_yticks([])
            
            # Lead I Top: H Offset: 6, V Offset: 115
            ecg_offset = 1
            h_offset = 6
            v_offset = 115
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["I"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "I", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead II Top: H Offset: 6, V Offset: 82
            v_offset = 82
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["II"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "II", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead III Top: H Offset: 6, V Offset: 48
            v_offset = 48
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["III"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "III", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead II Bottom (長節律條): H Offset: 6, V Offset: 13
            v_offset = 13
            plt.plot(
                (np.arange(5000) * 0.05 + h_offset),
                wavedata["II"] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "II", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead aVR Top: H Offset: 68, V Offset: 115
            ecg_offset = 2
            h_offset = 68
            v_offset = 115
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["AVR"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "aVR", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead aVL Top: H Offset: 68, V Offset: 82
            v_offset = 82
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["AVL"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "aVL", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead aVF Top: H Offset: 68, V Offset: 48
            v_offset = 48
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["AVF"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "aVF", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V1 Top: H Offset: 132, V Offset: 115
            ecg_offset = 3
            h_offset = 132
            v_offset = 115
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V1"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V1", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V2 Top: H Offset: 132, V Offset: 82
            v_offset = 82
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V2"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V2", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V3 Top: H Offset: 132, V Offset: 48
            v_offset = 48
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V3"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V3", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V4 Top: H Offset: 194, V Offset: 115
            ecg_offset = 4
            h_offset = 194
            v_offset = 115
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V4"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V4", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V5 Top: H Offset: 194, V Offset: 82
            v_offset = 82
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V5"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V5", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            # Lead V6 Top: H Offset: 194, V Offset: 48
            v_offset = 48
            plt.plot(
                (np.arange(1230) * 0.05 + h_offset),
                wavedata["V6"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10 + v_offset,
                color="black", linewidth=0.5,
            )
            plt.text(h_offset, v_offset - 3, "V6", horizontalalignment="left", 
                    verticalalignment="top", fontsize=18,)

            plt.axis("off")
            
            # 轉換為 base64
            jpg_bytes = BytesIO()
            plt.savefig(jpg_bytes, dpi=150, format="png", bbox_inches="tight")
            plt.close()
            jpg_bytes.seek(0)

            return base64.b64encode(jpg_bytes.getvalue()).decode()
            
        except Exception as e:
            print(f"❌ 圖像生成失敗: {e}")
            return ""
            # 返回空圖像
            return ""

    def postprocess_text(self, probability, lang="en"):
        """生成診斷報告文字"""
        is_stemi = probability > 0.5
        confidence = probability if is_stemi else (1 - probability)
        
        if lang == "zh":
            if is_stemi:
                diagnosis = "疑似急性ST段抬高型心肌梗塞 (STEMI)"
                recommendation = "建議立即進行心導管檢查和治療"
            else:
                diagnosis = "未偵測到急性ST段抬高型心肌梗塞 (STEMI)"
                recommendation = "請結合臨床症狀和其他檢查進行綜合判斷"
        else:
            if is_stemi:
                diagnosis = "Suspected ST-Elevation Myocardial Infarction (STEMI)"
                recommendation = "Immediate cardiac catheterization recommended"
            else:
                diagnosis = "No ST-Elevation Myocardial Infarction (STEMI) detected"
                recommendation = "Please correlate with clinical symptoms and other examinations"

        report = f"""
        AI 輔助 ECG 分析報告
        
        診斷結果: {diagnosis}
        信心度: {confidence:.1%}
        
        建議: {recommendation}
        
        注意事項:
        - 此結果僅供參考，不可作為最終診斷依據
        - 請結合患者臨床症狀進行綜合判斷
        - 建議由專業醫師進行最終診斷
        """
        
        return report.strip()

    def get_results(self, lang="zh"):
        """獲取完整的分析結果"""
        try:
            # 預處理資料
            proc_img = self.preprocess_image()
            
            # 執行推論
            outs = self.infer_one(proc_img)
            label, value = outs[0]

            # 急診警報邏輯（暫時停用）
            forER_Alert = False

            return (
                self.postprocess_image(),      # base64 編碼的圖像
                self.postprocess_text(value, lang=lang),  # 診斷報告
                [(label, value)],              # 原始結果
                forER_Alert,                   # 急診警報
            )
            
        except Exception as e:
            print(f"❌ 獲取結果失敗: {e}")
            raise
