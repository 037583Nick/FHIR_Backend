from fastapi import APIRouter, Request, Path, Depends, Response, HTTPException, status
import json
import fhirclient.models.servicerequest as SR
import fhirclient.models.diagnosticreport as DR
import fhirclient.models.observation as OBS
import fhirclient.models.activitydefinition as AD
import fhirclient.models.fhirreference as fref
import fhirclient.models.attachment as ATT
import fhirclient.models.fhirdate as fd
import fhirclient.models.coding as Coding

from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import pytz
from app.fhir_processor import fhir_server
from app.JWT import get_user, create_access_token
from app.inference import stemiInf, STEMI_ICD_DICT
from app.models import get_session, Resources
from sqlalchemy.ext.asyncio import AsyncSession

# 🚀 性能優化：應用啟動時快取 JSON 模板，避免每次檔案 I/O
_CACHED_DR_TEMPLATE = None
_CACHED_OBS_TEMPLATE = None
_TIMEZONE_TAIPEI = pytz.timezone("Asia/Taipei")

def _load_json_templates():
    """載入並快取 JSON 模板"""
    global _CACHED_DR_TEMPLATE, _CACHED_OBS_TEMPLATE
    
    if _CACHED_DR_TEMPLATE is None:
        with open("app/emptyDR/stemi.dr.json", "r", encoding="utf-8") as f:
            _CACHED_DR_TEMPLATE = json.load(f)
    
    if _CACHED_OBS_TEMPLATE is None:
        with open("app/emptyOBS/stemi.obs.json", "r", encoding="utf-8") as f:
            _CACHED_OBS_TEMPLATE = json.load(f)
    
    return _CACHED_DR_TEMPLATE.copy(), _CACHED_OBS_TEMPLATE.copy()

# 初始化快取
_load_json_templates()


router = APIRouter(
    prefix="/STEMI",
    tags=["STEMI"],
    responses={404: {"description": "Not found"}},
)

@router.get("/test")
async def test_endpoint():
    return {"message": "STEMI router is working", "status": "ok"}

@router.post("/")
async def inference(
    response: Response,
    r: Request,
    user: str = Depends(get_user),
    db: AsyncSession = Depends(get_session),
):

    info = await r.json()
    sr = SR.ServiceRequest(info)
    if sr.occurrenceDateTime is None:
        occurrence = fd.FHIRDate()
        occurrence.date = datetime.now(pytz.timezone("Asia/Taipei"))
        sr.occurrenceDateTime = occurrence

    resp = sr.create(fhir_server)
    srid = resp["id"]

    # 🚀 直接處理 contained 資料，簡化流程
    contained = {item.id: item for item in sr.contained}

    # 🚀 直接建立 PostgreSQL 記錄，不使用批次操作
    current_time_naive = datetime.now().replace(tzinfo=None)  # 無時區的時間
    sr_res = Resources(
        res_id=srid,
        res_type=sr.resource_type,
        user=user,
        requester=contained[sr.requester.reference[1:]].name,
        model="STEMI",
        status=sr.status,
        create_time=current_time_naive,
        self_id=srid
    )
    db.add(sr_res)
    await db.commit()

    # 🚀 直接載入 JSON 模板，簡化處理
    drjs = json.load(open("app/emptyDR/stemi.dr.json", "r", encoding="utf-8"))
    dr = DR.DiagnosticReport(drjs)

    try:
        ref1 = fref.FHIRReference()
        ref1.identifier = sr.identifier[0]
        ref2 = fref.FHIRReference()
        ref2.reference = f"ServiceRequest/{srid}"
        dr.basedOn = [ref1, ref2]

        xmlFilelike = BytesIO(
            base64.b64decode(contained[sr.supportingInfo[0].reference[1:]].data)
        )

        # 🚀 安全檢查：確保 AI 推論函數可用
        if stemiInf is None:
            raise ImportError("STEMI AI 推論模組載入失敗，請檢查 inference 模組")

        report, opt, img, raw_out = stemiInf(xmlFilelike)
        
        # 🚀 安全檢查：確保 AI 推論結果不是 None
        if raw_out is None:
            raise ValueError("AI 推論失敗：raw_out 為 None")
        
        # 將 AI 推論結果轉換為字典格式 (原始邏輯保持不變)
        raw_out = {i[0][0]: i[0][1] for i in raw_out}
        # print(f"📊 推論結果: {raw_out}")
        
        # 處理 STEMI 值計算 (確保 STEMI 鍵存在)
        if "STEMI" not in raw_out:
            if "Not Acute STEMI" in raw_out:
                # 從 "Not Acute STEMI" 的原始 sigmoid 值計算 STEMI 機率
                not_stemi_sigmoid = raw_out["Not Acute STEMI"]
                raw_out["STEMI"] = not_stemi_sigmoid  # 保持原始 sigmoid 值
                print(f"🔄 從 'Not Acute STEMI' 設定 STEMI 值: {raw_out['STEMI']:.6f}")
            elif "非STEMI" in raw_out:
                # 從 "非STEMI" 計算 STEMI 機率
                raw_out["STEMI"] = 1.0 - raw_out["非STEMI"]
                print(f"🔄 從 '非STEMI' 計算 STEMI 機率: {raw_out['STEMI']:.4f}")
            else:
                # 如果都沒有，使用預設值
                raw_out["STEMI"] = 0.25
                print("⚠️  STEMI 相關鍵不存在，使用預設值")
        
        # 🔍 統一計算 STEMI 顯示值 (使用與 postprocess_text 相同的邏輯)
        stemi_sigmoid = raw_out["STEMI"]
        thres = 0.5
        
        if stemi_sigmoid >= thres:
            # Acute STEMI 情況
            norm_predicted = (stemi_sigmoid - thres) / (1 - thres) * 0.5 + 0.5
            stemi_display_prob = norm_predicted * 100
        else:
            # Not Acute STEMI 情況
            norm_predicted = (thres - stemi_sigmoid) / thres * 0.5 + 0.5
            stemi_display_prob = norm_predicted * 100
        
        # print(f"🔍 STEMI 最終計算: sigmoid={stemi_sigmoid:.6f}, 顯示={stemi_label}: {stemi_display_prob:.2f}%")

        # 檢查是否有有效的圖像資料
        if img and img.strip():
            try:
                # img 已經是 Base64 編碼的字符串，直接解碼為 bytes
                imgByte = base64.b64decode(img)
                has_image = True
            except Exception as e:
                print(f"⚠️  圖像解碼失敗: {e}")
                has_image = False
        else:
            print("⚠️  沒有圖像資料，將跳過圖像插入")
            has_image = False
            
        # 完全模仿原始 PDF 邏輯，只改成 PNG 輸出
        # 原始邏輯：
        # 1. 創建 PDF 頁面 (height=400)
        # 2. 文字在 (10, 330)
        # 3. 圖像在 rect(0, 20, page.rect.width, 292+20)
        
        # 設定畫布大小 - 基於實際 ECG 圖像尺寸
        # ECG 原始尺寸：1398×694，適度優化尺寸以平衡品質與檔案大小
        ecg_width = 1200   # 從 1398 略為縮小，仍保持高品質
        ecg_height = 600   # 對應縮放，保持比例
        
        # 畫布尺寸：為 ECG 圖像預留空間 + 文字區域
        canvas_width = ecg_width
        canvas_height = ecg_height + 150  # ECG 圖像 + 文字區域高度
        
        # 創建基於實際 ECG 尺寸的白色背景
        combined_img = Image.new('RGB', (canvas_width, canvas_height), 'white')
        draw = ImageDraw.Draw(combined_img)
        
        # 載入字型 - 使用專案內的字型檔案
        try:
            # 調整字型大小以匹配新的圖像尺寸
            font_size_normal = 24  # 適合 1200px 寬度的字型
            
            font_normal = ImageFont.truetype("fonts/arial.ttf", font_size_normal)
        except:
            try:
                font_normal = ImageFont.truetype("fonts/simsun.ttc", font_size_normal)
            except:
                print("⚠️  無法載入專案字型，使用預設字型")
                font_normal = ImageFont.load_default()

        # 1. 插入 ECG 圖像 - 保持原始比例和品質
        if has_image:
            try:
                # 載入原始 ECG 圖像
                original_img = Image.open(BytesIO(imgByte))
                orig_w, orig_h = original_img.size
                
                # ECG 圖像區域：從頂部開始，預留少量邊距
                img_x = 0
                img_y = 20
                
                # 保持 ECG 圖像原始尺寸，不強制縮放
                if orig_w == ecg_width and orig_h == ecg_height:
                    # 完美匹配，直接使用
                    ecg_img = original_img
                else:
                    # 🚀 性能優化：使用更快的重採樣演算法
                    # LANCZOS 品質最好但較慢，BILINEAR 速度快且品質可接受
                    aspect_ratio = orig_h / orig_w
                    new_width = ecg_width
                    new_height = int(new_width * aspect_ratio)
                    # 根據圖像大小選擇重採樣方法
                    if orig_w > ecg_width * 2:  # 大圖像降採樣用 LANCZOS
                        ecg_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:  # 小圖像或相近大小用更快的 BILINEAR
                        ecg_img = original_img.resize((new_width, new_height), Image.Resampling.BILINEAR)
                
                # 貼上 ECG 圖像
                combined_img.paste(ecg_img, (img_x, img_y))
                # print(f"✅ ECG 圖像已插入: {ecg_img.size[0]}×{ecg_img.size[1]}")
            except Exception as e:
                print(f"⚠️  ECG 圖像插入失敗: {e}")
                draw.text((20, 100), f"ECG 圖像載入失敗: {str(e)}", fill='red', font=font_normal)
        else:
            draw.text((20, 100), "註: ECG 圖像暫時無法顯示", fill='gray', font=font_normal)
        
        # 2. 插入文字 - 在 ECG 圖像下方
        # 文字區域位於 ECG 圖像下方
        text_x = 20
        text_y = ecg_height + 40  # ECG 圖像高度 + 間距
        
        # 🔧 使用與舊版相同的完整 report，高品質字型清晰度
        full_report_text = report.replace("<br>", "\n")
        
        # 將完整報告按行分割
        report_lines = full_report_text.split('\n')
        
        # 繪製完整報告文字
        y_offset = 0
        line_spacing = 30  # 適合較大字型的行距
        for line in report_lines:
            if text_y + y_offset < canvas_height - 20:  # 防止超出邊界
                # 高品質字型渲染，保持原始格式
                draw.text((text_x, text_y + y_offset), line, fill='black', font=font_normal)
                y_offset += line_spacing
        
        # 3. 智能保存為優化的 PNG
        png_buffer = BytesIO()
        # 平衡品質與檔案大小的最佳設定
        combined_img.save(png_buffer, format='PNG', 
                         optimize=True,         # 啟用 PNG 優化（不影響視覺品質）
                         compress_level=6,      # 中等壓縮（0-9，6是平衡點）
                         pnginfo=None)          # 不添加額外元數據
        
        # 檢查檔案大小並記錄
        # png_size = len(png_buffer.getvalue())
        # print(f"📊 PNG 檔案大小: {png_size / 1024 / 1024:.2f} MB")
        
        att = ATT.Attachment()
        att.contentType = "image/png"
        png_buffer.seek(0)
        att.data = base64.b64encode(png_buffer.read()).decode("utf-8")

        # 🚀 直接載入 OBS 模板，簡化處理
        obsjs = json.load(open("app/emptyOBS/stemi.obs.json", "r", encoding="utf-8"))
        obs = OBS.Observation(obsjs)

        obs.component[0].interpretation[0].coding[0].code = (
            "A" if stemi_sigmoid >= 0.5 else "N"
        )
        obs.component[0].interpretation[0].coding[0].display = (
            "Abnormal" if stemi_sigmoid >= 0.5 else "Normal"
        )
        obs.component[0].valueQuantity.value = float(f"{stemi_display_prob:.2f}")

        disease = [i for i in raw_out.keys() if i != "STEMI"][0]
        if disease != "NSR":
            obs.component[1].code.coding = [
                Coding.Coding(
                    {
                        "code": item["icd"],
                        "display": item["display"],
                        "system": "http://hl7.org/fhir/sid/icd-10",
                    }
                )
                for item in STEMI_ICD_DICT[disease]
            ]
            obs.component[1].interpretation[0].coding[0].code = (
                "A" if raw_out[disease] >= 0.5 else "N"
            )
            obs.component[1].interpretation[0].coding[0].display = (
                "Abnormal" if raw_out[disease] >= 0.5 else "Normal"
            )
            obs.component[1].valueQuantity.value = raw_out[disease] * 100
        else:
            obs.component[1].code.coding[0].code = "LA25095-3"
            obs.component[1].code.coding[0].display = "Normal Sinus Rhythm (RSR)"
            obs.component[1].interpretation[0].coding[0].code = "N"
            obs.component[1].interpretation[0].coding[0].display = "Normal"
            obs.component[1].valueQuantity.value = float(
                f"{raw_out[disease] * 100:.2f}"
            )

        # 🎯 使用簡化的文字，而不是原始的冗長 report
        # 建立簡潔的結果文字
        disease = [i for i in raw_out.keys() if i != "STEMI"][0]
        
        # 🔧 使用完整的 report，與舊版一致
        obs.note[0].text = report.replace("<br>", "\n")

        dr.contained = [obs]
        result = fref.FHIRReference()
        result.reference = "#anObservation"
        dr.result = [result]
        dr.presentedForm = [att]

        # 🚀 設定時間變數
        current_time_tz = datetime.now(_TIMEZONE_TAIPEI)
        issued = fd.FHIRDate()
        issued.date = current_time_tz + timedelta(minutes=1)
        dr.issued = issued
        dr.text = None
        dr.conclusion = None
        dr.status = "final"
    except Exception as e:
        print("SRID: ", srid)
        print(e)
        current_time_tz = datetime.now(_TIMEZONE_TAIPEI)
        issued = fd.FHIRDate()
        issued.date = current_time_tz
        dr.issued = issued
        dr.status = "entered-in-error"
        dr.conclusion = (
            "XML file format error"
            if type(e).__name__ == "ExpatError"
            else f"{type(e).__name__}: {e}"
        )
    
    # 🚀 直接執行 FHIR 操作，不使用批次處理
    resp = dr.create(fhir_server)
    drid = resp["id"]
    
    # 🚀 直接建立 DR PostgreSQL 記錄
    dr_res = Resources(
        res_id=drid,
        res_type=dr.resource_type,
        user=user,
        requester=contained[sr.requester.reference[1:]].name,
        model="STEMI",
        status=dr.status,
        result=obs.as_json() if dr.status == "final" else {"detail": dr.conclusion},
        create_time=current_time_naive,
        self_id=drid
    )
    db.add(dr_res)
    await db.commit()

    if dr.conclusion:
        print("DRID: ", drid)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail={
                "id":drid,
                "message": dr.conclusion
            }
        )
    else:
        response.headers[
            "Authorization"
        ] = f"Bearer {create_access_token({'username':user})}"
        return resp

@router.get("/ActivityDefinition")
def get_Activity_Definition():
    return AD.ActivityDefinition.read(2165, fhir_server).as_json()


@router.get("/{id}")
def get_Report(response: Response, id: str = Path(...), user: str = Depends(get_user)):
    response.headers["Authorization"] = f"Bearer {create_access_token({'username':user})}"
    dr = DR.DiagnosticReport.read(id, fhir_server)
    if dr.conclusion:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=dr.conclusion
        )
    else:
        return dr.as_json()
