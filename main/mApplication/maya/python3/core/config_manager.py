# -*- coding: utf-8 -*-
"""
Configuration Manager
설정 파일 관리를 위한 클래스
"""

import os
import json
import sys
from typing import Dict, Any, Optional


class ConfigManager:
    """설정 파일 관리 클래스"""
    
    def __init__(self, base_path=None):
        """
        ConfigManager 초기화
        
        Args:
            base_path: 설정 파일들이 위치한 기본 경로
        """
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(__file__))
        
        self.base_path = base_path
        self.json_path = os.path.join(base_path, 'Json')
        self._cache = {}
        
        # JSON 경로가 sys.path에 없으면 추가
        if self.json_path not in sys.path:
            sys.path.append(self.json_path)
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """
        JSON 파일 로드
        
        Args:
            filename: JSON 파일명
            
        Returns:
            JSON 데이터 딕셔너리
        """
        # 캐시에서 먼저 확인
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = os.path.join(self.json_path, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 캐시에 저장
            self._cache[filename] = data
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {filename}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading {filename}: {e}")
    
    def save_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        JSON 파일 저장
        
        Args:
            filename: JSON 파일명
            data: 저장할 데이터
            
        Returns:
            성공 여부
        """
        file_path = os.path.join(self.json_path, filename)
        
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 캐시 업데이트
            self._cache[filename] = data
            return True
            
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False
    
    def get_config(self, filename: str, key: str = None, default=None):
        """
        설정 값 가져오기
        
        Args:
            filename: JSON 파일명
            key: 가져올 키 (None이면 전체 데이터)
            default: 기본값
            
        Returns:
            설정 값
        """
        try:
            data = self.load_json(filename)
            
            if key is None:
                return data
            
            # 키 경로 지원 (예: "config.ui.size")
            keys = key.split('.')
            value = data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            print(f"Error getting config {filename}.{key}: {e}")
            return default
    
    def set_config(self, filename: str, key: str, value: Any) -> bool:
        """
        설정 값 저장
        
        Args:
            filename: JSON 파일명
            key: 설정 키
            value: 설정 값
            
        Returns:
            성공 여부
        """
        try:
            # 기존 데이터 로드
            data = self.load_json(filename)
            
            # 키 경로 지원
            keys = key.split('.')
            current = data
            
            # 중첩된 딕셔너리 생성
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 값 설정
            current[keys[-1]] = value
            
            # 파일 저장
            return self.save_json(filename, data)
            
        except Exception as e:
            print(f"Error setting config {filename}.{key}: {e}")
            return False
    
    def clear_cache(self, filename: str = None):
        """
        캐시 클리어
        
        Args:
            filename: 특정 파일만 클리어 (None이면 전체)
        """
        if filename:
            self._cache.pop(filename, None)
        else:
            self._cache.clear()
    
    def list_config_files(self) -> list:
        """설정 파일 목록 반환"""
        try:
            return [f for f in os.listdir(self.json_path) if f.endswith('.json')]
        except:
            return []
    
    def get_available_configs(self) -> Dict[str, str]:
        """사용 가능한 설정 파일들과 설명 반환"""
        configs = {}
        for filename in self.list_config_files():
            try:
                data = self.load_json(filename)
                description = data.get('description', f'Configuration file: {filename}')
                configs[filename] = description
            except:
                configs[filename] = f'Configuration file: {filename}'
        
        return configs






