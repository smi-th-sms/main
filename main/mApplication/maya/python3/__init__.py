"""
Python3 Scripts Package for Maya
Maya 작업을 위한 Python3 스크립트 모음
"""

# 서브패키지 import
from . import tools

# 편의 함수 - 런처
def launch_tools():
    """MH Tools Suite 실행"""
    from .launch_mh_tools import launch
    launch()

__all__ = ['tools', 'launch_tools']






