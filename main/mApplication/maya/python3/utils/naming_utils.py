# -*- coding: utf-8 -*-
"""
Naming utilities for Maya tools
Maya 도구들을 위한 네이밍 유틸리티
"""

import maya.cmds as cmds
import string
import re
from typing import List, Dict, Optional


class NamingUtils:
    """네이밍 관련 유틸리티 클래스"""
    
    @staticmethod
    def get_base_name(obj_name: str) -> str:
        """오브젝트 이름에서 베이스 이름 추출"""
        return ''.join(obj_name.split('_')[:-1])
    
    @staticmethod
    def get_suffix(obj_name: str) -> str:
        """오브젝트 이름에서 서픽스 추출"""
        parts = obj_name.split('_')
        return parts[-1] if len(parts) > 1 else ''
    
    @staticmethod
    def get_namespace(obj_name: str) -> str:
        """오브젝트 이름에서 네임스페이스 추출"""
        if ':' in obj_name:
            return obj_name.split(':')[0]
        return ''
    
    @staticmethod
    def get_short_name(obj_name: str) -> str:
        """오브젝트의 짧은 이름 반환 (네임스페이스 제외)"""
        return obj_name.split(':')[-1]
    
    @staticmethod
    def apply_namespace(obj_name: str, namespace: str) -> str:
        """네임스페이스 적용"""
        if namespace and not NamingUtils.get_namespace(obj_name):
            return f"{namespace}:{obj_name}"
        return obj_name
    
    @staticmethod
    def remove_namespace(obj_name: str) -> str:
        """네임스페이스 제거"""
        return NamingUtils.get_short_name(obj_name)
    
    @staticmethod
    def change_namespace(obj_name: str, new_namespace: str) -> str:
        """네임스페이스 변경"""
        short_name = NamingUtils.get_short_name(obj_name)
        return NamingUtils.apply_namespace(short_name, new_namespace)
    
    @staticmethod
    def pad_number(num: int, digits: int = 2) -> str:
        """숫자를 지정된 자릿수로 패딩"""
        return str(num).zfill(digits)
    
    @staticmethod
    def pad_alpha(num: int) -> str:
        """숫자를 알파벳으로 변환"""
        if 0 <= num < 26:
            return string.ascii_uppercase[num]
        return str(num)
    
    @staticmethod
    def generate_name_pattern(pattern: str, num: int, **kwargs) -> str:
        """패턴에 따라 이름 생성"""
        result = pattern
        
        # # 패턴 처리 (숫자 패딩)
        if '#' in pattern:
            hash_count = pattern.count('#')
            padded_num = NamingUtils.pad_number(num, hash_count)
            result = result.replace('#' * hash_count, padded_num)
        
        # @ 패턴 처리 (알파벳)
        if '@' in pattern:
            alpha = NamingUtils.pad_alpha(num - 1)
            result = result.replace('@', alpha)
        
        # % 패턴 처리 (prefix/suffix)
        if '%' in pattern:
            parts = pattern.split('%')
            if len(parts) == 3:  # prefix%base%suffix
                prefix = parts[0] if parts[0] else ''
                suffix = parts[2] if parts[2] else ''
                base = parts[1] if parts[1] else ''
                result = f"{prefix}{base}{suffix}"
        
        # 추가 키워드 치환
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    @staticmethod
    def rename_objects(objects: List[str], pattern: str, start_num: int = 1) -> List[str]:
        """오브젝트들을 패턴에 따라 일괄 이름 변경"""
        renamed_objects = []
        
        for i, obj in enumerate(objects):
            if not cmds.objExists(obj):
                continue
            
            new_name = NamingUtils.generate_name_pattern(pattern, start_num + i)
            
            try:
                renamed_obj = cmds.rename(obj, new_name)
                renamed_objects.append(renamed_obj)
            except Exception as e:
                print(f"Failed to rename {obj} to {new_name}: {e}")
                renamed_objects.append(obj)
        
        return renamed_objects
    
    @staticmethod
    def find_objects_by_pattern(pattern: str, namespace: str = None) -> List[str]:
        """패턴에 맞는 오브젝트들 찾기"""
        all_objects = cmds.ls(type='transform') or []
        
        if namespace:
            all_objects = [obj for obj in all_objects if NamingUtils.get_namespace(obj) == namespace]
        
        # 패턴을 정규식으로 변환
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        
        matching_objects = []
        for obj in all_objects:
            short_name = NamingUtils.get_short_name(obj)
            if re.match(regex_pattern, short_name):
                matching_objects.append(obj)
        
        return matching_objects
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """이름이 Maya 규칙에 맞는지 검증"""
        # Maya에서 허용되지 않는 문자들
        invalid_chars = [' ', '.', ',', ';', ':', '[', ']', '{', '}', '(', ')', '+', '-', '=', '*', '&', '^', '%', '$', '#', '@', '!', '~', '`', '|', '\\', '/', '<', '>', '?']
        
        for char in invalid_chars:
            if char in name:
                return False
        
        # 숫자로 시작하면 안됨
        if name[0].isdigit():
            return False
        
        return True
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """이름을 Maya 규칙에 맞게 정리"""
        # 허용되지 않는 문자들을 언더스코어로 치환
        invalid_chars = [' ', '.', ',', ';', ':', '[', ']', '{', '}', '(', ')', '+', '-', '=', '*', '&', '^', '%', '$', '#', '@', '!', '~', '`', '|', '\\', '/', '<', '>', '?']
        
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # 연속된 언더스코어 제거
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip('_')
        
        # 숫자로 시작하면 앞에 언더스코어 추가
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        return sanitized
    
    @staticmethod
    def get_unique_name(base_name: str) -> str:
        """고유한 이름 생성"""
        if not cmds.objExists(base_name):
            return base_name
        
        counter = 1
        while True:
            new_name = f"{base_name}_{counter:02d}"
            if not cmds.objExists(new_name):
                return new_name
            counter += 1
    
    @staticmethod
    def batch_rename_selection(pattern: str, start_num: int = 1) -> List[str]:
        """선택된 오브젝트들을 패턴에 따라 일괄 이름 변경"""
        selection = cmds.ls(sl=True, fl=True, r=True) or []
        if not selection:
            print("No objects selected")
            return []
        
        return NamingUtils.rename_objects(selection, pattern, start_num)
    
    @staticmethod
    def create_naming_convention(prefix: str = "", suffix: str = "", side: str = "", 
                                part: str = "", number: int = None) -> str:
        """네이밍 컨벤션에 따라 이름 생성"""
        parts = []
        
        if prefix:
            parts.append(prefix)
        if side:
            parts.append(side)
        if part:
            parts.append(part)
        if number is not None:
            parts.append(NamingUtils.pad_number(number))
        if suffix:
            parts.append(suffix)
        
        return '_'.join(parts)






