# -*- coding: utf-8 -*-
"""
Base UI class for Maya tools
모든 Maya UI 도구의 베이스 클래스
"""

import sys
import maya.OpenMayaUI as omui
from maya import cmds

# PySide import with fallback
try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
    from PySide6 import __version__
    from shiboken6 import wrapInstance
    PYSIDE_VERSION = 6
except ImportError:
    try:
        from PySide2.QtCore import *
        from PySide2.QtGui import *
        from PySide2.QtWidgets import *
        from PySide2 import __version__
        from shiboken2 import wrapInstance
        PYSIDE_VERSION = 2
    except ImportError:
        print("Neither PySide6 nor PySide2 available - UI functionality limited")
        # Fallback 클래스 정의
        class QWidget:
            def __init__(self, parent=None):
                pass
            def setWindowFlags(self, flags):
                pass
            def show(self):
                pass
            def close(self):
                pass
                
        class Qt:
            Window = None
        PYSIDE_VERSION = 0


class BaseMayaUI(QWidget):
    """
    모든 Maya UI 도구의 베이스 클래스
    공통 기능과 패턴을 제공
    """
    
    def __init__(self, parent=None, *args, **kwargs):
        super(BaseMayaUI, self).__init__(parent, *args, **kwargs)
        self.setWindowFlags(Qt.Window)
        self._setup_common_ui()
        
    def _setup_common_ui(self):
        """공통 UI 설정"""
        self.setMinimumSize(300, 200)
        
    @staticmethod
    def maya_main_window():
        """Maya 메인 윈도우 포인터 반환"""
        try:
            main_window_ptr = omui.MQtUtil.mainWindow()
            if main_window_ptr:
                return wrapInstance(int(main_window_ptr), QWidget)
            else:
                print("Warning: Could not get Maya main window")
                return None
        except Exception as e:
            print(f"Error getting Maya main window: {e}")
            return None
    
    def show_tool(self):
        """도구 윈도우 표시"""
        try:
            if hasattr(self, '_previous_window') and self._previous_window:
                self._previous_window.close()
        except Exception as e:
            print(f"Error closing previous window: {e}")
            
        try:
            parent_window = self.maya_main_window()
            if parent_window:
                self.setParent(parent_window)
            self.show()
            return self
        except Exception as e:
            print(f"Error showing tool window: {e}")
            return None
    
    def closeEvent(self, event):
        """윈도우 닫기 이벤트 처리"""
        try:
            # 정리 작업 수행
            self._cleanup()
            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            event.accept()
    
    def _cleanup(self):
        """정리 작업 (서브클래스에서 오버라이드 가능)"""
        pass
    
    def log_message(self, message, level="INFO"):
        """로그 메시지 출력"""
        print(f"[{level}] {message}")
    
    def error_message(self, message):
        """에러 메시지 출력"""
        self.log_message(message, "ERROR")
    
    def warning_message(self, message):
        """경고 메시지 출력"""
        self.log_message(message, "WARNING")

