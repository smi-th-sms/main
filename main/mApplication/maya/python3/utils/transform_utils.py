# -*- coding: utf-8 -*-
"""
Transform utilities for Maya tools
Maya 도구들을 위한 트랜스폼 유틸리티
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import pymel.core as pm
import pymel.core.datatypes as dt
from typing import List, Tuple, Optional, Union


class TransformUtils:
    """트랜스폼 관련 유틸리티 클래스"""
    
    @staticmethod
    def reset_transform(obj: str, translate: bool = True, rotate: bool = True, scale: bool = True) -> bool:
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
    def freeze_transform(obj: str) -> bool:
        """오브젝트 트랜스폼 프리즈"""
        try:
            cmds.makeIdentity(obj, apply=True, t=True, r=True, s=True, n=False)
            return True
        except Exception as e:
            print(f"Failed to freeze transform for {obj}: {e}")
            return False
    
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
    def get_world_position(obj: str) -> Tuple[float, float, float]:
        """오브젝트의 월드 포지션 반환"""
        try:
            pos = cmds.xform(obj, q=True, ws=True, t=True)
            return tuple(pos)
        except Exception as e:
            print(f"Failed to get world position for {obj}: {e}")
            return (0, 0, 0)
    
    @staticmethod
    def get_world_rotation(obj: str) -> Tuple[float, float, float]:
        """오브젝트의 월드 로테이션 반환"""
        try:
            rot = cmds.xform(obj, q=True, ws=True, ro=True)
            return tuple(rot)
        except Exception as e:
            print(f"Failed to get world rotation for {obj}: {e}")
            return (0, 0, 0)
    
    @staticmethod
    def get_world_scale(obj: str) -> Tuple[float, float, float]:
        """오브젝트의 월드 스케일 반환"""
        try:
            scl = cmds.xform(obj, q=True, ws=True, s=True)
            return tuple(scl)
        except Exception as e:
            print(f"Failed to get world scale for {obj}: {e}")
            return (1, 1, 1)
    
    @staticmethod
    def set_world_position(obj: str, position: Tuple[float, float, float]) -> bool:
        """오브젝트의 월드 포지션 설정"""
        try:
            cmds.xform(obj, ws=True, t=position)
            return True
        except Exception as e:
            print(f"Failed to set world position for {obj}: {e}")
            return False
    
    @staticmethod
    def set_world_rotation(obj: str, rotation: Tuple[float, float, float]) -> bool:
        """오브젝트의 월드 로테이션 설정"""
        try:
            cmds.xform(obj, ws=True, ro=rotation)
            return True
        except Exception as e:
            print(f"Failed to set world rotation for {obj}: {e}")
            return False
    
    @staticmethod
    def get_distance(obj1: str, obj2: str) -> float:
        """두 오브젝트 간의 거리 계산"""
        try:
            pos1 = TransformUtils.get_world_position(obj1)
            pos2 = TransformUtils.get_world_position(obj2)
            
            # 거리 계산
            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            dz = pos2[2] - pos1[2]
            
            return (dx**2 + dy**2 + dz**2)**0.5
        except Exception as e:
            print(f"Failed to calculate distance between {obj1} and {obj2}: {e}")
            return 0.0
    
    @staticmethod
    def get_angle_between_vectors(obj1: str, obj2: str, obj3: str) -> float:
        """세 오브젝트로 이루어진 각도 계산"""
        try:
            pos1 = TransformUtils.get_world_position(obj1)
            pos2 = TransformUtils.get_world_position(obj2)
            pos3 = TransformUtils.get_world_position(obj3)
            
            # 벡터 계산
            v1 = [pos1[0] - pos2[0], pos1[1] - pos2[1], pos1[2] - pos2[2]]
            v2 = [pos3[0] - pos2[0], pos3[1] - pos2[1], pos3[2] - pos2[2]]
            
            # 내적 계산
            dot_product = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
            
            # 벡터 크기 계산
            mag1 = (v1[0]**2 + v1[1]**2 + v1[2]**2)**0.5
            mag2 = (v2[0]**2 + v2[1]**2 + v2[2]**2)**0.5
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            # 각도 계산 (라디안을 도로 변환)
            cos_angle = dot_product / (mag1 * mag2)
            cos_angle = max(-1, min(1, cos_angle))  # 범위 제한
            angle = om2.MAngle(math.acos(cos_angle), om2.MAngle.kRadians).asDegrees()
            
            return angle
        except Exception as e:
            print(f"Failed to calculate angle between {obj1}, {obj2}, {obj3}: {e}")
            return 0.0
    
    @staticmethod
    def create_offset_group(obj: str, name: str = None) -> str:
        """오브젝트를 위한 오프셋 그룹 생성"""
        try:
            if not name:
                name = f"{obj}_offset"
            
            offset_grp = cmds.createNode('transform', n=name)
            
            # 오브젝트의 부모 가져오기
            parent = cmds.listRelatives(obj, p=True)
            if parent:
                cmds.parent(offset_grp, parent[0])
            
            # 오브젝트를 오프셋 그룹으로 이동
            cmds.parent(obj, offset_grp)
            
            # 오프셋 그룹의 트랜스폼을 오브젝트와 매치
            TransformUtils.match_transform(obj, offset_grp)
            
            # 오브젝트 트랜스폼 리셋
            TransformUtils.reset_transform(obj)
            
            return offset_grp
        except Exception as e:
            print(f"Failed to create offset group for {obj}: {e}")
            return None
    
    @staticmethod
    def create_space_switches(control: str, spaces: List[str], space_attr: str = "space") -> bool:
        """스페이스 스위치 설정"""
        try:
            # 스페이스 속성 추가
            if not cmds.attributeQuery(space_attr, node=control, exists=True):
                cmds.addAttr(control, ln=space_attr, at='enum', en=':'.join(spaces), k=True)
            
            # 각 스페이스에 대한 컨스트레인트 생성
            constraints = []
            for i, space in enumerate(spaces):
                if space == "World":
                    continue
                
                constraint = cmds.parentConstraint(space, control, mo=True, n=f"{control}_{space}_constraint")
                constraints.append(constraint)
            
            # 스페이스 스위치 로직 설정
            for i, space in enumerate(spaces):
                if space == "World":
                    continue
                
                constraint = constraints[spaces.index(space) - 1] if spaces.index(space) > 0 else constraints[0]
                weight_attr = f"{constraint}.w0"
                
                # 조건부 연결 설정
                condition = cmds.createNode('condition', n=f"{control}_{space}_condition")
                cmds.setAttr(f"{condition}.operation", 0)  # Equal
                cmds.setAttr(f"{condition}.firstTerm", i)
                cmds.setAttr(f"{condition}.secondTerm", 1)
                cmds.setAttr(f"{condition}.colorIfTrueR", 1)
                cmds.setAttr(f"{condition}.colorIfFalseR", 0)
                
                cmds.connectAttr(f"{control}.{space_attr}", f"{condition}.firstTerm")
                cmds.connectAttr(f"{condition}.outColorR", weight_attr)
            
            return True
        except Exception as e:
            print(f"Failed to create space switches for {control}: {e}")
            return False
    
    @staticmethod
    def align_objects_to_curve(objects: List[str], curve: str, parameter: float = 0.0) -> bool:
        """오브젝트들을 커브에 정렬"""
        try:
            for obj in objects:
                # 커브의 포인트에서 포지션 가져오기
                pos = cmds.pointOnCurve(curve, pr=parameter, p=True)
                cmds.xform(obj, ws=True, t=pos)
                
                # 커브의 탄젠트 방향으로 로테이션 설정
                tangent = cmds.pointOnCurve(curve, pr=parameter, nt=True)
                # 탄젠트를 로테이션으로 변환하는 로직 필요
                
            return True
        except Exception as e:
            print(f"Failed to align objects to curve: {e}")
            return False
    
    @staticmethod
    def create_linear_spacing(objects: List[str], start_pos: Tuple[float, float, float], 
                            end_pos: Tuple[float, float, float]) -> bool:
        """오브젝트들을 선형으로 배치"""
        try:
            if len(objects) < 2:
                return False
            
            # 시작점과 끝점 사이의 간격 계산
            dx = (end_pos[0] - start_pos[0]) / (len(objects) - 1)
            dy = (end_pos[1] - start_pos[1]) / (len(objects) - 1)
            dz = (end_pos[2] - start_pos[2]) / (len(objects) - 1)
            
            for i, obj in enumerate(objects):
                pos = (start_pos[0] + dx * i, start_pos[1] + dy * i, start_pos[2] + dz * i)
                TransformUtils.set_world_position(obj, pos)
            
            return True
        except Exception as e:
            print(f"Failed to create linear spacing: {e}")
            return False
    
    @staticmethod
    def create_circular_spacing(objects: List[str], center: Tuple[float, float, float], 
                              radius: float, axis: str = 'Y') -> bool:
        """오브젝트들을 원형으로 배치"""
        try:
            import math
            
            angle_step = 2 * math.pi / len(objects)
            
            for i, obj in enumerate(objects):
                angle = i * angle_step
                
                if axis.upper() == 'X':
                    pos = (center[0], center[1] + radius * math.cos(angle), center[2] + radius * math.sin(angle))
                elif axis.upper() == 'Y':
                    pos = (center[0] + radius * math.cos(angle), center[1], center[2] + radius * math.sin(angle))
                else:  # Z axis
                    pos = (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), center[2])
                
                TransformUtils.set_world_position(obj, pos)
            
            return True
        except Exception as e:
            print(f"Failed to create circular spacing: {e}")
            return False
    
    @staticmethod
    def get_bounding_box(objects: List[str]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """오브젝트들의 바운딩 박스 계산"""
        try:
            if not objects:
                return ((0, 0, 0), (0, 0, 0))
            
            # 첫 번째 오브젝트로 초기화
            bbox = cmds.exactWorldBoundingBox(objects[0])
            min_pos = (bbox[0], bbox[1], bbox[2])
            max_pos = (bbox[3], bbox[4], bbox[5])
            
            # 나머지 오브젝트들과 비교
            for obj in objects[1:]:
                bbox = cmds.exactWorldBoundingBox(obj)
                min_pos = (min(min_pos[0], bbox[0]), min(min_pos[1], bbox[1]), min(min_pos[2], bbox[2]))
                max_pos = (max(max_pos[0], bbox[3]), max(max_pos[1], bbox[4]), max(max_pos[2], bbox[5]))
            
            return (min_pos, max_pos)
        except Exception as e:
            print(f"Failed to get bounding box: {e}")
            return ((0, 0, 0), (0, 0, 0))
    
    @staticmethod
    def center_objects(objects: List[str], center_pos: Tuple[float, float, float] = None) -> bool:
        """오브젝트들을 중심점으로 이동"""
        try:
            if not objects:
                return False
            
            if center_pos is None:
                # 바운딩 박스의 중심 계산
                min_pos, max_pos = TransformUtils.get_bounding_box(objects)
                center_pos = ((min_pos[0] + max_pos[0]) / 2, 
                            (min_pos[1] + max_pos[1]) / 2, 
                            (min_pos[2] + max_pos[2]) / 2)
            
            # 각 오브젝트의 현재 포지션 가져오기
            current_positions = []
            for obj in objects:
                pos = TransformUtils.get_world_position(obj)
                current_positions.append(pos)
            
            # 오프셋 계산 및 적용
            for i, obj in enumerate(objects):
                offset = (center_pos[0] - current_positions[i][0],
                         center_pos[1] - current_positions[i][1],
                         center_pos[2] - current_positions[i][2])
                
                new_pos = (current_positions[i][0] + offset[0],
                          current_positions[i][1] + offset[1],
                          current_positions[i][2] + offset[2])
                
                TransformUtils.set_world_position(obj, new_pos)
            
            return True
        except Exception as e:
            print(f"Failed to center objects: {e}")
            return False






