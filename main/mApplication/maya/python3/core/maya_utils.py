# -*- coding: utf-8 -*-
"""
Maya utilities for Maya tools
Maya 도구들을 위한 유틸리티 함수 모음
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Tuple, Optional, Union


class MayaUtils:
    """Maya 공통 유틸리티 클래스"""
    
    @staticmethod
    def safe_index_access(item_list: list, index: int, default=None):
        """안전한 리스트 인덱스 접근"""
        try:
            return item_list[index] if 0 <= index < len(item_list) else default
        except (IndexError, TypeError):
            return default
    
    @staticmethod
    def get_selection(type: str = None) -> List[str]:
        """선택된 오브젝트 반환"""
        try:
            if type:
                return cmds.ls(sl=True, type=type) or []
            return cmds.ls(sl=True) or []
        except:
            return []
    
    @staticmethod
    def clear_selection():
        """선택 해제"""
        try:
            cmds.select(clear=True)
        except:
            pass
    
    @staticmethod
    def has_object(obj_name: str) -> Optional[str]:
        """오브젝트가 존재하는지 확인"""
        try:
            if cmds.objExists(obj_name):
                return obj_name
        except:
            pass
        return None
    
    @staticmethod
    def get_children(obj: str, type: str = None) -> List[str]:
        """오브젝트의 자식 노드 반환"""
        try:
            if type:
                return cmds.listRelatives(obj, children=True, type=type, fullPath=False) or []
            return cmds.listRelatives(obj, children=True, fullPath=False) or []
        except:
            return []
    
    @staticmethod
    def match_transform(source: str, target: str, 
                      pos: bool = True, rot: bool = True, scl: bool = False, piv: bool = False) -> bool:
        """소스 오브젝트의 트랜스폼을 타겟에 매치"""
        try:
            cmds.matchTransform(target, source, pos=pos, rot=rot, scl=scl, piv=piv)
            return True
        except Exception as e:
            print(f"Failed to match transform from {source} to {target}: {e}")
            return False
    
    @staticmethod
    def transform_reset(obj: str, translate: bool = True, rotate: bool = True, scale: bool = False) -> bool:
        """오브젝트 트랜스폼 초기화"""
        try:
            if translate:
                cmds.setAttr(f"{obj}.translate", 0, 0, 0)
            if rotate:
                cmds.setAttr(f"{obj}.rotate", 0, 0, 0)
            if scale:
                cmds.setAttr(f"{obj}.scale", 1, 1, 1)
            return True
        except Exception as e:
            print(f"Failed to reset transform for {obj}: {e}")
            return False
    
    @staticmethod
    def set_override_color(obj: str, color_index: int) -> bool:
        """오브젝트의 오버라이드 컬러 설정"""
        try:
            cmds.setAttr(f"{obj}.overrideEnabled", 1)
            cmds.setAttr(f"{obj}.overrideColor", color_index)
            return True
        except Exception as e:
            print(f"Failed to set override color for {obj}: {e}")
            return False
    
    @staticmethod
    def set_outliner_color(obj: str, color: List[float]) -> bool:
        """아웃라이너 컬러 설정"""
        try:
            cmds.setAttr(f"{obj}.useOutlinerColor", 1)
            cmds.setAttr(f"{obj}.outlinerColor", color[0], color[1], color[2], type='double3')
            return True
        except Exception as e:
            print(f"Failed to set outliner color for {obj}: {e}")
            return False
    
    @staticmethod
    def get_bind_joints(mesh: str) -> List[str]:
        """메쉬의 바인드 조인트 반환"""
        try:
            # skinCluster 찾기
            history = cmds.listHistory(mesh, pruneDagObjects=True)
            skin_clusters = cmds.ls(history, type='skinCluster')
            
            if not skin_clusters:
                return []
            
            # 첫 번째 skinCluster의 영향 조인트 반환
            return cmds.skinCluster(skin_clusters[0], q=True, inf=True) or []
        except Exception as e:
            print(f"Failed to get bind joints for {mesh}: {e}")
            return []
    
    @staticmethod
    def copy_skin_weights(source_mesh: str, target_mesh: str, 
                         joint_mapping: dict = None) -> Optional[str]:
        """스킨 웨이트 복사"""
        try:
            # 소스 메쉬의 skinCluster 찾기
            source_history = cmds.listHistory(source_mesh, pruneDagObjects=True)
            source_skin = cmds.ls(source_history, type='skinCluster')
            
            if not source_skin:
                print(f"No skinCluster found on source mesh: {source_mesh}")
                return None
            
            source_skin = source_skin[0]
            source_joints = cmds.skinCluster(source_skin, q=True, inf=True)
            
            # 타겟 조인트 결정
            if joint_mapping:
                target_joints = [joint_mapping.get(j, j) for j in source_joints]
            else:
                target_joints = source_joints
            
            # 타겟 메쉬에 skinCluster가 있는지 확인
            target_history = cmds.listHistory(target_mesh, pruneDagObjects=True)
            target_skin = cmds.ls(target_history, type='skinCluster')
            
            if not target_skin:
                # skinCluster가 없으면 생성
                target_skin = cmds.skinCluster(
                    target_joints, target_mesh,
                    toSelectedBones=True,
                    normalizeWeights=1,
                    name=f"{target_mesh}_skinCluster"
                )[0]
            else:
                target_skin = target_skin[0]
            
            # 웨이트 복사
            cmds.copySkinWeights(
                sourceSkin=source_skin,
                destinationSkin=target_skin,
                noMirror=True,
                surfaceAssociation='closestPoint',
                influenceAssociation=['name', 'oneToOne']
            )
            
            return target_skin
            
        except Exception as e:
            print(f"Failed to copy skin weights from {source_mesh} to {target_mesh}: {e}")
            return None
    
    @staticmethod
    def object_clean(obj: str) -> bool:
        """오브젝트 클린업 (히스토리 삭제, 프리즈 등)"""
        try:
            # 히스토리 삭제
            cmds.delete(obj, constructionHistory=True)
            
            # 트랜스폼 프리즈
            try:
                cmds.makeIdentity(obj, apply=True, t=False, r=False, s=True, n=False)
            except:
                pass
            
            return True
        except Exception as e:
            print(f"Failed to clean object {obj}: {e}")
            return False
    
    @staticmethod
    def create_matrix_constraint(source: str, target: str, pivot_calc: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """매트릭스 컨스트레인트 생성 (multMatrix + decomposeMatrix)"""
        try:
            # multMatrix 노드 생성
            mm_node = cmds.createNode('multMatrix', name=f"{target}_multMatrix")
            
            # decomposeMatrix 노드 생성
            dm_node = cmds.createNode('decomposeMatrix', name=f"{target}_decomposeMatrix")
            
            # 연결 설정
            cmds.connectAttr(f"{source}.worldMatrix[0]", f"{mm_node}.matrixIn[0]")
            
            # 타겟의 부모 inversMatrix 연결
            parent = cmds.listRelatives(target, parent=True, fullPath=False)
            if parent:
                cmds.connectAttr(f"{parent[0]}.worldInverseMatrix[0]", f"{mm_node}.matrixIn[1]")
            
            # multMatrix → decomposeMatrix
            cmds.connectAttr(f"{mm_node}.matrixSum", f"{dm_node}.inputMatrix")
            
            # decomposeMatrix → target
            cmds.connectAttr(f"{dm_node}.outputTranslate", f"{target}.translate")
            cmds.connectAttr(f"{dm_node}.outputRotate", f"{target}.rotate")
            cmds.connectAttr(f"{dm_node}.outputScale", f"{target}.scale")
            
            if pivot_calc:
                # 피벗 계산 로직 추가
                cmds.connectAttr(f"{dm_node}.outputTranslate", f"{target}.rotatePivot")
                cmds.connectAttr(f"{dm_node}.outputTranslate", f"{target}.scalePivot")
            
            return (mm_node, dm_node)
            
        except Exception as e:
            print(f"Failed to create matrix constraint from {source} to {target}: {e}")
            return (None, None)
    
    @staticmethod
    def get_shape_node(obj: str, type: str = None) -> Optional[str]:
        """오브젝트의 shape 노드 반환"""
        try:
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=False) or []
            if not shapes:
                return None
            
            if type:
                for shape in shapes:
                    if cmds.nodeType(shape) == type:
                        return shape
                return None
            
            return shapes[0]
        except:
            return None
    
    @staticmethod
    def create_locator_at_position(name: str, position: Tuple[float, float, float]) -> str:
        """특정 위치에 로케이터 생성"""
        try:
            loc = cmds.spaceLocator(name=name)[0]
            cmds.xform(loc, ws=True, t=position)
            return loc
        except Exception as e:
            print(f"Failed to create locator {name} at {position}: {e}")
            return None
    
    @staticmethod
    def parent_objects(children: List[str], parent: str) -> bool:
        """오브젝트들을 부모 아래로 이동"""
        try:
            for child in children:
                if cmds.objExists(child) and cmds.objExists(parent):
                    cmds.parent(child, parent)
            return True
        except Exception as e:
            print(f"Failed to parent objects to {parent}: {e}")
            return False
    
    @staticmethod
    def duplicate_object(obj: str, name: str = None) -> Optional[str]:
        """오브젝트 복제"""
        try:
            dup = cmds.duplicate(obj, name=name)[0]
            return dup
        except Exception as e:
            print(f"Failed to duplicate object {obj}: {e}")
            return None
    
    @staticmethod
    def create_group(name: str, objects: List[str] = None) -> str:
        """그룹 생성"""
        try:
            grp = cmds.group(empty=True, name=name)
            
            if objects:
                for obj in objects:
                    if cmds.objExists(obj):
                        cmds.parent(obj, grp)
            
            return grp
        except Exception as e:
            print(f"Failed to create group {name}: {e}")
            return None
    
    @staticmethod
    def hide_object(obj: str) -> bool:
        """오브젝트 숨기기"""
        try:
            cmds.setAttr(f"{obj}.visibility", 0)
            return True
        except:
            return False
    
    @staticmethod
    def show_object(obj: str) -> bool:
        """오브젝트 보이기"""
        try:
            cmds.setAttr(f"{obj}.visibility", 1)
            return True
        except:
            return False
    
    @staticmethod
    def lock_attributes(obj: str, attrs: List[str]) -> bool:
        """속성 잠그기"""
        try:
            for attr in attrs:
                cmds.setAttr(f"{obj}.{attr}", lock=True)
            return True
        except Exception as e:
            print(f"Failed to lock attributes on {obj}: {e}")
            return False
    
    @staticmethod
    def unlock_attributes(obj: str, attrs: List[str]) -> bool:
        """속성 잠금 해제"""
        try:
            for attr in attrs:
                cmds.setAttr(f"{obj}.{attr}", lock=False)
            return True
        except Exception as e:
            print(f"Failed to unlock attributes on {obj}: {e}")
            return False
    
    @staticmethod
    def hide_attributes(obj: str, attrs: List[str]) -> bool:
        """속성 숨기기"""
        try:
            for attr in attrs:
                cmds.setAttr(f"{obj}.{attr}", keyable=False, channelBox=False)
            return True
        except Exception as e:
            print(f"Failed to hide attributes on {obj}: {e}")
            return False
    
    @staticmethod
    def show_attributes(obj: str, attrs: List[str]) -> bool:
        """속성 보이기"""
        try:
            for attr in attrs:
                cmds.setAttr(f"{obj}.{attr}", keyable=True)
            return True
        except Exception as e:
            print(f"Failed to show attributes on {obj}: {e}")
            return False










