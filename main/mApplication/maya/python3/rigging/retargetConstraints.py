import maya.cmds as cmds

def retargetConstraints(source, targets, constraintTypes=['parentConstraint', 'scaleConstraint'], maintainOffset=True):
    """
    타겟 오브젝트들의 기존 constraint를 삭제하고 새로운 소스로 constraint를 재생성
    
    Args:
        source (str): 새로운 constraint 소스 오브젝트
        targets (list): constraint를 받을 타겟 오브젝트들
        constraintTypes (list): 적용할 constraint 타입 리스트
        maintainOffset (bool): offset 유지 여부
    """
    if not cmds.objExists(source):
        cmds.warning(f"Source object '{source}' does not exist.")
        return
    
    for target in targets:
        if not cmds.objExists(target):
            cmds.warning(f"Target object '{target}' does not exist. Skipping.")
            continue
        
        # 기존 constraint 삭제
        constraints = cmds.listRelatives(target, type='constraint') or []
        if constraints:
            cmds.delete(constraints)
        
        # 새로운 constraint 생성
        for constraintType in constraintTypes:
            if constraintType == 'parentConstraint':
                cmds.parentConstraint(source, target, mo=maintainOffset)
            elif constraintType == 'scaleConstraint':
                cmds.scaleConstraint(source, target, mo=maintainOffset)
            elif constraintType == 'pointConstraint':
                cmds.pointConstraint(source, target, mo=maintainOffset)
            elif constraintType == 'orientConstraint':
                cmds.orientConstraint(source, target, mo=maintainOffset)

# 사용 예시
if __name__ == "__main__":
    # 방법 1: 하드코딩 (기존 방식)
    source = 'MainHip'
    targets = ['IKHandleFollowMain', 'IKStatic', 'RootFollowMain', 'GlobalFollowMain']
    retargetConstraints(source, targets)
    
    # 방법 2: 선택된 오브젝트 사용 (첫번째가 소스, 나머지가 타겟)
    # sel = cmds.ls(sl=True)
    # if len(sel) > 1:
    #     retargetConstraints(sel[0], sel[1:])


