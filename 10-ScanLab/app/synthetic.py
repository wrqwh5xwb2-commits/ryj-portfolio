"""原创程序生成测试图；没有真实个人信息，也不是实拍样本。"""
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def paper():
    img = np.full((860,630,3), 247, np.uint8)
    cv2.rectangle(img,(42,42),(588,112),(93,65,37),-1)
    cv2.putText(img,"SCANLAB / FIELD NOTES",(61,84),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2,cv2.LINE_AA)
    cv2.putText(img,"Document imaging experiment",(44,167),cv2.FONT_HERSHEY_SIMPLEX,.75,(42,44,49),2,cv2.LINE_AA)
    for i,line in enumerate(["01  Detect the four page corners", "02  Estimate a projective transform", "03  Flatten uneven lighting", "04  Compare and export the result"]):
        cv2.putText(img,line,(46,225+i*44),cv2.FONT_HERSHEY_SIMPLEX,.62,(62,62,62),1,cv2.LINE_AA)
    cv2.rectangle(img,(44,418),(586,656),(120,120,120),1)
    for y in range(466,657,47): cv2.line(img,(44,y),(586,y),(180,180,180),1)
    cv2.line(img,(300,418),(300,656),(180,180,180),1)
    for i,(a,b) in enumerate([("PROCESS", "OPENCV"),("Geometry", "warpPerspective"),("Contours", "approxPolyDP"),("Threshold", "adaptiveThreshold"),("Data", "Synthetic / demo")]):
        cv2.putText(img,a,(59,449+i*47),cv2.FONT_HERSHEY_SIMPLEX,.53,(60,60,60),1,cv2.LINE_AA)
        cv2.putText(img,b,(313,449+i*47),cv2.FONT_HERSHEY_SIMPLEX,.5,(60,60,60),1,cv2.LINE_AA)
    cv2.putText(img,"No OCR. No cloud upload. Local processing.",(44,723),cv2.FONT_HERSHEY_SIMPLEX,.55,(77,77,77),1,cv2.LINE_AA)
    cv2.putText(img,"Original synthetic test chart | v1",(44,787),cv2.FONT_HERSHEY_SIMPLEX,.48,(112,112,112),1,cv2.LINE_AA)
    return img


def scene(seed=0, kind="perspective"):
    rng = np.random.default_rng(seed)
    h,w=1080,1100
    background = np.empty((h,w,3),np.uint8)
    values = np.clip(60 + np.linspace(0,28,w)[None,:] + rng.normal(0,2,(h,w)),0,255).astype(np.uint8)
    for channel,offset in enumerate([9,4,0]): background[:,:,channel]=values+offset
    points=np.float32([[195,100],[855,158],[924,957],[121,920]]) + rng.uniform(-40,40,(4,2)).astype(np.float32)
    if kind=="tilted": points=np.float32([[345,47],[991,367],[660,1020],[60,748]])
    page=paper()
    if kind=="shadow":
        lighting=np.tile(np.linspace(.38,1,page.shape[1]),(page.shape[0],1))
        page=np.uint8(page*lighting[:,:,None])
    if kind=="lowcontrast":
        background[:]=180
        page=np.uint8(page*.3+130)
    source=np.float32([[0,0],[629,0],[629,859],[0,859]])
    matrix=cv2.getPerspectiveTransform(source,points)
    projected=cv2.warpPerspective(page,matrix,(w,h))
    mask=cv2.warpPerspective(np.full(page.shape[:2],255,np.uint8),matrix,(w,h))
    background[mask>127]=projected[mask>127]
    if kind=="blur": background=cv2.GaussianBlur(background,(13,13),4)
    if kind=="occluded": cv2.rectangle(background,(100,60),(480,300),(55,60,60),-1)
    return background,points


def write_png(path,image):
    ok, encoded=cv2.imencode(".png",image)
    assert ok
    Path(path).write_bytes(encoded.tobytes())


if __name__ == "__main__":
    directory=ROOT/"samples"
    directory.mkdir(exist_ok=True)
    labels={}
    for kind in ["perspective","shadow","tilted","blur","occluded"]:
        image,points=scene(42,kind)
        write_png(directory/f"{kind}.png",image)
        labels[kind]={"corners_pixels":points.tolist(),"size":[1100,1080],"provenance":"original synthetic"}
    write_png(directory/"blank.png",np.full((720,960,3),145,np.uint8))
    (directory/"ground-truth.json").write_text(json.dumps(labels,indent=2),encoding="utf-8")
    print("Generated 6 synthetic images and ground-truth labels.")
