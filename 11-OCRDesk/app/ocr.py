"""RapidOCR 适配层。识别模型属于上游，本项目负责输入、校对与导出流程。"""
import base64
import csv
import io
from functools import lru_cache
from threading import Lock
from time import perf_counter

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from rapidocr import RapidOCR

INFERENCE_LOCK = Lock()


@lru_cache(maxsize=1)
def engine():
    return RapidOCR(params={'Global.log_level':'warning',
                            'EngineConfig.onnxruntime.intra_op_num_threads':2,
                            'EngineConfig.onnxruntime.inter_op_num_threads':1})


def decode(raw):
    if not raw or len(raw)>8*1024*1024:
        raise ValueError('请选择不超过8MB的图片')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in {'PNG','JPEG','WEBP'}:
                raise ValueError('只支持PNG、JPG、WebP')
            if im.width*im.height>20_000_000 or min(im.size)<32:
                raise ValueError('图片需至少32×32像素，且不超过2000万像素')
            im=ImageOps.exif_transpose(im).convert('RGBA')
            original=list(im.size)
            background=Image.new('RGBA',im.size,'white')
            background.alpha_composite(im)
            background.thumbnail((1800,1800),Image.Resampling.LANCZOS)
            return cv2.cvtColor(np.asarray(background.convert('RGB')),cv2.COLOR_RGB2BGR),original
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError('无法解码图片，请选择有效图片') from exc


def recognize(raw):
    image,original=decode(raw)
    # 单进程串行推理，让模型实例初始化和推理不发生重入。
    with INFERENCE_LOCK:
        model=engine()
        start=perf_counter()
        prediction=model(image)
        elapsed=round((perf_counter()-start)*1000,1)
    texts=prediction.txts if prediction.txts is not None else []
    lines=[{'id':i+1,'original':text,'text':text,'score':float(score),'reviewed':False,
            'box':np.asarray(box).round(2).tolist()}
           for i,(text,score,box) in enumerate(zip(texts,
               prediction.scores if prediction.scores is not None else [],
               prediction.boxes if prediction.boxes is not None else []))]
    ok,png=cv2.imencode('.png',image)
    if not ok:raise ValueError('无法编码预览')
    return {'lines':lines,'elapsed_ms':elapsed,'original_size':original,
            'working_size':[image.shape[1],image.shape[0]],
            'preview':'data:image/png;base64,'+base64.b64encode(png).decode(),
            'engine':'RapidOCR 3.9.2 / ONNX Runtime CPU',
            'status':'ready' if lines else 'no_text'}


def safe_cell(text):
    """防止识别出的文本在Excel里被当成公式；保留原文另见JSON。"""
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r','\n')) else text


def export_csv(rows):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(['行号','原始识别','人工校对','模型分数','已修改','已核对'])
    for row in rows:
        writer.writerow([row['id'],safe_cell(row['original']),safe_cell(row['text']),
                         f"{row['score']:.5f}",row['original']!=row['text'],row.get('reviewed',False)])
    return stream.getvalue().encode('utf-8-sig')
