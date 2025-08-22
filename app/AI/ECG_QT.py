from .base import BasePreprocessor
import numpy as np
import matplotlib.pyplot as plt
import base64
from io import BytesIO

ECG_FIELD_NAMES2 = [
    'I', 'II', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'AVR', 'AVL', 'AVF', 'III'
]

class ECG_QTPreprocessor(BasePreprocessor):
    def __init__(self, fn, server=None):
        # by是孟軒之前的組長，by大哥
        super().__init__(fn, model_name="ecg_stemi_by", server=server)
        self.fn = fn  # 存儲 fn 作為實例變量


    # 覆蓋基類中的 load_image 方法，避免 NotImplementedError
    # 如果不用這個，他會去調用父類的load_image方法，但是父類的load_image方法是raise NotImplementedError
    # 用這樣只會針對這個class的load_image方法
    def load_image(self, fn):
        xd = fn  # 使用存儲的 fn
        scaler_ = xd['AnnotatedECG']['component']['series']['component']['sequenceSet']['component'][1]['sequence']['value']['scale']['@value']
        scaler = np.float64(scaler_) * 1000
        wavedata = {}
        channelBaselines = {}
        i = 0
        for idx in [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 9]:
            text = xd['AnnotatedECG']['component']['series']['component']['sequenceSet']['component'][idx]['sequence']['value']['digits']
            ecg_text = np.array(text.split(' ')).astype(int)
            field = ECG_FIELD_NAMES2[i]
            channelBaselines[field] = xd['AnnotatedECG']['component']['series']['component']['sequenceSet']['component'][idx]['sequence']['value']['origin']['@value']
            wavedata[field] = list(
                    map(lambda x: int(((x) + float(channelBaselines[field])) * scaler),
                        ecg_text))[::2]
            wavedata[field] = np.array(wavedata[field]).astype(np.float64)/1000/1000
            i = i+1
        return wavedata

    def get_results(self,lang="en"):
        proc_img = self.preprocess_image()
        outs = self.infer_one([proc_img])
        label, value = outs[0]
        forER_Alert = False
        return (
            self.postprocess_image(),
            self.postprocess_text(value, lang=lang),
            [(label, value)],
            forER_Alert
        )

    def preprocess_image(self):
        wavedata = self.load_image(self.fn)
        stacked = np.stack(
            [
                wavedata["I"],
                wavedata["II"],
                wavedata["AVR"],
                wavedata["AVL"],
                wavedata["AVF"],
                wavedata["III"],                
                wavedata["V1"],
                wavedata["V2"],
                wavedata["V3"],
                wavedata["V4"],
                wavedata["V5"],
                wavedata["V6"]
            ],
            -1,
        ).astype(np.float32)
        return stacked


    # Return a postprocessed image in base64 string, ready to be displayed on website
    def postprocess_image(self):
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
        # Lead I Top:
        # H Offset: 6, V Offset: 115
        ecg_offset = 1
        h_offset = 6
        v_offset = 115
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["I"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "I",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead II Top:
        # H Offset: 6, V Offset: 82
        v_offset = 82
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["II"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "II",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead III Top:
        # H Offset: 6, V Offset: 48
        v_offset = 48
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["III"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "III",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead II Bottom:
        # H Offset: 6, V Offset: 13
        v_offset = 13
        plt.plot(
            (np.arange(5000) * 0.05 + h_offset),
            wavedata["II"] * 10 + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "II",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead aVR Top:
        # H Offset: 68, V Offset: 115
        ecg_offset = 2
        h_offset = 68
        v_offset = 115
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["AVR"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "aVR",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead aVL Top:
        # H Offset: 68, V Offset: 82
        v_offset = 82
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["AVL"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "aVL",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead aVF Top:
        # H Offset: 68, V Offset: 48
        v_offset = 48
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["AVF"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "aVF",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V1 Top:
        # H Offset: 132, V Offset: 115
        ecg_offset = 3
        h_offset = 132
        v_offset = 115
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V1"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V1",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V2 Top:
        # H Offset: 132, V Offset: 82
        v_offset = 82
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V2"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V2",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V3 Top:
        # H Offset: 132, V Offset: 48
        v_offset = 48
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V3"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V3",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V4 Top:
        # H Offset: 194, V Offset: 115
        ecg_offset = 4
        h_offset = 194
        v_offset = 115
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V4"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V4",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V5 Top:
        # H Offset: 194, V Offset: 82
        v_offset = 82
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V5"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V5",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        # Lead V6 Top:
        # H Offset: 194, V Offset: 48
        v_offset = 48
        plt.plot(
            (np.arange(1230) * 0.05 + h_offset),
            wavedata["V6"][1250 * (ecg_offset - 1) : 1250 * ecg_offset - 20] * 10
            + v_offset,
            color="black",
            linewidth=0.5,
        )
        plt.text(
            h_offset,
            v_offset - 3,
            "V6",
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=18,
        )

        plt.axis("off")
        # plt.show()
        jpg_bytes = BytesIO()
        plt.savefig(jpg_bytes, dpi=150, format="png", bbox_inches="tight")
        plt.close()
        jpg_bytes.seek(0)

        return base64.b64encode(jpg_bytes.getvalue()).decode()

    def postprocess_text(self, confidence, thres=0.5, lang="en"):
        if confidence >= thres and thres > 0 and thres < 1:
            norm_predicted = (confidence - thres) / (1 - thres) * 0.5 + 0.5
            report_text = f"Acute STEMI: {norm_predicted*100:.2f}%"
        if confidence < thres and thres > 0 and thres < 1:
            norm_predicted = (thres - confidence) / (thres) * 0.5 + 0.5
            report_text = f"Not Acute STEMI: {norm_predicted*100:.2f}%"

        #         report_text = f'{label}: {confidence*100:.2f}%'
        # if lang == "cn":
        #     translate = Translator()
        #     report_text = translate.translate(report_text, dest="zh-CN")
        #     return report_text.text
        return report_text

