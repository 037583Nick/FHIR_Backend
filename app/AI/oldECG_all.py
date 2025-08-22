from .ECG_STEMI import ECG_STEMIPreprocessor
from .ECG import ECGPreprocessor
from .ECG_QT import ECG_QTPreprocessor


class ECG_AllPreprocessor:
    def __init__(self, fn, server="10.24.211.151:30123"):
        self.imgproc = ECGPreprocessor(fn, server)
        self.imgproc2 = ECG_STEMIPreprocessor(fn, server)
        self.imgproc.__init__(fn, server=server)
        self.imgproc2.__init__(fn, server=server)

    def get_results(self, lang="en"):
        img, txt, qa = self.imgproc.get_results()
        _, txt2, qa2, forER_Alert = self.imgproc2.get_results()
        return img, self.postprocess_text(txt, txt2), [qa, qa2], forER_Alert

    def postprocess_text(self, label1, label2):
        report_text = f"{label1}<br><br>"
        report_text += f"{label2}"
        return report_text


class QTPreprocessor:
    def __init__(self, fn, ecg_apiname,server="10.24.211.151:30123"):
        self.fn = fn  # 保存初始化時的 fn
        self.imgproc = ECG_QTPreprocessor(fn, server)

    def get_results(self,lang="en"):
        encode_image, report_text, raw_out, forER_Alert = self.imgproc.get_results()
        return encode_image,self.postprocess_text(report_text), raw_out,forER_Alert
    
    def postprocess_text(self, label1):
        report_text = f"{label1}<br><br>"
        return report_text