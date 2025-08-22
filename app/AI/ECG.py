from .base import BasePreprocessor
import numpy as np
import xmltodict
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO
# from googletrans import Translator

#  可能是長佳的  心律不整模型   8導程的


class ECGPreprocessor(BasePreprocessor):
    def __init__(self, fn, server=None):
        super().__init__(fn, model_name="ecg_multicat12", server=server)

    def get_results(self, lang="en"):
        proc_img = self.preprocess_image()
        outs = self.infer_one([proc_img])
        label, value = outs[0]
        return (
            self.postprocess_image(),
            self.postprocess_text(label, value, lang),
            [(label, value)],
        )

    # Load Image function
    def load_image(self, fn):
        # with open(fn, encoding="utf-8") as f:
        fn.seek(0)
        x = fn.read()
        xd = xmltodict.parse(x)
        wavedata = dict()
        for w in xd["RestingECG"]["Waveform"][1]["LeadData"]:
            wavedata[w["LeadID"]] = np.frombuffer(
                base64.b64decode(w["WaveFormData"]), dtype=np.int16
            ) * (float(w["LeadAmplitudeUnitsPerBit"]) / 1000)
        wavedata["AVR"] = -1 * ((wavedata["I"] + wavedata["II"]) / 2)
        wavedata["AVL"] = wavedata["I"] - wavedata["II"] / 2
        wavedata["AVF"] = wavedata["II"] - wavedata["I"] / 2
        wavedata["III"] = wavedata["II"] - wavedata["I"]
        return wavedata

    # Return a preprocessed image, ready for TRT Server
    def preprocess_image(self):
        wavedata = self.image
        stacked = np.stack(
            [
                wavedata["I"],
                wavedata["II"],
                wavedata["V1"],
                wavedata["V2"],
                wavedata["V3"],
                wavedata["V4"],
                wavedata["V5"],
                wavedata["V6"],
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

    def postprocess_text(self, label, confidence, lang="en"):
        report_text = f"{label}: {confidence*100:.2f}%"
        # if lang == "cn":
        #     translate = Translator()
        #     report_text = translate.translate(report_text, dest="zh-CN")
        #     return report_text.text
        return report_text
