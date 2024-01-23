import math
from io import BytesIO
from math import sqrt, pow

from PyPDF2 import PdfWriter, PdfReader, Transformation
from PyPDF2.generic import RectangleObject

from utils import attrdict
from pagemap import pageMap

PAGE_QUANTUM = 4

async def fold(config):
    work = attrdict()
    result=attrdict()
    ret = attrdict(
        config=config,
        work=work,
        result=result,
        )

    work.reader = PdfReader(config.pdfFile)
    work.foldCutReader = PdfReader(config.foldCutFile)
    work.writer = PdfWriter()

    pageCounts(ret)
    pageMap(ret)
    render(ret)

    if False:
        page1 = work.reader.pages[0]
        page1.scale_by(0.5)
        work.writer.add_page(page1)

    result.outer = BytesIO()
    work.writer.write(result.outer)

    return ret


async def copy(config):

    work = attrdict()
    result=attrdict()
    ret = attrdict(
        config=config,
        work=work,
        result=result,
        )

    work.reader = PdfReader(config.pdfFile)
    work.writer = PdfWriter()

    width = config.width
    height = config.height


    writer = work.writer

    #pagex = writer.add_blank_page(width, height)
    #print(f'pagex.mediabox: {pagex.mediabox}, pagex]cropbox: {pagex.cropbox}')

    up = config.up
    print(f'copy: up: {up}')
    assert up == int(up) and up >= 0, str((up, int(up)))
    numIter = 1 << up

    scale = 1 / numIter
    cellWidth = width * scale
    cellHeight = height * scale

    iters = (iter(work.reader.pages),) * numIter
    #for pagePages in zip(*iters):
    for pagePages in zip(work.reader.pages):
        print(f'len(pagePages): {len(pagePages)}')
        outPdfPage = writer.add_blank_page(width, height)
        for index, inpage in enumerate(pagePages):
            op = Transformation().scale(sx=scale, sy=scale).translate(tx=cellWidth/2, ty=cellHeight)
            #op = Transformation().scale(sx=scale, sy=scale).translate(tx=cellWidth/2, ty=cellHeight*index)
            inpage.add_transformation(op)
            outPdfPage.merge_page(inpage, expand=False)


    result.outer = BytesIO()
    work.writer.write(result.outer)

    return ret

def render(ret):
    print(f'render:')
    work = ret.work

    inPages = work.reader.pages
    outPages = work.outPages

    width = ret.config.width
    height = ret.config.height

    numFolds = ret.config.numFolds

    numFoldsVert = (numFolds + 1) // 2
    numFoldsHoriz = numFolds // 2

    print(f'numFolds: {numFolds}, numFoldsVert: {numFoldsVert}, numFoldsHoriz: {numFoldsHoriz}')

    #scale = 1 / sqrt(numFolds)
    #scale = 1 / numFolds
    cellScale = 1 / pow(2, numFolds/2)
    cellScale = 0
    #scale = 1 / 4
    #cellWidth = int(width * cellScale)
    #cellHeight = int(height * cellScale)
    cellWidth = int(width / (1 << numFoldsHoriz))
    cellHeight = int(height / (1 << numFoldsVert))
    print(f'render: cellScale: {cellScale}, cellWidth: {cellWidth}, cellHeight: {cellHeight}')

    writer = work.writer

    #pagex = writer.add_blank_page(width, height)
    #print(f'pagex.mediabox: {pagex.mediabox}, pagex]cropbox: {pagex.cropbox}')

    for outIndex, outPage in enumerate(outPages):
        outPdfPage = writer.add_blank_page(width, height)
        print(f'outIndex: {outIndex}, outPdfPage.user_unit: {outPdfPage.user_unit}, len(outPage): {len(outPage)}, outPage: {outPage}')
        for inPageIndex, link in outPage.items():
            inPage = inPages[inPageIndex]
            print(' ', f'inPageIndex: {inPageIndex}, link: {link}, inPage.user_unit: {inPage.user_unit},  inPage.mediabox: {inPage.mediabox}')
            x, y, d = link

            # TODO: abstract this and move to fold or pagemap
            if numFoldsHoriz != numFoldsVert:
                ipx, ipy = map(float, inPage.mediabox.upper_right)
                if outIndex % 2 == 0:
                    inPage.add_transformation(Transformation().rotate(90).translate(tx=ipy, ty=0))
                else:
                    inPage.add_transformation(Transformation().rotate(-90).translate(tx=0, ty=ipx))
                print(' ', f'inPage.mediabox 2: {inPage.mediabox}')
                # Note:
                #inPage.mediabox.upper_right = ipy, ipx
                #print(' ', f'inPage.mediabox 3: {inPage.mediabox}')

            assert inPage.mediabox.lower_left == (0.0, 0.0), str((inPage.mediabox))
            px, py = map(float, inPage.mediabox.upper_right)

            widthScale = cellWidth / px
            heightScale = cellHeight / py
            scale = min(widthScale, heightScale)
            print(' ', f'scale: {scale}, widthScale: {widthScale}, heightScale: {heightScale}')

            tx = cellWidth * ((1<<numFoldsHoriz)-1-x)
            ty = cellHeight * ((1<<numFoldsVert)-1-y)
            print(' ', f'tx: {tx}, ty: {ty}')
            op = Transformation().scale(sx=scale, sy=scale)
            if d == -1:
                op = op.rotate(180).translate(tx=cellWidth, ty=cellHeight)
            op = op.translate(tx=tx, ty=ty)

            inPage.add_transformation(op)
            outPdfPage.merge_page(inPage)

        if outIndex == 1 and numFolds >= 1:
            fold1 = ret.work.foldCutReader.pages[1-1]
            print(f'fold1: mediabox: {fold1.mediabox}, cropbox: {fold1.cropbox}, artbox: {fold1.artbox}')
            foldHeight = 10
            xLo = 0
            xHi = width
            yOffset = height/2+0
            foldBox = RectangleObject((xLo, yOffset-foldHeight/2, xHi, yOffset+foldHeight/2))
            fold1.mediabox = foldBox
            fold1.cropbox = foldBox
            outPdfPage.merge_page(fold1)

        if outIndex == 0:
            if numFolds >= 2:
                fold2 = ret.work.foldCutReader.pages[2-1]
                print(f'fold2: mediabox: {fold2.mediabox}, cropbox: {fold2.cropbox}, artbox: {fold2.artbox}')
                foldWidth = 8
                xOffset = width*1/2+1
                yLo = 0
                yHi = height*1/2
                foldBox = RectangleObject((xOffset-foldWidth/2, yLo, xOffset+foldWidth/2, yHi))
                fold2.mediabox = foldBox
                fold2.cropbox = foldBox
                outPdfPage.merge_page(fold2)

            if numFolds >= 3:
                fold3 = ret.work.foldCutReader.pages[3-1]
                print(f'fold3: mediabox: {fold3.mediabox}, cropbox: {fold3.cropbox}, artbox: {fold3.artbox}')
                foldHeight = 8
                xLo = 0
                xHi = width*1/2
                yOffset = height*3/4+0
                foldBox = RectangleObject((xLo, yOffset-foldHeight/2, xHi, yOffset+foldHeight/2))
                fold3.mediabox = foldBox
                fold3.cropbox = foldBox
                outPdfPage.merge_page(fold3)

            if numFolds >= 4:
                fold4 = ret.work.foldCutReader.pages[4-1]
                print(f'fold4: mediabox: {fold4.mediabox}, cropbox: {fold4.cropbox}, artbox: {fold4.artbox}')
                foldHeight = 8
                yLo = height*1/2
                yHi = height*3/4
                xOffset = width*3/4+0
                foldBox = RectangleObject((xOffset-foldHeight/2, yLo, xOffset+foldHeight/2, yHi))
                fold4.mediabox = foldBox
                fold4.cropbox = foldBox
                outPdfPage.merge_page(fold4)

        outPdfPage.compress_content_streams()


def pageCounts(ret):
    # Do work for page indices to figure out how many slots there are
    # on sheets and which indices will get rendered onto which sheets.
    # Does not do the low-level mapping to placement of indices on
    # front and backs of sheets.

    work = ret.work

    numPages = work.numPages = len(work.reader.pages)
    #print(f'len(reader.pages): {len(reader.pages)}')
    #print(f'numPages: {numPages}')

    numPageQuanta = (numPages + (PAGE_QUANTUM - 1)) // PAGE_QUANTUM
    numPagesTotal = numPageQuanta * PAGE_QUANTUM
    numBlankEnd = numPagesTotal - numPages
    print(f'numPages: {numPages}, numPagesTotal: {numPagesTotal}, numBlankEnd: {numBlankEnd}')

    numFolds = int(ret.config.numFolds)
    assert numFolds == ret.config.numFolds and numFolds >= 0, str((ret.config.numFolds, numFolds))

    # number of page cells on one side of a sheet
    numSheetFace = 1 << numFolds
    numSheetPages = 2 * numSheetFace

    numSheets = int(math.ceil(numPagesTotal / numSheetPages))

    numSheetPagesTotal = numSheets * numSheetPages
    numBlankMiddle = numSheetPagesTotal - numPagesTotal

    print(f'numFolds: {numFolds}, numSheets: {numSheets}, numBlankMiddle: {numBlankMiddle}')


    # build and pad the sequence of input pdf pages (their indices, with None for blank)
    pages = list(range(numPages))

    # add numBlankEnd to the end
    while len(pages) < numPagesTotal:
        pages.append(None)

    # add numBlankMiddle to the middle
    while len(pages) < numSheetPagesTotal:
        pages.insert(len(pages)//2, None)
    print(f'pages: {pages}')


    # build the indices of pages that go on each sheet for each sheet,
    # where sheet is a two-sided printer piece of paper
    sheetPages = tuple(list() for _ in range(numSheets))
    for sheetPage in sheetPages:
        # first half from head of pages
        for _ in range(numSheetFace):
            sheetPage.append(pages.pop(0))
        # second half from tail of pages
        for _ in range(numSheetFace):
            sheetPage.insert(numSheetFace, pages.pop())
    # empty
    assert not pages, str((pages,))

    print(f'sheetPages: {sheetPages}')

    work.numPagesTotal = numPagesTotal
    work.numSheets = numSheets
    work.sheetPages = sheetPages
