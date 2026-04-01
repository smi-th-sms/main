"""
Rig Tool Hub
============
AS Fit Tool + MH Fit Tool + Rig Develop Tool 통합 탭 런처.

Usage:
    import importlib
    import rig_tool_hub
    importlib.reload(rig_tool_hub)
    rig_tool_hub.show()
"""

import maya.cmds as cmds

_WIN_ID = "rigToolHubWin"


def show():
    import sys
    import os
    import importlib

    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)

    import as_fit_tool
    import mh_fit_tool
    import rig_develop_tool
    import ctrl_creator_tool
    importlib.reload(ctrl_creator_tool)
    importlib.reload(as_fit_tool)
    importlib.reload(mh_fit_tool)
    importlib.reload(rig_develop_tool)

    if cmds.window(_WIN_ID, exists=True):
        cmds.deleteUI(_WIN_ID)

    win = cmds.window(_WIN_ID, title="Rig Tool Hub",
                      widthHeight=(440, 860), sizeable=True, mxb=False)
    tabs = cmds.tabLayout(innerMarginWidth=2, innerMarginHeight=4)

    fit_scroll    = as_fit_tool.build_tab_ui(tabs)
    mh_scroll     = mh_fit_tool.build_tab_ui(tabs)
    dev_scroll    = rig_develop_tool._UI().build_tab_ui(tabs)

    cmds.tabLayout(tabs, edit=True, tabLabel=[
        (fit_scroll, "AS Fit"),
        (mh_scroll,  "MH Fit"),
        (dev_scroll, "Rig Develop"),
    ])

    cmds.showWindow(win)


if __name__ == "__main__":
    show()
