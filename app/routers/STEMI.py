from fastapi import APIRouter, Request, Path, Depends, Response, HTTPException, status
from fhirclient import server
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
import fitz
from datetime import datetime, timedelta, timezone
import pytz
from app.fhir_processor import fhir_server
from app.JWT import get_user, create_access_token
from app.inference import stemiInf, STEMI_ICD_DICT
from app.models import datetimeConverter, get_session, Resources,get_tryExcept_Moreinfo,mongo_client,mongo_client2
from sqlalchemy.ext.asyncio import AsyncSession
import os
import pymongo
from pymongo.errors import ServerSelectionTimeoutError


router = APIRouter(
    prefix="/STEMI",
    tags=["STEMI"],
    responses={404: {"description": "Not found"}},
)


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

    try:
        mongo_col = mongo_client["FHIR"]["resources"]
        # 嘗試連接主要 MongoDB
        mongo_client.admin.command('ping')
    except ServerSelectionTimeoutError as e:
        get_tryExcept_Moreinfo(e)
        mongo_col = mongo_client2["FHIR"]["resources"]

   # 儲存 ServiceRequest 至 MongoDB
    mongo_col.insert_one(datetimeConverter(dict(resp)))
    contained = {item.id: item for item in sr.contained}

    sr_res = Resources(
        res_id=srid,
        res_type=sr.resource_type,
        user=user,
        requester=contained[sr.requester.reference[1:]].name,
        model="STEMI",
        status=sr.status,
        create_time=datetime.now(),
        self_id=srid
    )
    db.add(sr_res)
    await db.commit()

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
            obs.component[1].valueQuantity.value = float(
                f"{raw_out[disease] * 100:.2f}"
            )

        obs.note[0].text = report.replace("<br>", "\n")

        dr.contained = [obs]
        result = fref.FHIRReference()
        result.reference = "#anObservation"
        dr.result = [result]
        dr.presentedForm = [att]

        issued = fd.FHIRDate()
        issued.date = datetime.now(pytz.timezone("Asia/Taipei")) + timedelta(minutes=1)
        dr.issued = issued
        dr.text = None
        dr.conclusion = None
        dr.status = "final"
    except Exception as e:
        print("SRID: ", srid)
        print(e)
        issued = fd.FHIRDate()
        issued.date = datetime.now(pytz.timezone("Asia/Taipei"))
        dr.issued = issued
        dr.status = "entered-in-error"
        dr.conclusion = (
            "XML file format error"
            if type(e).__name__ == "ExpatError"
            else f"{type(e).__name__}: {e}"
        )
    # print(json.dumps(dr.as_json()))
    resp = dr.create(fhir_server)
    drid = resp["id"]
    
    # 把 DiagnosticReport 存進 MongoDB
    mongo_col.insert_one(datetimeConverter(dict(resp)))
    
    dr_res = Resources(
        res_id=drid,
        res_type=dr.resource_type,
        user=user,
        requester=contained[sr.requester.reference[1:]].name,
        model="STEMI",
        status=dr.status,
        result=obs.as_json() if dr.status == "final" else {"detail": dr.conclusion},
        create_time=datetime.now(),
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

@router.get("/ActivityDefinition/")
def get_Activity_Definition():
    return AD.ActivityDefinition.read(2165, fhir_server).as_json()


@router.get("/{id}/")
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
