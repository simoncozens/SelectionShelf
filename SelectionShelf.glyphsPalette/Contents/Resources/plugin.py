import objc
from vanilla import Window, Group, List, EditText, Button
from GlyphsApp.plugins import PalettePlugin
from GlyphsApp import (
    Glyphs,
    UPDATEINTERFACE,
    GSEditViewController,
    GSComponent,
    GSAnchor,
    GSNode,
)

KEY = "co.uk.corvelsoftware.selectionshelf"


class DeleteCallbackList(List):
    def __init__(self, posSize, items, **kwargs):
        if "deleteCallback" in kwargs:
            self.deleteCallback = kwargs["deleteCallback"]
            del kwargs["deleteCallback"]
        super().__init__(posSize, items, **kwargs)

    def _removeSelection(self):
        selection = self.getSelection()
        thelist = self.get()
        for index in selection:
            self.deleteCallback(thelist[index])
        super()._removeSelection()


def layerIterator(layer, lmbd):
    if not layer:
        return
    for component in layer.components:
        lmbd(component)
    for path in layer.paths:
        for node in path.nodes:
            lmbd(node)
    for anchor in layer.anchors:
        lmbd(anchor)


def setSelection(thing, name):
    if not thing.userData[KEY]:
        thing.userData[KEY] = {}
    thing.userData[KEY][name] = 1


def deleteSelection(thing, name):
    if thing.userData[KEY] and name in thing.userData[KEY]:
        del thing.userData[KEY][name]
        if not thing.userData[KEY]:
            del thing.userData[KEY]


class SelectionShelf(PalettePlugin):
    dialog = objc.IBOutlet()
    textField = objc.IBOutlet()

    @objc.python_method
    def settings(self):
        self.name = "Selection Shelf"
        width = 160
        height = 120
        self.paletteView = Window((width, height + 10))
        self.paletteView.frame = Group((0, 0, width, height + 10))
        self.paletteView.frame.list = List((0, 0, -0, -30), [])
        self.paletteView.frame.name = EditText((0, -27, -80, 25), text="")
        self.paletteView.frame.save = Button(
            (-75, -30, -5, -0), "Save", sizeStyle="small", callback=self.saveSelection
        )
        self.dialog = self.paletteView.frame.getNSView()

    @objc.python_method
    def start(self):
        # Adding a callback for the 'GSUpdateInterface' event
        Glyphs.addCallback(self.update, UPDATEINTERFACE)

    @objc.python_method
    def __del__(self):
        Glyphs.removeCallback(self.update)

    @objc.python_method
    def update(self, sender):
        currentTab = sender.object()
        if not isinstance(currentTab, GSEditViewController):
            return
        self.updatelist(currentTab.activeLayer())

    @objc.python_method
    def updatelist(self, layer):
        # Check all shapes, nodes and anchors for selection names
        oldselections = self.paletteView.frame.list.get()
        selections = set([])
        layerIterator(
            layer,
            lambda thing: selections.update(set(thing.userData.get(KEY, {}).keys())),
        )
        if (selections or oldselections) and selections != set(oldselections):
            if hasattr(self.paletteView.frame, "list"):
                delattr(self.paletteView.frame, "list")
            keylist = sorted(list(selections))
            self.paletteView.frame.list = DeleteCallbackList(
                (0, 0, -0, -30),
                keylist,
                doubleClickCallback=self.restoreSelection,
                enableDelete=True,
                deleteCallback=self.deleteSelection,
            )

    @objc.python_method
    def saveSelection(self, sender):
        name = self.paletteView.frame.name.get()
        if not name:
            return
        layer = Glyphs.font.selectedLayers[0]
        if not layer:
            return
        if not layer.selection:
            return
        otherLayers = [
            otherLayer for otherLayer in layer.parent.layers if otherLayer != layer
        ]
        isCompatible = layer.parent.mastersCompatible
        for thing in layer.selection:
            setSelection(thing, name)
            # Try to find compatible things in other masters,
            # propagate selection there.
            if not otherLayers or not isCompatible:
                continue
            if isinstance(thing, GSComponent):
                index = layer.shapes.index(thing)
                for otherLayer in otherLayers:
                    setSelection(otherLayer.shapes[index], name)
            if isinstance(thing, GSAnchor):
                anchorname = thing.name
                for otherLayer in otherLayers:
                    setSelection(otherLayer.anchors[anchorname], name)
            if isinstance(thing, GSNode):
                # Well this is unfortunate
                nodeindex = thing.index
                pathindex = layer.shapes.index(thing.parent)
                for otherLayer in otherLayers:
                    setSelection(otherLayer.shapes[pathindex].nodes[nodeindex], name)

        self.paletteView.frame.name.set("")
        self.updatelist(layer)

    @objc.python_method
    def restoreSelection(self, sender):
        indices = self.paletteView.frame.list.getSelection()
        if not indices:
            return
        name = self.paletteView.frame.list.get()[indices[0]]

        layer = Glyphs.font.selectedLayers[0]
        newselection = []
        layerIterator(
            layer,
            lambda thing: name in thing.userData.get(KEY, {})
            and newselection.append(thing),
        )
        # "click" on the layer editor
        gview = layer.font().currentTab.graphicView()
        gview.window().makeFirstResponder_(gview)
        layer.selection = newselection

    @objc.python_method
    def deleteSelection(self, name):
        layer = Glyphs.font.selectedLayers[0]
        otherLayers = [
            otherLayer for otherLayer in layer.parent.layers if otherLayer != layer
        ]
        isCompatible = layer.parent.mastersCompatible

        def deletor(thing):
            deleteSelection(thing, name)
            if not otherLayers or not isCompatible:
                return
            # Try to find compatible things in other masters,
            # propagate (de)selection there.
            #
            # I could probably abstract this out from the equivalent
            # code in saveSelection, but it's a bit nasty so I'll
            # only do so if I need to change this code.
            if isinstance(thing, GSComponent):
                index = layer.shapes.index(thing)
                for otherLayer in otherLayers:
                    deleteSelection(otherLayer.shapes[index], name)
            if isinstance(thing, GSAnchor):
                anchorname = thing.name
                for otherLayer in otherLayers:
                    deleteSelection(otherLayer.anchors[anchorname], name)
            if isinstance(thing, GSNode):
                nodeindex = thing.index
                pathindex = layer.shapes.index(thing.parent)
                for otherLayer in otherLayers:
                    deleteSelection(otherLayer.shapes[pathindex].nodes[nodeindex], name)

        layerIterator(layer, deletor)

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
