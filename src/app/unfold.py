from io import BytesIO
from collections import namedtuple
import math

from pypdf import PdfWriter, PdfReader, Transformation
from pypdf.generic import RectangleObject

from utils import attrdict

debug = True
#debug = False
numTestFolds = 4

def log(*args):
    debug and print(*args)


class WorkCell(namedtuple('WorkCell', 'pageIndices, moves')): pass

class PageMoves(namedtuple('PageMoves', 'pageIndex, positionIndices, invert, direction, moves')): pass


NUM_FACES_PER_SHEET = 2
FOLD_QUANTUM = 4
HORIZONTAL = 'h'
VERTICAL = 'v'
FRONT = 0 #'f'
BACK = 1 #'b'

class Unfold(object):
    """
    Calculates sheet-faces geometry transformations for a given number of folds
    """

    def __init__(self, config):

        self.numFolds = int(config.numFolds)
        assert self.numFolds == config.numFolds and self.numFolds >= 0, str((config.numFolds, self.numFolds))

        self.numCellsPerFace = 1 << self.numFolds
        self.numCellsPerSheet = NUM_FACES_PER_SHEET * self.numCellsPerFace

        self.buildFolded()
        self.unfold()
        self.byPages()

        print(f'numFolds: {self.numFolds}, foldIndex: {self.foldIndex}')
        if debug:
            for key, cell in sorted(self.cells.items()):
                log(' ', f'{key} : {cell}')

        print(f'len(pages): {len(self.pages)}')
        if debug:
            for index, page in enumerate(self.pages):
                log(index, ':', f'pageIndex: {page.pageIndex}, positionIndices: {page.positionIndices}, invert: {page.invert}, direction: {page.direction}, moves: {page.moves}')


    def buildFolded(self):
        # build folded sheet and unfold it
        self.cells = dict()
        self.cells[FRONT, 0, 0] = WorkCell(pageIndices=list(range(self.numCellsPerSheet)), moves=list())
        self.numH = 1
        self.numV = 1
        self.foldIndex = 0

    def unfold(self):
        while True:
            log(f'unfold: cells: {self.cells}')
            if self.verticalUnfold(): break

            log(f'unfold: cells: {self.cells}')
            if self.horizontalUnfold(): break

    def byPages(self):
        # project fold artifacts by page index
        self.pages = [None] * len(self.cells)
        for positionIndices, cell in self.cells.items():
            pageIndex, = cell.pageIndices
            moves = tuple(reversed(cell.moves))
            # TODO: abstract orientation issues
            invert = sum(move == VERTICAL for move in moves) % 2
            direction = 1 if sum(move is not None for move in moves) % 2 == 0 else -1
            self.pages[pageIndex] = PageMoves(pageIndex=pageIndex,
                                              positionIndices=positionIndices,
                                              invert=invert,
                                              direction=direction,
                                              moves=moves)

    def render(self):
        pass

    @staticmethod
    def splitCell(cell, move):
        assert len(cell.pageIndices) >= 2, str((cell.pageIndices,))

        # new cell pages are reverse of second half of parent's pages
        pageIndices = list()
        while len(pageIndices) < len(cell.pageIndices):
            pageIndices.append(cell.pageIndices.pop())
        assert len(pageIndices) == len(cell.pageIndices), str((len(pageIndices), len(cell.pageIndices)))

        # we could link moves into a tree
        moves = list(cell.moves)
        if move is not None:
            # special case, used for final, sheet unfold
            cell.moves.append(None)
            moves.append(move)

        return WorkCell(pageIndices=pageIndices, moves=moves)

    def horizontalUnfold(self):
        # undo a fold that moves things horizontally
        log(f'horizontalUnfold():')

        if self.foldIndex < self.numFolds:
            self.numH *= 2
            move = HORIZONTAL
            face = FRONT
        else:
            # distinguished, final, face flipping move (no move because back face is already flipped, so this flip results in no flip)
            assert self.foldIndex == self.numFolds, str((self.foldIndex, self.numFolds))
            move = None
            face = BACK

        self.foldIndex += 1
        hLimit = self.numH - 1
        for (_, x, y), cell in tuple(self.cells.items()):
            self.cells[face, hLimit - x, y] = self.splitCell(cell, move)

        return self.foldIndex > self.numFolds

    def verticalUnfold(self):
        # undo a fold that moves things vertically
        log(f'verticalUnfold():')

        if self.foldIndex < self.numFolds:
            self.numV *= 2
            move = VERTICAL
            face = FRONT
        else:
            # distinguished, final, face flipping move (no move because back face is already flipped, so this flip results in no flip)
            assert self.foldIndex == self.numFolds, str((self.foldIndex, self.numFolds))
            move = None
            face = BACK

        self.foldIndex += 1
        vLimit = self.numV - 1
        for (_, x, y), cell in tuple(self.cells.items()):
            self.cells[face, x, vLimit - y] = self.splitCell(cell, move)

        return self.foldIndex > self.numFolds

    def uncollate(self, numPages):
        # uncollate the pages
        indices = list(range(numPages))
        if self.numFolds == 0:
            while len(indices) % NUM_FACES_PER_SHEET != 0:
                indices.append(None)
        else:
            while len(indices) % FOLD_QUANTUM != 0:
                indices.append(None)

        numIndicesTotal = int(math.ceil(len(indices) / self.numCellsPerSheet)) * self.numCellsPerSheet

        while len(indices) < numIndicesTotal:
            indices.insert(len(indices)//2, None)

        print(f'numIndicesTotal: {numIndicesTotal}, indices: {indices}')

        self.indices = indices

async def unfold(config):
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

    geo = Unfold(config)
    print(f'geo.numFolds: {geo.numFolds}, geo.numCellsPerSheet: {geo.numCellsPerSheet}')
    #print(f'dir(geo): {dir(geo)}')

    geo.uncollate(len(work.reader.pages))

    result.outFile = BytesIO()
    result.media_type = 'application/pdf'
    work.writer.write(result.outFile)

    return ret
