import collections
import os
from io import StringIO

# 直接導入舊版 ECG 處理器，按照 oldstemi.py 的方式
from ..AI import ECG_AllPreprocessor

# 從環境變數讀取 gRPC 伺服器地址，如果沒有則使用新版地址
GRPC_SERVER_ADDRESS = os.getenv("GRPC_SERVER_ADDRESS", "10.69.12.83:8006")

STEMI_ICD_DICT = {
    "AFIB": [
        {"icd": "I48.0", "display": "Paroxysmal atrial fibrillation"},
        {"icd": "I48.1", "display": "Persistent atrial fibrillation"},
        {"icd": "I48.2", "display": "Chronic atrial fibrillation"},
    ],
    "AFL": [
        {"icd": "I48.3", "display": "Typical atrial flutter"},
        {"icd": "I48.4", "display": "Atypical atrial flutter"},
    ],
    "APB": [{"icd": "I49.1", "display": "Atrial fibrillation and flutter"}],
    "BIGEMINY": [{"icd": "R00.8", "display": "Other abnormalities of heart beat"}],
    "CHB": [{"icd": "I44.2", "display": "Atrioventricular block, complete"}],
    "EAR": [{"icd": "I49.8", "display": "Other specified cardiac arrhythmias"}],
    "FRAV": [{"icd": "I44.0", "display": "Atrioventricular block, first degree"}],
    "PSVT": [
        {"icd": "I47.1", "display": "Supraventricular tachycardia"},
        {"icd": "I47.2", "display": "Ventricular tachycardia"},
        {"icd": "I47.9", "display": "Paroxysmal tachycardia, unspecified"},
    ],
    "SAV": [{"icd": "I44.1", "display": "Atrioventricular block, second degree"}],
    "ST": [{"icd": "R00.0", "display": "Tachycardia, unspecified"}],
    "VPB": [{"icd": "I49.3", "display": "Ventricular premature depolarization"}],
    "SECAV1": [{"icd": "I44.1", "display": "Atrioventricular block, second degree"}],
}


def check_muse_stemi(xd):
    Diag = xd['RestingECG']['OriginalDiagnosis']['DiagnosisStatement']
    if isinstance(Diag, collections.OrderedDict):
        diag = Diag['StmtText']
        #         print('OrderedDict')
        #         print(Diag)
        return 0.0
    elif isinstance(Diag, list):
        diag = [f['StmtText'] for f in Diag if isinstance(f['StmtText'], str)]
        diag = ' '.join(diag)
        if ('STEMI' in diag):
            return 1.0
        else:
            return 0.0


def ekg_opt_report(raw_data):
    ekg_data, stemi_data = raw_data
    ekg_label, ekg_value = ekg_data[0]
    _, stemi_value = stemi_data[0]
    stemi_report_text = '是' if stemi_value > 0.5 else '否'
    stemi_report_value = stemi_value if stemi_value > 0.5 else 1 - stemi_value
    ekg_names = {'AFIB': 'Atrial Fibrillation ', 'AFL': 'Atrial Flutter',
                 'APB': 'Atrial Premature Beat ', 'BIGEMINY': 'Ventricular Bigeminy',
                 'CHB': 'Complete Heart Block ', 'EAR': 'Ectopic Atrial Rhythm',
                 'FRAV': 'First Degree AV Block ', 'NSR': 'Normal Sinus Rhythm',
                 'PSVT': 'Paroxysmal Supraventricular Tachycardia', 'SAV': 'Second Degree AV Block',
                 'ST': 'Sinus Tachycardia', 'VPB': 'Ventricular Premature Beat',
                 'SECAV1': 'Second Degree AV Block Type 1'}
    ekg_report_text = ekg_names.get(ekg_label)

    report = f"""
    ECG AI 輔助判讀報告

    - 心律：{ekg_report_text} (機率{">" if ekg_value > 0.95 else ""}{min(ekg_value, 0.95) * 100:.2f}%)
    - 心肌梗塞(STEMI)：{stemi_report_text} (機率{">" if stemi_report_value > 0.95 else ""}{min(stemi_report_value, 0.95) * 100:.2f}%)

    ----------------------------------
    說明
    (1)此判讀結果僅用於輔助醫師心電圖判讀，並不作為最後診斷之唯一依據。
    (2)本產品僅適用於成人患者，且不適用心律調節器病人。
    (3)心律包含13種常見心律不整判讀。
    (4)本輔助判讀已通過TFDA 認證，達到97%準確率。

    Powered by 長佳智能/人工智慧醫學診斷中心"""
    return report


def inference(filelike):
    # 直接使用 AI 推論，移除所有模擬數據邏輯 (按照 oldstemi.py 的方式)
    filelike.seek(0)
    content = filelike.read()
    
    # 處理字符串或字節數據
    if isinstance(content, bytes):
        stemi_project = StringIO(content.decode('utf-8'))
    else:
        stemi_project = StringIO(content)
        
    # 直接呼叫 AI，不使用模擬數據
    imgproc = ECG_AllPreprocessor(stemi_project, server=GRPC_SERVER_ADDRESS)
    encoded_image, report_text, raw_out, forER_Alert = imgproc.get_results()

    opt_report_text = ekg_opt_report(raw_data=raw_out)

    return report_text, opt_report_text, encoded_image, raw_out

