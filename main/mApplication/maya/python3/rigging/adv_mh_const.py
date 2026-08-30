import maya.cmds as cmds

def halfList(object_):
    half = int(len(object_)/2)
    items = object_[:half]
    targets = object_[half:]
    return items,targets

def constraints(items,targets):
    for i,item in enumerate(items):
        cmds.parentConstraint(item,targets[i],mo=1)
        cmds.scaleConstraint(item,targets[i],mo=1)

def matchTrans(items,targets):
    for i,item in enumerate(items):
        cmds.matchTransform(item, targets[i], pos=1)

mh_dict = {
'mh_spines':['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05']
,'mh_legs':['thigh_r', 'calf_r', 'foot_r', 'ball_r', 'thigh_l', 'calf_l', 'foot_l', 'ball_l']
,'mh_neck_head':['neck_01', 'neck_02', 'head']
,'mh_arms':['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r']
,'mh_fingers':['pinky_metacarpal_l', 'pinky_01_l', 'pinky_02_l', 'pinky_03_l', 'ring_metacarpal_l', 'ring_01_l', 'ring_02_l', 'ring_03_l', 'thumb_01_l', 'thumb_02_l', 'thumb_03_l', 'middle_metacarpal_l', 'middle_01_l', 'middle_02_l', 'middle_03_l', 'index_metacarpal_l', 'index_01_l', 'index_02_l', 'index_03_l', 'pinky_metacarpal_r', 'pinky_01_r', 'pinky_02_r', 'pinky_03_r', 'ring_metacarpal_r', 'ring_01_r', 'ring_02_r', 'ring_03_r', 'thumb_01_r', 'thumb_02_r', 'thumb_03_r', 'middle_metacarpal_r', 'middle_01_r', 'middle_02_r', 'middle_03_r', 'index_metacarpal_r', 'index_01_r', 'index_02_r', 'index_03_r']
}
adv_dict = {
'adv_spines':['Root_M', 'Spine1_M', 'Spine2_M', 'Spine3_M', 'Chest_M', 'ChestBR_M']
,'adv_legs':['Hip_R', 'Knee_R', 'Ankle_R', 'Toes_R', 'Hip_L', 'Knee_L', 'Ankle_L', 'Toes_L']
,'adv_neck_head':['Neck_M', 'NeckPart1_M', 'Head_M']
,'adv_arms':['Scapula_L', 'Shoulder_L', 'Elbow_L', 'Wrist_L', 'Scapula_R', 'Shoulder_R', 'Elbow_R', 'Wrist_R']
,'adv_fingers':['PinkyFinger0_L', 'PinkyFinger1_L', 'PinkyFinger2_L', 'PinkyFinger3_L', 'RingFinger0_L', 'RingFinger1_L', 'RingFinger2_L', 'RingFinger3_L', 'ThumbFinger1_L', 'ThumbFinger2_L', 'ThumbFinger3_L', 'MiddleFinger0_L', 'MiddleFinger1_L', 'MiddleFinger2_L', 'MiddleFinger3_L', 'IndexFinger0_L', 'IndexFinger1_L', 'IndexFinger2_L', 'IndexFinger3_L', 'PinkyFinger0_R', 'PinkyFinger1_R', 'PinkyFinger2_R', 'PinkyFinger3_R', 'RingFinger0_R', 'RingFinger1_R', 'RingFinger2_R', 'RingFinger3_R', 'ThumbFinger1_R', 'ThumbFinger2_R', 'ThumbFinger3_R', 'MiddleFinger0_R', 'MiddleFinger1_R', 'MiddleFinger2_R', 'MiddleFinger3_R', 'IndexFinger0_R', 'IndexFinger1_R', 'IndexFinger2_R', 'IndexFinger3_R']
}
mh_fit_dict = {
'mh_spines':['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05']
,'mh_legs':['thigh_r', 'calf_r', 'foot_r', 'ball_r']
,'mh_neck_head':['neck_01', 'head']
,'mh_arms':['clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r']
,'mh_fingers':['pinky_metacarpal_r', 'pinky_01_r', 'pinky_02_r', 'pinky_03_r', 'ring_metacarpal_r', 'ring_01_r', 'ring_02_r', 'ring_03_r', 'thumb_01_r', 'thumb_02_r', 'thumb_03_r', 'middle_metacarpal_r', 'middle_01_r', 'middle_02_r', 'middle_03_r', 'index_metacarpal_r', 'index_01_r', 'index_02_r', 'index_03_r']
}
adv_fit_dict = {
'adv_spines':['Root', 'Spine1', 'Spine2', 'Spine3', 'Chest', 'ChestBR']
,'adv_legs':['Hip', 'Knee', 'Ankle', 'Toes']
,'adv_neck_head':['Neck', 'Head']
,'adv_arms':['Scapula', 'Shoulder', 'Elbow', 'Wrist']
,'adv_fingers':['PinkyFinger0', 'PinkyFinger1', 'PinkyFinger2', 'PinkyFinger3', 'RingFinger0', 'RingFinger1', 'RingFinger2', 'RingFinger3', 'ThumbFinger1', 'ThumbFinger2', 'ThumbFinger3', 'MiddleFinger0', 'MiddleFinger1', 'MiddleFinger2', 'MiddleFinger3', 'IndexFinger0', 'IndexFinger1', 'IndexFinger2', 'IndexFinger3']
}

# sel = cmds.ls(sl=1,r=1)
# items,targets = halfList(sel)
# constraints(items,targets)

for i,item in enumerate(adv_dict.keys()):
    item = adv_dict[item]
    target = mh_dict[list(mh_dict.keys())[i]]
    print(item, target)
    constraints(item,target)
'''
for i,item in enumerate(adv_fit_dict.keys()):
    item = adv_fit_dict[item]
    target = mh_fit_dict[list(mh_fit_dict.keys())[i]]
    matchTrans(item,target)
'''