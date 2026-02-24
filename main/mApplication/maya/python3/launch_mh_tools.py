"""
MH Tools Launcher
Maya에서 MH Tools Suite를 빠르게 실행하기 위한 런처

사용법:
    Maya Script Editor에서:
    # 방법 1: 직접 import
    from python3 import launch_mh_tools
    launch_mh_tools.launch()
    
    # 방법 2: 패키지를 통한 실행
    import python3
    python3.launch_tools()
"""

import sys
import importlib


def launch():
    """MH Tools Suite 실행"""
    try:
        # 모듈 import (상대 경로 사용)
        from .tools import mh_tools_integrated
        
        # 리로드 (개발 중 변경사항 반영)
        importlib.reload(mh_tools_integrated)
        
        # UI 표시
        mh_tools_integrated.show()
        
        print("MH Tools Suite가 실행되었습니다!")
        
    except ImportError as e:
        print(f"Import 오류: {str(e)}")
        print("\n경로가 설정되어 있는지 확인하세요:")
        print("  E:/script/pythonWorkSpace/main/mApplication/maya")
        print("\n경로 추가 방법:")
        print("  import sys")
        print("  sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')")
        
    except Exception as e:
        print(f"실행 오류: {str(e)}")


# 모듈 import 시 자동 실행
if __name__ != "__main__":
    print("MH Tools Launcher 로드됨")
    print("실행하려면:")
    print("  - from python3 import launch_mh_tools")
    print("  - launch_mh_tools.launch()")
    print("또는:")
    print("  - import python3")
    print("  - python3.launch_tools()")
    
    # 자동 실행 (선택사항)
    # launch()






