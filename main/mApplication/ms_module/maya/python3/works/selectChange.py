import maya.cmds as cmds

def remove_namespace(name):
    return name.split(":")[-1]
    
source_joints = cmds.ls(sl=1,r=1,fl=1)
'''
change_joints = []
for src_joint in source_joints:
    src_name = remove_namespace(src_joint).split("|")[-1]
    if cmds.objExists(src_name):
        change_joints.append(src_name)
'''
change_joints = []
for src_joint in source_joints:
    change_joints.append(f'scene:{src_joint}')

cmds.select(change_joints)