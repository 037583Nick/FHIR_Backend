import fhirclient.models.diagnosticreport as DR
import fhirclient.models.servicerequest as SR
import fhirclient.models.observation as OBS
import fhirclient.models.fhirreference as fref
import fhirclient.models.attachment as ATT
import fhirclient.models.fhirdate as fd
import fhirclient.models.coding as Coding

from io import BytesIO
import base64
import fitz
import json
import os
from datetime import datetime, timedelta, timezone
import pytz
from fhirclient import server

FHIR_SERVER_URL = os.environ.get("FHIR_SERVER_URL", "http://10.69.12.83:8080/fhir")
fhir_server = server.FHIRServer(None, FHIR_SERVER_URL)

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


def stemiInferencer(dr):
    # 延遲導入以避免循環依賴
    from .inference import stemiInf
    
    baseOn = dr.basedOn
    # srList = SR.ServiceRequest.where({'identifier':f'{baseOn[0].identifier.system}|{baseOn[0].identifier.value}'}).perform_resources(fhir_server)
    # if(len(srList) > 0):
    #     sr = srList[-1]
    # else:
    #     return 'continue'
    sr = SR.ServiceRequest.read(baseOn[1].reference.split("/")[-1], fhir_server)

    for item in sr.contained:
        if item.id == sr.supportingInfo[0].reference[1:]:
            binary = item
            break
    xmlFilelike = BytesIO(base64.b64decode(binary.data))

    report, opt, img, raw_out = stemiInf(xmlFilelike)
    raw_out = {i[0][0]: i[0][1] for i in raw_out}

    imgByte = base64.b64decode(img)
    doc = fitz.open()
    doc.insert_page(0, height=400)
    page = doc.load_page(0)

    p = fitz.Point(10, 330)
    rc = page.insert_text(
        p,  # bottom-left of 1st char
        report.replace("<br>", "\n"),  # the text (honors '\n')
    )

    y = 20
    rect = fitz.Rect(0, y, page.rect.width, 292 + y)
    page.insert_image(rect, stream=imgByte)
    pdf = BytesIO()
    doc.save(pdf)
    att = ATT.Attachment()
    att.contentType = "application/pdf"
    pdf.seek(0)
    att.data = base64.b64encode(pdf.read()).decode("utf-8")

    # print(os.listdir())
    obsjs = json.load(open("app/emptyOBS/stemi.obs.json"))
    obs = OBS.Observation(obsjs)

    obs.component[0].interpretation[0].coding[0].code = (
        "A" if raw_out["STEMI"] >= 0.5 else "N"
    )
    obs.component[0].interpretation[0].coding[0].display = (
        "Abnormal" if raw_out["STEMI"] >= 0.5 else "Normal"
    )
    obs.component[0].valueQuantity.value = float(f"{raw_out['STEMI'] * 100:.2f}")

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
        obs.component[1].valueQuantity.value = float(f"{raw_out[disease] * 100:.2f}")

    obs.note[0].text = report.replace("<br>", "\n")

    dr.contained = [obs]
    result = fref.FHIRReference()
    result.reference = "#anObservation"
    dr.result = [result]
    dr.presentedForm = [att]

    issued = fd.FHIRDate()
    issued.date = datetime.now(pytz.timezone("Asia/Taipei"))
    dr.issued = issued

    dr.text = None
    dr.conclusion = None
    dr.status = "final"
    resp = dr.update(fhir_server)
    return resp
