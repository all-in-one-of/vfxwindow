"""Set the window class to be specific to whichever program is loaded.

TODO:
    Substance callbacks
    Add dialog code for each application
    Revise setDefault* methods

    # Potential breaking changes
    Change setDocked to setFloating
    Remove docked in favour of floating
    Remove *_VERSION constants
    Changed dialog to isDialog
    Add dialog classmethod to replace cls.ForceDialog = True
    Remove processEvents
    Remove signalExists
"""

from __future__ import absolute_import

__all__ = ['VFXWindow']
__version__ = '1.4.5'

import os
import sys
try:
    from importlib.util import find_spec as importable
except ImportError:
    from pkgutil import find_loader as importable


def _setup_qapp():
    """Attempt to start a QApplication automatically in batch mode.
    The purpose of this is to override whatever the program uses.
    This must happen before any libraries are imported, as it's usually
    at that point when the QApplication is initialised.
    """
    from .utils.Qt import QtWidgets
    try:
        app = QtWidgets.QApplication(sys.argv)
    except RuntimeError:
        pass


if importable('maya') and 'maya.exe' in sys.executable:
    if type(sys.stdout) == file:
        _setup_qapp()
        from .maya import MayaBatchWindow as VFXWindow
    else:
        from .maya import MayaWindow as VFXWindow

elif importable('nuke') and 'Nuke' in sys.executable:
    if type(sys.stdout) == file:
        raise NotImplementedError('unable to use qt when nuke is in batch mode')
        from .nuke import NukeBatchWindow as VFXWindow
    else:
        from .nuke import NukeWindow as VFXWindow

elif importable('hou') and 'houdini' in sys.executable:
    from .houdini import HoudiniWindow as VFXWindow

elif importable('bpy') and 'blender.exe' in sys.executable:
    from .blender import BlenderWindow as VFXWindow

elif importable('unreal') and 'UE4Editor.exe' in sys.executable:
    from .unreal import UnrealWindow as VFXWindow

elif importable('MaxPlus') and '3dsmax.exe' in sys.executable:
    from .max import MaxWindow as VFXWindow

elif importable('sd') and 'Substance Designer.exe' in sys.executable:
    from .substance import SubstanceWindow as VFXWindow

else:
    from .standalone import StandaloneWindow as VFXWindow
