
# TODO: add logic as constructor and methods to class
class Zoo(dict): pass
#Zoo = type('Zoo', (dict,), {})

# return if size is 2, or assert on validation failure
def validate(zoo):
    sizes = set(map(lambda x: len(x[0]), zoo.values()))
    assert len(sizes) == 1, str((sizes, zoo))
    size, = sizes
    return size == 2

# many assumptions, primarily that:
# - all horizontal folds are the "same" in terms of the side of the fold (all on left or all on right)
# - all vertical folds are the "same" in terms of the side of the fold (all on bottom or all on top)
# these assumptions mean that the first page always remains in a corner, and the x,y indices are
# offsets from that corner

# undo a horizontal fold (that is, horizontal movement, vertical crease...)
def horiz(zoo):
    zoo.foldIndex += 1
    zoo.x *= 2
    s1 = zoo.x - 1
    for (x,y), (z, d) in tuple(zoo.items()):
        mid = len(z) // 2
        zoo[x,y] = z[:mid], d
        x1 = s1 - x
        zoo[x1,y] = z[:mid-1:-1], (d if zoo.foldIndex % 2 else -d)
    return validate(zoo)

# undo a vertical fold (that is, vertical movement, horizontal crease...)
def vert(zoo):
    zoo.foldIndex += 1
    zoo.y *= 2
    s1 = zoo.y - 1
    for (x,y), (z, d) in tuple(zoo.items()):
        mid = len(z) // 2
        zoo[x,y] = z[:mid], d
        y1 = s1 - y
        # invert
        zoo[x,y1] = z[:mid-1:-1], (d if zoo.foldIndex % 2 else -d)
    return validate(zoo)

def undo(isOdd, pages):
    zoo = Zoo()
    # cell on sheet, and pages (folded) behind the cell, and orientation
    zoo[0,0] = pages, 1
    zoo.x = 1
    zoo.y = 1
    zoo.foldIndex = 0

    # zero folds, or odd
    isDone = validate(zoo) or (vert(zoo) if isOdd else False)

    if not isDone:
        # undo the folds
        while True:
            if horiz(zoo): break
            if vert(zoo): break

    print(f'zoo.x: {zoo.x}, zoo.y: {zoo.y}')
    for y in range(zoo.y):
        for x in range(zoo.x):
            print(f'{x,y} : {zoo[x,y]}')

    def pageMapper(zoo):
        # yields: pageIndex, (x, y, face, orientation)
        for (x,y), (z, d) in zoo.items():
            assert len(z) == 2, str((x, y, z, zoo))
            # front
            yield z[0], (x, y, 0, d)
            # back
            yield z[1], (zoo.x - 1 - x, y, 1, d)

    zoon = dict(pageMapper(zoo))
    print('pages:')
    for page, link in sorted(zoon.items()):
        print(f'{page} : {link}')

    return zoon


def sheetMap(ret):
    print(f'sheetMap:')
    work = ret.work
    pageMap = work.pageMap

    outPages = list()
    for sheetPage in work.sheetPages:
        sheetFront = dict()
        outPages.append(sheetFront)
        sheetBack = dict()
        outPages.append(sheetBack)

        for mapIndex, pageIndex in enumerate(sheetPage):
            if pageIndex is None: continue
            link = pageMap[mapIndex]
            x, y, z, d = link
            print(f'pageIndex: {pageIndex}, link: {link}')
            (sheetFront if z == 0 else sheetBack)[pageIndex] = x, y, d

    for outIndex, outPage in enumerate(outPages):
        print(f'outIndex: {outIndex}, outPage: {outPage}')

    return outPages

def pageMap(ret):
    numFolds = ret.config.numFolds
    assert int(numFolds) == numFolds, str((int(numFolds), numFolds))

    isOdd = numFolds % 2

    # each fold doubles, and there are two sides
    numPagesPerSheet = (1 << numFolds) * 2
    numPagesPerSide = numPagesPerSheet // 2

    twoFaceTemplate = tuple(range(numPagesPerSheet))

    print(f'pageMap: numFolds: {numFolds}, numPagesPerSheet: {numPagesPerSheet}, numPagesPerSide: {numPagesPerSide}')

    ret.work.pageMap = undo(isOdd, twoFaceTemplate)
    ret.work.outPages = sheetMap(ret)
