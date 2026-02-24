import maya.cmds as cmds

sel = cmds.ls(sl=1,r=1)
[cmds.setAttr(f'{i}.type', 18) for i in sel]
[cmds.setAttr(f'{i}.otherType', '1', type='string') for i in sel]
[cmds.setAttr(f'{i}.drawLabel', 1) for i in sel]