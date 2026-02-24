import maya.cmds as cmds

controller = cmds.ls(sl=1,r=1)[0]
nums = list(range(5))

for typ in ['Curl', 'Swing', 'Twist']:
    if not cmds.attributeQuery(f"{typ}_divider", node=controller, exists=True):
        cmds.addAttr(controller, longName=f"{typ}_divider", attributeType="enum", defaultValue=0, en=f"{typ}:", nn="________", keyable=True)
    for i in list(range(5)):
        if not cmds.attributeQuery(f"{typ}{i}", node=controller, exists=True):
                cmds.addAttr(controller, longName=f"{typ}{i}", attributeType="double", defaultValue=0, keyable=True)
