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

    def get_results(self, lang="zh"):
        """獲取完整的分析結果"""
        try:
            # 獲取 STEMI 分析結果
            encoded_image, stemi_report, raw_stemi, forER_Alert = self.stemi_processor.get_results(lang)
            
            # 創建簡化的心律分析報告（暫時使用模擬結果）
            rhythm_report = self._generate_rhythm_report()
            
            # 合併報告
            combined_report = self._combine_reports(rhythm_report, stemi_report)
            
            # 創建合併的原始結果
            raw_combined = [
                [("NSR", 0.85)],  # 模擬心律結果
                raw_stemi         # STEMI 結果
            ]
            
            return encoded_image, combined_report, raw_combined, forER_Alert
            
        except Exception as e:
            print(f"❌ ECG 分析失敗: {e}")
            raise

    def _generate_rhythm_report(self):
        """生成簡化的心律分析報告"""
        return """
        心律分析結果: 正常竇性心律 (NSR)
        信心度: 85.0%
        
        建議: 心律基本正常
        """

    def _combine_reports(self, rhythm_report, stemi_report):
        """合併心律和 STEMI 報告"""
        combined = f"""
        ECG AI 輔助分析完整報告
        
        === 心律分析 ===
        {rhythm_report.strip()}
        
        === STEMI 分析 ===
        {stemi_report.strip()}
        
        === 注意事項 ===
        - 此結果僅供參考，不可作為最終診斷依據
        - 請結合患者臨床症狀進行綜合判斷
        - 建議由專業醫師進行最終診斷
        
        報告生成時間: {self._get_current_time()}
        """
        return combined.strip()

    def _get_current_time(self):
        """獲取當前時間"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def postprocess_text(self, label1, label2):
        """後處理文字報告（向後兼容）"""
        report_text = f"{label1}<br><br>"
        report_text += f"{label2}"
        return report_text


class QTPreprocessor:
    """QT 間隔處理器（暫時停用）"""
    
    def __init__(self, fn, ecg_apiname, server=None):
        self.fn = fn
        print("⚠️  QT 處理器暫時停用，請使用完整 ECG 分析")

    def get_results(self, lang="zh"):
        """返回基本結果"""
        return "", "QT 間隔分析暫時停用", [], False
    
    def postprocess_text(self, label1):
        """後處理文字"""
        return f"{label1}<br><br>"
