"""Window class for Nuke.

TODO: Get callbacks from https://learn.foundry.com/nuke/developers/110/pythonreference/
"""

from __future__ import absolute_import, print_function

import inspect
from collections import defaultdict

import nuke
from nukescripts import panels, utils

from .abstract import AbstractWindow, getWindowSettings
from .standalone import StandaloneWindow
from .utils import hybridmethod, setCoordinatesToScreen, searchGlobals
from .utils.Qt import QtWidgets


NUKE_VERSION = float('{}.{}'.format(nuke.env['NukeVersionMajor'], nuke.env['NukeVersionMinor']))


def getMainWindow():
    """Returns Nuke's main window
    Source: https://github.com/fredrikaverpil/pyvfx-boilerplate/blob/master/boilerplate.py
    """
    for obj in QtWidgets.QApplication.topLevelWidgets():
        if obj.inherits('QMainWindow') and obj.metaObject().className() == 'Foundry::UI::DockMainWindow':
            return obj
    raise RuntimeError('Could not find DockMainWindow instance')


def deleteQtWindow(windowId):
    """Delete a window.
    Source: https://github.com/fredrikaverpil/pyvfx-boilerplate/blob/master/boilerplate.py
    """
    for obj in QtWidgets.QApplication.allWidgets():
        if obj.objectName() == windowId:
            obj.deleteLater()


def _removeMargins(widget):
    """Remove Nuke margins when docked UI
    Source: https://gist.github.com/maty974/4739917
    """
    for parent in (widget.parentWidget().parentWidget(), widget.parentWidget().parentWidget().parentWidget().parentWidget()):
        parent.layout().setContentsMargins(0, 0, 0, 0)


class Pane(object):
    @classmethod
    def get(cls, value=None):
        if value is not None:
            return nuke.getPaneFor(value)
        return cls.auto()

    @classmethod
    def auto(cls):
        """Automatically select a pane to attach to.
        If there are somehow no panels that exist then None will be returned.
        """
        for pane_func in cls.__PRIORITY:
            pane = pane_func.__get__(cls, None)()
            if pane is not None:
                return pane

    @classmethod
    def find(cls, windowID):
        """Find which pane the WindowID is docked to."""
        current_pane = nuke.getPaneFor(windowID)
        if current_pane is None:
            return None
        for pane_func in cls.__PRIORITY:
            index = 1
            while True:
                pane = pane_func.__get__(cls, None)(index)
                if pane is None:
                    break
                if pane == current_pane:
                    return pane_func.__get__(cls, None)(index, name=True)
                index += 1

    @classmethod
    def Properties(cls, index=1, name=False):
        panel_name = 'Properties.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def NodeGraph(cls, index=1, name=False):
        panel_name = 'DAG.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Viewer(cls, index=1, name=False):
        panel_name = 'Viewer.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Progress(cls, index=1, name=False):
        panel_name = 'Progress.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def DopeSheet(cls, index=1, name=False):
        panel_name = 'DopeSheet.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Toolbar(cls, index=1, name=False):
        panel_name = 'Toolbar.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def CurveEditor(cls, index=1, name=False):
        panel_name = 'Curve Editor.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def PixelAnalyzer(cls, index=1, name=False):
        panel_name = 'Pixel Analyzer.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def ErrorConsole(cls, index=1, name=False):
        panel_name = 'Error Console.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def ScriptEditor(cls, index=1, name=False):
        panel_name = 'uk.co.thefoundry.scripteditor.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Histogram(cls, index=1, name=False):
        panel_name = 'uk.co.thefoundry.histogram.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Waveform(cls, index=1, name=False):
        panel_name = 'uk.co.thefoundry.waveformscope.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    @classmethod
    def Vectorscope(cls, index=1, name=False):
        panel_name = 'uk.co.thefoundry.vectorscope.{}'.format(index)
        if name:
            return panel_name
        return nuke.getPaneFor(panel_name)

    __PRIORITY = [
        Properties,
        NodeGraph,
        Viewer,
        DopeSheet,
        CurveEditor,
        PixelAnalyzer,
        Progress,
        ErrorConsole,
        ScriptEditor,
        Histogram,
        Waveform,
        Vectorscope,
        Toolbar,
    ]


class NukeCommon(object):
    pass
        

class NukeWindow(NukeCommon, AbstractWindow):
    """Base class for docking windows in Nuke.

    Usage:
        class MainWindow(NukeWindow):
            ...
        MainWindow.show()

    Important:
        To save any window preferences, such as its location, do it it in "saveWindowPosition",
         which will run once each time the window is hidden (or closed).
        To update the window with any scene changes, use "updateToCurrent",
         which will run once each time the window is shown (required as callbacks are unregistered when the window is hidden).
    """

    _CALLBACKS = {
        'onUserCreate': ('addOnUserCreate', 'removeOnUserCreate'),
        'onCreate': ('addOnCreate', 'removeOnCreate'),
        'onScriptLoad': ('addOnScriptLoad', 'removeOnScriptLoad'),
        'onScriptSave': ('addOnScriptSave', 'removeOnScriptSave'),
        'onScriptClose': ('addOnScriptClose', 'removeOnScriptClose'),
        'onDestroy': ('addOnDestroy', 'removeOnDestroy'),
        'knobChanged': ('addKnobChanged', 'removeKnobChanged'),
        'updateUI': ('addUpdateUI', 'removeUpdateUI'),
    }

    def __init__(self, parent=None, **kwargs):
        if parent is None:
            parent = getMainWindow()
        super(NukeWindow, self).__init__(parent, **kwargs)
        self.nuke = True

        self.__windowHidden = False
        try:
            self.setDockable(self.windowSettings['nuke']['docked'], override=True)
        except KeyError:
            self.setDockable(getattr(self, 'WindowDockable', True), override=True)

        # Fix for parent bug
        # See NukeWindow.parent for more information
        self.__useNukeTemporaryParent = True
        self.windowReady.connect(self.__disableTemporaryParent)
        
        # This line seemed to be recommended, but I'm not sure why
        #if not self.dockable():
        #    self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):
        super(NukeWindow, self).clearWindowInstance(self.WindowID)

        if self.dockable():
            if self.exists():
                #Delete the pane if it is floating by itself
                if self.floating(alternative=True) and self.siblings() == 1:
                    self.parent().parent().parent().parent().parent().parent().parent().parent().parent().close()

                #Remove the tab and pane if by itself
                else:
                    self.parent().parent().parent().parent().parent().parent().parent().close()
                    deleteQtWindow(self.WindowID)
        else:
            self.saveWindowPosition()
        return super(NukeWindow, self).closeEvent(event)

    def setDefaultSize(self, width, height):
        """Override of setDefaultSize to disable it if window is docked."""
        if not self.dockable():
            super(NukeWindow, self).setDefaultSize(width, height)

    def setDefaultWidth(self, width):
        """Override of setDefaultWidth to disable it if window is docked."""
        if not self.dockable():
            super(NukeWindow, self).setDefaultWidth(width)

    def setDefaultHeight(self, height):
        """Override of setDefaultHeight to disable it if window is docked."""
        if not self.dockable():
            super(NukeWindow, self).setDefaultHeight(height)

    def setDefaultPosition(self, x, y):
        """Override of setDefaultPosition to disable it if window is docked."""
        if not self.dockable():
            super(NukeWindow, self).setDefaultPosition(x, y)

    def setWindowPalette(self, program, version=None, style=True, force=False):
        """Set the palette of the window.
        This will change the entire Nuke GUI so it's disabled by default.
        The force parameter can be set to override this behaviour.
        """
        if force:
            super(NukeWindow, self).setWindowPalette(program, version, style)

    def windowPalette(self):
        currentPalette = super(NukeWindow, self).windowPalette()
        if currentPalette is None:
            return 'Nuke.{}'.format(NUKE_VERSION)
        return currentPalette

    def exists(self, alternative=False):
        """Check if the window still exists.
        See if it is attached to any pane, or check the parents up to the QStackedWidget.
        """
        if self.dockable():
            if alternative:
                return self.parent().parent().parent().parent().parent().parent().parent().parent() is not None
            return Pane.get(self.WindowID) is not None
        return not self.isClosed()

    def floating(self, alternative=False):
        """Determine if the window is floating."""
        if self.dockable():
            if alternative:
                return self.parent().parent().parent().parent().parent().parent().parent().parent().parent().parent().parent().parent() is not None
            return Pane.find(self.WindowID) is None
        return True

    def siblings(self):
        """Count the number of siblings in the QStackedWidget."""
        if self.dockable():
            try:
                return self.parent().parent().parent().parent().parent().parent().parent().parent().count()
            except AttributeError:
                return 0
        return None

    def getAttachedPane(self):
        """Find the name of the pane the window is attached to."""
        return Pane.find(self.WindowID)
    
    def saveWindowPosition(self):
        """Save the window location."""
        if 'nuke' not in self.windowSettings:
            self.windowSettings['nuke'] = {}
        try:
            nukeSettings = self.windowSettings['nuke']
        except KeyError:
            nukeSettings = self.windowSettings['nuke'] = {}
        self.windowSettings['nuke']['docked'] = self.dockable(raw=True)
        if self.dockable():
            try:
                dockWindowSettings = self.windowSettings['nuke']['dock']
            except KeyError:
                dockWindowSettings = self.windowSettings['nuke']['dock'] = {}
            panel = self.getAttachedPane()
            if panel is not None:
                self.windowSettings['nuke']['dock']['panel'] = panel
            
            # TODO: Figure out how to launch a floating docked window
            try:
                dockWindowSettings['width'] = self.width()
                dockWindowSettings['height'] = self.height()
                dockWindowSettings['x'] = self.x()
                dockWindowSettings['y'] = self.y()
            except RuntimeError as e:
                if str(e) != 'window is currently in a quantum state (while dragging it technically doesn\'t exist)':
                    raise
        else:
            try:
                mainWindowSettings = self.windowSettings['nuke']['main']
            except KeyError:
                mainWindowSettings = self.windowSettings['nuke']['main'] = {}
            mainWindowSettings['width'] = self.width()
            mainWindowSettings['height'] = self.height()
            mainWindowSettings['x'] = self.x()
            mainWindowSettings['y'] = self.y()

        super(NukeWindow, self).saveWindowPosition()
        
    def loadWindowPosition(self):
        """Set the position of the window when loaded."""
        if self.dockable():
            return
        try:
            settings = self.windowSettings['nuke']['main']
            x = settings['x']
            y = settings['y']
            width = settings['width']
            height = settings['height']
        except KeyError:
            super(NukeWindow, self).loadWindowPosition()
        else:
            x, y = setCoordinatesToScreen(x, y, width, height, padding=5)
            self.resize(width, height)
            self.move(x, y)

    def hideEvent(self, event):
        """Unregister callbacks and save window location."""
        if not event.spontaneous() and not self.isClosed():
            try:
                self._unregisterNukeCallbacks()
            except TypeError:
                self.__windowHidden = True
            self.saveWindowPosition()
        return super(NukeWindow, self).hideEvent(event)

    def showEvent(self, event):
        """Register callbacks and update UI (if checkForChanges is defined)."""
        if not event.spontaneous():
            self._registerNukeCallbacks()
            self.__windowHidden = False
            if hasattr(self, 'checkForChanges'):
                self.checkForChanges()
        return super(NukeWindow, self).showEvent(event)
    
    def _parentOverride(self, usePane=False):
        """Get the widget that contains the correct size and position on screen."""
        try:
            if usePane:
                pane = Pane.get(self.WindowID)
                if pane is None:
                    raise AttributeError()
                return pane
            if not self.floating(alternative=True):
                return self.parent().parent().parent().parent().parent().parent().parent().parent().parent()
            return self.parent().parent().parent().parent().parent().parent().parent().parent().parent().parent().parent()
        except AttributeError:
            if self.exists():
                raise
            else:
                raise RuntimeError('window is currently in a quantum state (while dragging it technically doesn\'t exist)')
    
    def width(self):
        if self.dockable():
            return self._parentOverride(usePane=True).width()
        return super(NukeWindow, self).width()
    
    def height(self):
        if self.dockable():
            return self._parentOverride(usePane=True).width()
        return super(NukeWindow, self).width()
    
    def _registerNukeCallbacks(self):
        """Register all callbacks."""
        numEvents = 0
        windowInstance = self.windowInstance()
        for group in windowInstance['callback'].keys():
            for callbackName, (callbackAdd, callbackRemove) in self._CALLBACKS.items():
                for func in windowInstance['callback'][group][callbackName]:
                    for nodeClass in windowInstance['callback'][group][callbackName][func]:
                        if nodeClass is None:
                            getattr(nuke, callbackAdd)(func)
                        else:
                            getattr(nuke, callbackAdd)(func, nodeClass=nodeClass)
                        numEvents += 1
        return numEvents

    def _unregisterNukeCallbacks(self, group=None):
        """Unregister all callbacks."""
        numEvents = 0
        windowInstance = self.windowInstance()
        for group in windowInstance['callback'].keys():
            for callbackName, (callbackAdd, callbackRemove) in self._CALLBACKS.items():
                for func in windowInstance['callback'][group][callbackName]:
                    for nodeClass in windowInstance['callback'][group][callbackName][func]:
                        if nodeClass is None:
                            getattr(nuke, callbackRemove)(func)
                        else:
                            getattr(nuke, callbackRemove)(func, nodeClass=nodeClass)
                        numEvents += 1
        return numEvents

    def removeCallback(self, func, group=None, nodeClass=None):
        """Remove an individual callback."""
        windowInstance = self.windowInstance()
        if group is None:
            groups = windowInstance['callback'].keys()
        else:
            if group not in windowInstance['callback']:
                groups = []
            groups = [group]

        numEvents = 0
        for group in groups:
            for callbackName, (callbackAdd, callbackRemove) in self._CALLBACKS.items():
                if func in windowInstance['callback'][group][callbackName]:
                    for nodeClass in windowInstance['callback'][group][callbackName][func]:
                        if nodeClass is None:
                            if nodeClass is None:
                                getattr(nuke, callbackRemove)(func)
                            else:
                                getattr(nuke, callbackRemove)(func, nodeClass=nodeClass)
                        elif nodeClass == nodeClass:
                            getattr(nuke, callbackRemove)(func, nodeClass=nodeClass)
                        else:
                            continue
                        numEvents += 1
                        del windowInstance['callback'][group][callbackName][func][nodeClass]
        return numEvents

    @hybridmethod
    def removeCallbacks(cls, self, group=None, windowInstance=None, windowID=None):
        """Remove a callback group or all callbacks."""
        # Handle classmethod
        if self is cls:
            if windowInstance is None and windowID is not None:
                windowInstance = cls.windowInstance(windowID)
            if windowInstance is None:
                raise ValueError('windowInstance or windowID parameter is required for classmethod')
        # Handle normal method
        elif windowInstance is None:
            windowInstance = self.windowInstance()

        # Select all groups if specific one not provided
        if group is None:
            groups = windowInstance['callback'].keys()
        else:
            if group not in windowInstance['callback']:
                groups = []
            else:
                groups = [group]

        # Iterate through each callback to remove certain groups
        numEvents = 0
        for group in groups:
            for callbackName, (callbackAdd, callbackRemove) in self._CALLBACKS.items():
                for func in windowInstance['callback'][group][callbackName]:
                    for nodeClass in windowInstance['callback'][group][callbackName][func]:
                        if nodeClass is None:
                            getattr(nuke, callbackRemove)(func)
                        else:
                            getattr(nuke, callbackRemove)(func, nodeClass=nodeClass)
                        numEvents += 1
            del windowInstance['callback'][group]
        return numEvents

    def _addNukeCallbackGroup(self, group):
        windowInstance = self.windowInstance()
        if group in windowInstance['callback']:
            return
        windowInstance['callback'][group] = defaultdict(lambda: defaultdict(set))

    def addCallbackOnUserCreate(self, func, nodeClass=None, group=None):
        """Executed whenever a node is created by the user.
        Not called when loading existing scripts, pasting nodes, or undoing a delete.
        """
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onUserCreate'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnUserCreate(func)
            else:
                nuke.addOnUserCreate(func, nodeClass=nodeClass)

    def addCallbackOnCreate(self, func, nodeClass=None, group=None):
        """Executed when any node is created.
        Examples include loading a script (includes new file), pasting a node, selecting a menu item, or undoing a delete.
        """
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onCreate'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnCreate(func)
            else:
                nuke.addOnCreate(func, nodeClass=nodeClass)

    def addCallbackOnScriptLoad(self, func, nodeClass=None, group=None):
        """Executed when a script is loaded.
        This will be called by onCreate (for root), and straight after onCreate.
        """
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onScriptLoad'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnScriptLoad(func)
            else:
                nuke.addOnScriptLoad(func, nodeClass=nodeClass)

    def addCallbackOnScriptSave(self, func, nodeClass=None, group=None):
        """Executed when the user tries to save a script."""
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onScriptSave'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnScriptSave(func)
            else:
                nuke.addOnScriptSave(func, nodeClass=nodeClass)

    def addCallbackOnScriptClose(self, func, nodeClass=None, group=None):
        """Executed when Nuke is exited or the script is closed."""
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onScriptClose'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnScriptClose(func)
            else:
                nuke.addOnScriptClose(func, nodeClass=nodeClass)

    def addCallbackOnDestroy(self, func, nodeClass=None, group=None):
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['onDestroy'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addOnDestroy(func)
            else:
                nuke.addOnDestroy(func, nodeClass=nodeClass)

    def addCallbackKnobChanged(self, func, nodeClass=None, group=None):
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['knobChanged'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addKnobChanged(func)
            else:
                nuke.addKnobChanged(func, nodeClass=nodeClass)

    def addCallbackUpdateUI(self, func, nodeClass=None, group=None):
        self._addNukeCallbackGroup(group)
        self.windowInstance()['callback'][group]['updateUI'][func].add(nodeClass)
        if not self.__windowHidden:
            if nodeClass is None:
                nuke.addUpdateUI(func)
            else:
                nuke.addUpdateUI(func, nodeClass=nodeClass)

    @classmethod
    def clearWindowInstance(self, windowID):
        """Close the last class instance."""
        try:
            previousInstance = super(NukeWindow, self).clearWindowInstance(windowID)
        except TypeError:
            return
        if previousInstance is None:
            return
        self.removeCallbacks(windowInstance=previousInstance)

        #Shut down the window
        if not previousInstance['window'].isClosed():
            try:
                previousInstance['window'].close()
            except (RuntimeError, ReferenceError):
                pass

    def deferred(self, func, *args, **kwargs):
        """Execute a deferred command."""
        utils.executeDeferred(func, *args, **kwargs)

    def parent(self, *args, **kwargs):
        """Fix a weird Nuke crash.
        It seems to be under a specific set of circumstances, so I'm
        not sure how to deal with it other than with this workaround.

        Details specific to my issue:
            Non-dockable window
            Location data doesn't exist, causing centreWindow to run
            Requesting self.parent() inside centreWindow crashes Nuke.

        This fix runs getMainWindow if loading isn't complete.
        """
        if not self.__useNukeTemporaryParent or self.dockable():
            return super(NukeWindow, self).parent(*args, **kwargs)
        return getMainWindow()
    
    def __disableTemporaryParent(self):
        """See NukeWindow.parent for information."""
        self.__useNukeTemporaryParent = False

    @hybridmethod
    def show(cls, self, *args, **kwargs):
        """Show the Nuke window.

        IMPORTANT:
            If using the dockable window, then the namespace needs to be set.
            This is simply a string of how the window is called, such as "module.MyWindow.show(namespace='module.MyWindow')".
            It's not ideal and can't be error checked, but it's required for the time being.
        """
        # Window is already initialised
        if self is not cls:
            return super(NukeWindow, cls).show()

        #Close down any instances of the window
        try:
            cls.clearWindowInstance(cls.WindowID)
        except AttributeError:
            settings = {}
        else:
            settings = getWindowSettings(cls.WindowID)

        #Load settings
        try:
            nukeSettings = settings['nuke']
        except KeyError:
            nukeSettings = settings['nuke'] = {}

        if hasattr(cls, 'WindowDockable'):
            docked = cls.WindowDockable
        else:
            try:
                docked = nukeSettings['docked']
            except KeyError:
                try:
                    docked = cls.WindowDefaults['docked']
                except (AttributeError, KeyError):
                    docked = True

        dockOverride = False
        if docked:
            # Attempt to find the module in the global scope
            # If it can't be found, then it can't be docked
            namespace = searchGlobals(cls)
            if namespace is None:
                docked = cls.WindowDockable = False
                dockOverride = True

        #Return new class instance and show window
        if docked:
            try:
                pane = Pane.get(nukeSettings['dock']['panel']) or Pane.auto()
            except KeyError:
                pane = Pane.auto()

            panel = panels.registerWidgetAsPanel(
                widget=namespace,
                name=getattr(cls, 'WindowName', 'New Window'),
                id=cls.WindowID,
                create=True,
            )
            panel.addToPane(pane)
                
            panelObject = panel.customKnob.getObject()
            if panelObject is not None:
                widget = panelObject.widget
                _removeMargins(widget)
                return widget
        
        win = super(NukeWindow, cls).show(*args, **kwargs)
        if dockOverride:
            cls.WindowDockable = True
            win.setDockable(True, override=True)
        return win


class NukeBatchWindow(NukeCommon, StandaloneWindow):
    """Variant of the Standalone window for Nuke in batch mode.

    Warning: This does not yet work properly. It is able to launch a
    process to run the GUI in (since batch mode uses a QCoreApplication
    which does not allow windows), but that process is not able to
    correctly import the "_nuke" library.
    """

    def __init__(self, parent=None, **kwargs):
        super(NukeBatchWindow, self).__init__(parent, **kwargs)
        self.nuke = False
        self.batch = True
        self.standalone = False

    def setWindowPalette(self, program, version=None, style=True, force=False):
        if force:
            super(NukeBatchWindow, self).setWindowPalette(program, version, style)

    def saveWindowPosition(self):
        """Save the window location."""
        try:
            nukeSettings = self.windowSettings['nuke']
        except KeyError:
            nukeSettings = self.windowSettings['nuke'] = {}
        try:
            mainWindowSettings = nukeSettings['batch']
        except KeyError:
            mainWindowSettings = nukeSettings['batch'] = {}
        mainWindowSettings['width'] = self.width()
        mainWindowSettings['height'] = self.height()
        mainWindowSettings['x'] = self.x()
        mainWindowSettings['y'] = self.y()

        super(NukeBatchWindow, self).saveWindowPosition()

    def loadWindowPosition(self):
        """Set the position of the window when loaded."""
        try:
            width = self.windowSettings['nuke']['batch']['width']
            height = self.windowSettings['nuke']['batch']['height']
            x = self.windowSettings['nuke']['batch']['x']
            y = self.windowSettings['nuke']['batch']['y']
        except KeyError:
            super(NukeBatchWindow, self).loadWindowPosition()
        else:
            x, y = setCoordinatesToScreen(x, y, width, height, padding=5)
            self.resize(width, height)
            self.move(x, y)

    @hybridmethod
    def show(cls, self, *args, **kwargs):
        """Load the window in Nuke batch mode."""
        # Window is already initialised
        if self is not cls:
            return super(NukeBatchWindow, cls).show()
        
        # Close down window if it exists and open a new one
        try:
            cls.clearWindowInstance(cls.WindowID)
        except AttributeError:
            pass
        kwargs['instance'] = False
        kwargs['exec_'] = True
        return super(NukeBatchWindow, cls).show(*args, **kwargs)
