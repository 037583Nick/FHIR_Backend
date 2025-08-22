import os
from .modern_ecg_stemi import ModernECG_STEMIPreprocessor

class ModernECG_AllPreprocessor:
    """現代化的 ECG 全功能預處理器，避免舊版依賴"""
    
    def __init__(self, fn, server=None):
        # 設置環境變數避免 protobuf 衝突
        os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
        
        # 只使用 STEMI 處理器（主要功能）
        self.stemi_processor = ModernECG_STEMIPreprocessor(fn, server)
        
        # 暫時不實現其他處理器，避免舊版依賴
        self.fn = fn
        self.server = server
            server = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")
        
        try:
            # 使用現代化的 STEMI 預處理器
            self.imgproc2 = ModernECG_STEMIPreprocessor(fn, server)
            print("✅ 現代化 STEMI 預處理器初始化成功")
            
            # 嘗試使用舊版 ECG 預處理器（用於心律分析）
            try:
                self.imgproc = ECGPreprocessor(fn, server)
                print("✅ ECG 心律預處理器初始化成功")
                self.has_rhythm_analysis = True
            except Exception as e:
                print(f"⚠️  ECG 心律預處理器初始化失敗: {e}")
                print("   將僅提供 STEMI 分析")
                self.imgproc = None
                self.has_rhythm_analysis = False
                
        except Exception as e:
            print(f"❌ 預處理器初始化失敗: {e}")
            raise

    def get_results(self, lang="zh"):
        """獲取完整的 ECG 分析結果"""
        try:
            # 獲取 STEMI 分析結果
            stemi_img, stemi_txt, stemi_qa, forER_Alert = self.imgproc2.get_results(lang)
            
            if self.has_rhythm_analysis and self.imgproc is not None:
                try:
                    # 獲取心律分析結果
                    rhythm_img, rhythm_txt, rhythm_qa = self.imgproc.get_results()
                    
                    # 合併結果
                    combined_text = self.postprocess_text(rhythm_txt, stemi_txt)
                    combined_qa = [rhythm_qa, stemi_qa[0]]  # rhythm_qa 已經是 tuple，stemi_qa 是 list
                    
                    return stemi_img, combined_text, combined_qa, forER_Alert
                    
                except Exception as e:
                    print(f"❌ 心律分析失敗: {e}")
                    print("   返回僅 STEMI 分析結果")
                    
            # 如果心律分析不可用，僅返回 STEMI 分析
            return stemi_img, stemi_txt, stemi_qa, forER_Alert
            
        except Exception as e:
            print(f"❌ 獲取結果失敗: {e}")
            raise

    def postprocess_text(self, rhythm_text, stemi_text):
        """合併心律和 STEMI 分析文字"""
        report_text = f"""
        ECG AI 輔助分析報告
        
        === 心律分析 ===
        {rhythm_text}
        
        === STEMI 分析 ===
        {stemi_text}
        
        === 綜合建議 ===
        請由專業醫師結合臨床症狀進行最終診斷
        此AI分析結果僅供參考，不可作為診斷依據
        """
        
        return report_text.strip()

# 向後兼容的別名
ECG_AllPreprocessor = ModernECG_AllPreprocessor
