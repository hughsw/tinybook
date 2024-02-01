import sys, os
from io import BytesIO
from typing import Union
from json import loads

from fastapi import FastAPI, Path, Query, Form, File, UploadFile, Request
from fastapi.responses import StreamingResponse
import papersize

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


fold_marks_filename = '/app/FoldMarks.pdf'
def get_fold_marks_blob():
    with open(fold_marks_filename, 'rb') as foldAndCutMarksFile:
        return foldAndCutMarksFile.read()

foldMarksBlob = get_fold_marks_blob()

@app.post("/tinybook")
async def tinybook(
        configJson: str = Form(...),
        pdfFile: UploadFile = File(...),
):
    print(f'/tinybook: pdfFile: {pdfFile}')
    print(f'/tinybook: configJson: {repr(configJson)}')

    config = attrdict(loads(configJson))
    config.size = papersize.SIZES.get(config.layout.lower())
    if config.size is None:
        config.size = '8.5in x 11in'
    print(f'/tinybook: size: {config.size}')

    if False:
        x = papersize.parse_couple(config.size, unit='pt')
        print(f'x: {x}')
        config.width = int(8.5 * 72)
        config.height = int(11 * 72)

    config.width, config.height = map(int, papersize.parse_couple(config.size, unit='pt'))

    print(f'/tinybook: config: {config}')

    fileBlob = await pdfFile.read()
    config.pdfFile = BytesIO(fileBlob)

    if False:
        with open('/app/FoldMarks.pdf', 'rb') as foldAndCutMarksFile:
        #with open('/app/FoldAndCutMarks.pdf', 'rb') as foldAndCutMarksFile:
        #with open('/app/Fables.pdf', 'rb') as foldAndCutMarksFile:
        #with open('/app/foo.pdf', 'rb') as foldAndCutMarksFile:
            config.foldCutFile = BytesIO(foldAndCutMarksFile.read())

    config.foldCutFile = BytesIO(foldMarksBlob)

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
