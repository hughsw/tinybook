import math
from io import BytesIO
from math import sqrt, pow

from pypdf import PdfWriter, PdfReader, Transformation
from pypdf.generic import RectangleObject
from pypdf._page import PageObject


from utils import attrdict
from pagemap import pageMap

## FIX ME
#import pypdf
#pypdf._page.MERGE_CROP_BOX = "trimbox"

PAGE_QUANTUM = 4

#async
def fold(config):
    work = attrdict()
    result=attrdict()

    work.foldCutReader = PdfReader(config.foldCutFile, strict=True)
    print(f'foldCutReader: foldCutReader.resolved_objects: {work.foldCutReader.resolved_objects}')

    work.reader = PdfReader(config.pdfFile, strict=True)
    #print(f'reader: reader.viewer_preferences: {work.reader.viewer_preferences}')
    print(f'reader: reader.resolved_objects: {work.reader.resolved_objects}')

    work.writer = PdfWriter()


    ret = attrdict(
        config=config,
        work=work,
        result=result,
        )

    pageCounts(ret)
    pageMap(ret)
    render(ret)

    if False:
        page1 = work.reader.pages[0]
        page1.scale_by(0.75)
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

    print(f'writer: writer.page_layout: {work.writer.page_layout}, writer.page_mode: {work.writer.page_mode}')
    #writer = work.writer

    #pagex = writer.add_blank_page(width, height)
    #print(f'pagex.mediabox: {pagex.mediabox}, pagex]cropbox: {pagex.cropbox}')

    for outIndex, outPage in enumerate(outPages):
        outPdfPage = PageObject.create_blank_page(width=width, height=height)
        #outPdfPage = work.writer.add_blank_page(width=width, height=height)
        #print(f'type(outPdfPage): {type(outPdfPage)}')
        #print(f'dir(outPdfPage): {dir(outPdfPage)}')
        print(f'outIndex: {outIndex}, outPdfPage.user_unit: {outPdfPage.user_unit}, outPdfPage.mediabox: {outPdfPage.mediabox}, len(outPage): {len(outPage)}, outPage: {outPage}')
        #print(f'outIndex: {outIndex}, outPdfPage.page_number: {outPdfPage.page_number}, outPdfPage.user_unit: {outPdfPage.user_unit}, outPdfPage.mediabox: {outPdfPage.mediabox}, len(outPage): {len(outPage)}, outPage: {outPage}')

        for inPageIndex, link in outPage.items():
            inPage = inPages[inPageIndex]
            print(' ', f'inPageIndex: {inPageIndex}, link: {link}, inPage.user_unit: {inPage.user_unit},  inPage.mediabox: {inPage.mediabox}')

            if False:
                outPdfPage.merge_page(inPage)
                #break

                if True:
                    page1 = work.reader.pages[0]
                    page1.scale_by(0.25)
                    #outPdfPage.merge_page(page1)
                    #inPage.scale_by(0.25)
                    work.writer.add_page(inPage)
                    #work.writer.add_page(page1)

            else:

                x, y, d = link
                op = Transformation()

                # TODO: abstract this and move to fold or pagemap
                if numFoldsHoriz != numFoldsVert:
                    print(f'  numFoldsHoriz != numFoldsVert')
                    ipx, ipy = map(float, inPage.mediabox.upper_right)
                    if outIndex % 2 == 0:
                        op = op.rotate(90).translate(tx=ipy, ty=0)
                        #inPage.add_transformation(Transformation().rotate(90).translate(tx=ipy, ty=0))
                    else:
                        op = op.rotate(-90).translate(tx=0, ty=ipx)
                        #inPage.add_transformation(Transformation().rotate(-90).translate(tx=0, ty=ipx))
                    print(f'  inPage.mediabox 2: {inPage.mediabox}')
                    # Note:
                    #inPage.mediabox.upper_right = ipy, ipx
                    #print(' ', f'inPage.mediabox 3: {inPage.mediabox}')

                assert inPage.mediabox.lower_left == (0.0, 0.0), str((inPage.mediabox))
                px, py = map(float, inPage.mediabox.upper_right)

                widthScale = cellWidth / px
                heightScale = cellHeight / py
                scale = min(widthScale, heightScale)
                print(' ', f'scale: {scale}, widthScale: {widthScale}, heightScale: {heightScale}')
                op = op.scale(sx=scale, sy=scale)

                if d == -1:
                    op = op.rotate(180).translate(tx=cellWidth, ty=cellHeight)

                tx = cellWidth * ((1<<numFoldsHoriz)-1-x)
                ty = cellHeight * ((1<<numFoldsVert)-1-y)
                print(f'  x: {x}, y: {y}, d: {d}, tx: {tx}, ty: {ty}')
                op = op.translate(tx=tx, ty=ty)

                print(f'  op: {op}')
                outPdfPage.merge_transformed_page(inPage, op, expand=True)

                if False:
                    inPage.add_transformation(op)
                    inPage.transfer_rotation_to_content()
                    print(f'  inPage.mediabox 3: {inPage.mediabox}, cropbox: {inPage.cropbox}, artbox: {inPage.artbox}')
                    outPdfPage.merge_page(inPage)


        if True:
            if outIndex == 1:
                if numFolds >= 1:
                    fold1 = ret.work.foldCutReader.pages[1-1]
                    #fold1.transfer_rotation_to_content()
                    print(f'fold1: mediabox: {fold1.mediabox}, cropbox: {fold1.cropbox}, artbox: {fold1.artbox}')
                    #foldHeight = 10
                    foldHeight = 12
                    xLo = 0
                    xHi = width
                    yOffset = height/2+0
                    foldBox = RectangleObject((xLo, yOffset-foldHeight/2, xHi, yOffset+foldHeight/2))
                    print(f'fold1: foldBox: {foldBox}')
                    fold1.mediabox = foldBox
                    fold1.cropbox = foldBox
                    fold1.artbox = foldBox
                    #outPdfPage.merge_transformed_page(fold1, Transformation())
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
                    print(f'fold2: foldBox: {foldBox}')
                    fold2.mediabox = foldBox
                    fold2.cropbox = foldBox
                    fold2.artbox = foldBox
                    outPdfPage.merge_transformed_page(fold2, Transformation())
                    #outPdfPage.merge_page(fold2)

                if numFolds >= 3:
                    fold3 = ret.work.foldCutReader.pages[3-1]
                    print(f'fold3: mediabox: {fold3.mediabox}, cropbox: {fold3.cropbox}, artbox: {fold3.artbox}')
                    foldHeight = 8
                    xLo = 0
                    xHi = width*1/2
                    yOffset = height*3/4+0
                    foldBox = RectangleObject((xLo, yOffset-foldHeight/2, xHi, yOffset+foldHeight/2))
                    print(f'fold3: foldBox: {foldBox}')
                    fold3.mediabox = foldBox
                    fold3.cropbox = foldBox
                    fold3.artbox = foldBox
                    outPdfPage.merge_transformed_page(fold3, Transformation())
                    #outPdfPage.merge_page(fold3)

                if numFolds >= 4:
                    fold4 = ret.work.foldCutReader.pages[4-1]
                    print(f'fold4: mediabox: {fold4.mediabox}, cropbox: {fold4.cropbox}, artbox: {fold4.artbox}')
                    foldWidth = 9
                    yLo = height*1/2
                    yHi = height*3/4
                    xOffset = width*3/4+0
                    foldBox = RectangleObject((xOffset-foldWidth/2, yLo, xOffset+foldWidth/2, yHi))
                    print(f'fold4: foldBox: {foldBox}')
                    fold4.mediabox = foldBox
                    fold4.cropbox = foldBox
                    fold4.artbox = foldBox
                    outPdfPage.merge_transformed_page(fold4, Transformation())
                    #outPdfPage.merge_page(fold4)

        if False:
            outPdfPage.compress_content_streams()

        work.writer.add_page(outPdfPage)

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
