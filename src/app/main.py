import sys, os
from io import BytesIO
from typing import Union
from json import loads

from fastapi import FastAPI, Path, Query, Form, File, UploadFile, Request
from fastapi.responses import StreamingResponse

from utils import attrdict
from fold import fold, copy

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "tinybook"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    #print(f'/items/: item_id: {item_id}')
    return {"item_id": item_id, "q": q}

@app.post("/tinybook")
async def tinybook(
        configJson: str = Form(...),
        pdfFile: UploadFile = File(...),
):
    print(f'/tinybook: pdfFile: {pdfFile}')
    print(f'/tinybook: configJson: {repr(configJson)}')

    config = attrdict(loads(configJson))
    config.width = int(8.5 * 72)
    config.height = int(11 * 72)

    print(f'/tinybook: config: {config}')

    fileBlob = await pdfFile.read()
    config.pdfFile = BytesIO(fileBlob)

    with open('/app/FoldMarks.pdf', 'rb') as foldAndCutMarksFile:
    #with open('/app/FoldAndCutMarks.pdf', 'rb') as foldAndCutMarksFile:
    #with open('/app/Fables.pdf', 'rb') as foldAndCutMarksFile:
    #with open('/app/foo.pdf', 'rb') as foldAndCutMarksFile:
        config.foldCutFile = BytesIO(foldAndCutMarksFile.read())

    folds = fold(config)
    #folds = await fold(config)

    outFile = folds.result.outer
    outFile.seek(0)
    outStream = StreamingResponse(outFile, media_type='application/pdf')

    return outStream


@app.post("/tb2")
async def tinybook(
        configJson: str = Form(...),
        pdfFile: UploadFile = File(...),
):
    config = attrdict(loads(configJson))

    config.sheetsPerStitch = 2
    config.width = int(8.5 * 72)
    config.height = int(11 * 72)

    print(f'config: {config}')
    print(f'pdfFile.filename: {pdfFile.filename}, pdfFile.content_type: {pdfFile.content_type}')

    fileBlob = await pdfFile.read()
    config.pdfFile = BytesIO(fileBlob)

    # TODO: global resource
    with open('/app/FoldAndCutMarks.pdf', 'rb') as foldAndCutMarksFile:
        config.foldCutFile = BytesIO(foldAndCutMarksFile.read())

    folds = await unfold(config)

    outFile = folds.result.outFile
    outFile.seek(0)
    outStream = StreamingResponse(outFile, media_type=folds.result.media_type)

    return outStream


@app.post("/simple")
async def simple(
        configJson: str = Form(...),
        pdfFile: UploadFile = File(...),
):
    print(f'/simple: configJson: {configJson}')

    config = attrdict(loads(configJson))
    config.width = int(8.5 * 72)
    config.height = int(11 * 72)

    infileBlob = await pdfFile.read()
    config.pdfFile = BytesIO(infileBlob)

    pdfCopy = await copy(config)

    outFile = pdfCopy.result.outer
    outFile.seek(0)
    return StreamingResponse(outFile, media_type='application/pdf')

from unfold import unfold, Unfold, numTestFolds
#u = Unfold(attrdict(numFolds=numTestFolds))
