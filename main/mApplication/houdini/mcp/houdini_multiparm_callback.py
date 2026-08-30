# Houdini Python Script Node - Step 1: Basic Setup
# subnet의 paths multiparm 인스턴스에 따라 blast 노드를 생성하는 스크립트

import hou

def step1_basic_setup():
    """1단계: 기본 설정 및 파라미터 확인"""
    
    # 현재 노드 (subnet)
    node = hou.pwd()
    print(f"Current node: {node.name()}")
    print(f"Node type: {node.type().name()}")
    
    # paths 파라미터 값 가져오기
    try:
        count = node.evalParm("paths")
        print(f"Paths count: {count}")
    except:
        print("Error: 'paths' parameter not found")
        return
    
    print("Step 1 completed!")

# 스크립트 실행
if __name__ == "__main__":
    step1_basic_setup()
