import json
from datetime import datetime,timezone
from time import perf_counter
import cv2
import numpy as np
from .synthetic import ROOT, scene, write_png
from .vision import detect, ordered, rectify, enhance


def evaluate():
    cases=[]
    for kind in ["perspective","shadow","tilted","blur","lowcontrast","occluded"]:
        for seed in [101,202,303,404]:
            image,truth=scene(seed,kind)
            start=perf_counter()
            found,_,_=detect(image)
            duration=(perf_counter()-start)*1000
            error=None; iou=0
            if found is not None:
                # 角点循环/反向对齐，度量几何位置而非起点标签。
                possibilities=[np.roll(p,i,axis=0) for p in [found,found[::-1]] for i in range(4)]
                error=float(min(float(np.linalg.norm(p-truth,axis=1).mean()) for p in possibilities)/np.hypot(*image.shape[:2]))
                a=np.zeros(image.shape[:2],np.uint8);b=a.copy()
                cv2.fillConvexPoly(a,np.int32(truth),1);cv2.fillConvexPoly(b,np.int32(found),1)
                iou=float(np.logical_and(a,b).sum()/max(np.logical_or(a,b).sum(),1))
            cases.append({"condition":kind,"seed":seed,"detected":found is not None,"corner_error_diagonal":None if error is None else round(error,5),"iou":round(iou,4),"pass":error is not None and error<=.025 and iou>=.9,"detect_ms":round(duration,2)})
    blanks=[detect(np.full((720,960,3),v,np.uint8))[0] is None for v in [0,80,160,255]]
    result={"created_at":datetime.now(timezone.utc).isoformat(),"opencv_version":cv2.__version__,"data":"24 positive synthetic development cases + 4 uniform negative images; not real camera validation", "criterion":"mean corner distance / image diagonal <= 0.025 AND polygon IoU >= 0.90", "case_count":len(cases), "pass_count":sum(c["pass"] for c in cases),"detection_count":sum(c["detected"] for c in cases),"blank_rejections":sum(blanks),"blank_count":len(blanks),"p95_detect_ms":round(float(np.percentile([c["detect_ms"] for c in cases],95)),2),"cases":cases}
    (ROOT/"docs"/"benchmark.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    image,_=scene(42)
    corners,_,_=detect(image)
    if corners is not None:
        warped,_=rectify(image,corners);enhanced,binary=enhance(warped)
        for name,img in [("color",warped),("enhanced",enhanced),("binary",binary)]:write_png(ROOT/"docs"/f"example-{name}.png",img)
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},indent=2))
    return result


if __name__=="__main__": evaluate()
