# -*- coding: utf-8 -*-
"""
Logger for Maya tools
Maya 도구들을 위한 로깅 시스템
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional


class MayaLogger:
    """Maya 도구들을 위한 로거 클래스"""
    
    def __init__(self, name: str = "MayaTools", log_level: str = "INFO"):
        """
        MayaLogger 초기화
        
        Args:
            name: 로거 이름
            log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 중복 핸들러 방지
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """핸들러 설정"""
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 파일 핸들러
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """디버그 메시지"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """정보 메시지"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """경고 메시지"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """에러 메시지"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """치명적 에러 메시지"""
        self.logger.critical(message)
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None):
        """함수 호출 로깅"""
        args_str = str(args) if args else ""
        kwargs_str = str(kwargs) if kwargs else ""
        self.debug(f"Calling {func_name}({args_str}, {kwargs_str})")
    
    def log_function_result(self, func_name: str, result=None, error=None):
        """함수 결과 로깅"""
        if error:
            self.error(f"{func_name} failed: {error}")
        else:
            self.debug(f"{func_name} completed successfully")
    
    def log_maya_operation(self, operation: str, objects: list = None, success: bool = True):
        """Maya 작업 로깅"""
        objects_str = f" on {objects}" if objects else ""
        status = "SUCCESS" if success else "FAILED"
        self.info(f"Maya operation: {operation}{objects_str} - {status}")


class ToolLogger:
    """개별 도구를 위한 로거 래퍼"""
    
    def __init__(self, tool_name: str, parent_logger: Optional[MayaLogger] = None):
        """
        ToolLogger 초기화
        
        Args:
            tool_name: 도구 이름
            parent_logger: 부모 로거
        """
        self.tool_name = tool_name
        self.parent_logger = parent_logger or MayaLogger()
        self.logger = logging.getLogger(f"{self.parent_logger.name}.{tool_name}")
    
    def debug(self, message: str):
        """디버그 메시지"""
        self.logger.debug(f"[{self.tool_name}] {message}")
    
    def info(self, message: str):
        """정보 메시지"""
        self.logger.info(f"[{self.tool_name}] {message}")
    
    def warning(self, message: str):
        """경고 메시지"""
        self.logger.warning(f"[{self.tool_name}] {message}")
    
    def error(self, message: str):
        """에러 메시지"""
        self.logger.error(f"[{self.tool_name}] {message}")
    
    def critical(self, message: str):
        """치명적 에러 메시지"""
        self.logger.critical(f"[{self.tool_name}] {message}")
    
    def log_ui_action(self, action: str, widget: str = None):
        """UI 액션 로깅"""
        widget_str = f" on {widget}" if widget else ""
        self.info(f"UI Action: {action}{widget_str}")
    
    def log_operation_start(self, operation: str):
        """작업 시작 로깅"""
        self.info(f"Starting operation: {operation}")
    
    def log_operation_end(self, operation: str, success: bool = True):
        """작업 완료 로깅"""
        status = "completed" if success else "failed"
        self.info(f"Operation {operation} {status}")


# 전역 로거 인스턴스
default_logger = MayaLogger()






