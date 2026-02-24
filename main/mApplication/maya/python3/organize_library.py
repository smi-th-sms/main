"""
라이브러리 정리 스크립트
2025-12-08 이후 생성된 테스트/임시 파일들을 백업하고 카테고리별로 정리
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# 기준 날짜 (2025-12-08)
CUTOFF_DATE = datetime(2025, 12, 8)

# 현재 디렉토리
BASE_DIR = Path(__file__).parent

# 파일 분류
PRODUCTION_TOOLS = [
    'mh_tools_integrated.py',
    'fbx_import_tool.py',
    'namespace_manager_tool.py',
    'layer_manager_tool.py',
    'scene_cleanup_tool.py',
    'skin_copy_tool.py',
    'NToNSkinCopy.py',
    'oneToNSkinCopy.py',
    'createSets.py',
    'reNamer.py',
]

RIGGING_TOOLS = [
    'FKIKSnapBakeTool.py',
    'customRiggingTool.py',
    'poseReaderV01_3.py',
    'ADVTwist.py',
    'jointSet.py',
    'vertex_reorder_tool.py',
    'offset_.py',
]

CHARACTER_TOOLS = [
    'mh_body_transfer_manager.py',
    'MHADV3.py',
    'MHADV3_refactored.py',
    'CNTManager3.py',
    'CNTManager3_refactored.py',
    'CNTManager2_fixed.py',
    'MconTool.py',
]

HOUDINI_TOOLS = [
    'connect_to_houdini.py',
    'houdini_mcp_connector.py',
    'houdini_mcp_quick_start.py',
    'houdini_mcp_server.py',
    'houdini_multiparm_callback.py',
    'demo_houdini_control.py',
    'start_houdini_mcp_test.py',
    'parts_deform_sync_callback.py',
    'HOUDINI_MCP_QUICK_GUIDE.md',
    'HOUDINI_MCP_README.md',
]

# 패턴 기반 백업 파일 (접두사)
ARCHIVE_PATTERNS = {
    'test_files': ['test_', 'final_test_'],
    'debug_files': ['debug_', 'diagnose_', 'inspect_', 'scan_'],
    'check_files': ['check_', 'verify_', 'audit_'],
    'temp_files': ['fix_', 'update_', 'setup_', 'add_', 'duplicate_', 'install_', 
                   'copy_', 'create_', 'extract_', 'find_', 'get_', 'show_', 
                   'simplify_', 'restart_', 'reload_', 'move_', 'document_', 
                   'analyze_', 'force_'],
}

# 제외할 항목
EXCLUDE_ITEMS = [
    '__init__.py',
    '__pycache__',
    'core',
    'utils',
    'icon',
    'Json',
    'MSTool',
    'rigSupport',
    'organize_library.py',  # 이 스크립트 자체
    'tools',
    'rigging',
    'character',
    'houdini_integration',
    'archive',
    # 문서 파일들
    'README.md',
    'CNTManager3_FixReport.md',
    # MEL 스크립트들
    'ColorSetting.mel',
    'ControlShape.mel',
]


def get_file_modified_date(file_path):
    """파일 수정 날짜 가져오기"""
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)


def should_archive(filename, file_path):
    """파일을 백업해야 하는지 확인"""
    # 2025-12-08 이전 파일은 유지
    modified_date = get_file_modified_date(file_path)
    if modified_date < CUTOFF_DATE:
        return False, None
    
    # 패턴 매칭
    for archive_type, patterns in ARCHIVE_PATTERNS.items():
        for pattern in patterns:
            if filename.startswith(pattern):
                return True, archive_type
    
    return False, None


def move_file(src, dst_dir, dry_run=True):
    """파일 이동 (dry_run=False일 때만 실제 이동)"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    
    if dry_run:
        print(f"  [DRY RUN] {src.name} -> {dst_dir.name}/")
    else:
        shutil.move(str(src), str(dst))
        print(f"  [MOVED] {src.name} -> {dst_dir.name}/")


def organize_library(dry_run=True):
    """라이브러리 정리"""
    print("="*70)
    print("라이브러리 정리 시작")
    print(f"기준 날짜: {CUTOFF_DATE.strftime('%Y-%m-%d')}")
    print(f"모드: {'DRY RUN (시뮬레이션)' if dry_run else 'ACTUAL (실제 이동)'}")
    print("="*70)
    
    moved_count = {'tools': 0, 'rigging': 0, 'character': 0, 'houdini': 0, 'archive': 0}
    
    # 1. Production Tools 이동
    print("\n[1] Production Tools → tools/")
    for filename in PRODUCTION_TOOLS:
        file_path = BASE_DIR / filename
        if file_path.exists():
            move_file(file_path, BASE_DIR / 'tools', dry_run)
            moved_count['tools'] += 1
    
    # 2. Rigging Tools 이동
    print("\n[2] Rigging Tools → rigging/")
    for filename in RIGGING_TOOLS:
        file_path = BASE_DIR / filename
        if file_path.exists():
            move_file(file_path, BASE_DIR / 'rigging', dry_run)
            moved_count['rigging'] += 1
    
    # 3. Character Tools 이동
    print("\n[3] Character Tools → character/")
    for filename in CHARACTER_TOOLS:
        file_path = BASE_DIR / filename
        if file_path.exists():
            move_file(file_path, BASE_DIR / 'character', dry_run)
            moved_count['character'] += 1
    
    # 4. Houdini Tools 이동
    print("\n[4] Houdini Tools → houdini_integration/")
    for filename in HOUDINI_TOOLS:
        file_path = BASE_DIR / filename
        if file_path.exists():
            move_file(file_path, BASE_DIR / 'houdini_integration', dry_run)
            moved_count['houdini'] += 1
    
    # 5. 백업 대상 파일 찾기 및 이동
    print("\n[5] Archive Files (2025-12-08 이후) → archive/")
    
    all_files = [f for f in BASE_DIR.iterdir() if f.is_file()]
    
    for file_path in all_files:
        filename = file_path.name
        
        # 제외 항목 확인
        if filename in EXCLUDE_ITEMS:
            continue
        
        # Python 파일만 처리
        if not filename.endswith('.py'):
            continue
        
        # 이미 분류된 파일인지 확인
        if (filename in PRODUCTION_TOOLS or 
            filename in RIGGING_TOOLS or 
            filename in CHARACTER_TOOLS or 
            filename in HOUDINI_TOOLS):
            continue
        
        # 백업 대상인지 확인
        should_backup, archive_type = should_archive(filename, file_path)
        
        if should_backup and archive_type:
            archive_dir = BASE_DIR / 'archive' / archive_type
            move_file(file_path, archive_dir, dry_run)
            moved_count['archive'] += 1
    
    # 6. 문서 파일 정리
    print("\n[6] Documentation Files → archive/")
    doc_files = [
        'ASSETS_COMPLETE_SUMMARY.txt',
        'ASSETS_SCRIPTS_DOCUMENTATION.txt',
        'OBJECT_MERGE2_IMPLEMENTATION_REPORT.txt',
        'PACKAGING_COMPLETE_REPORT.txt',
        'PATH_FIX_FINAL_SUMMARY.txt',
    ]
    
    for filename in doc_files:
        file_path = BASE_DIR / filename
        if file_path.exists():
            # 날짜 확인
            modified_date = get_file_modified_date(file_path)
            if modified_date >= CUTOFF_DATE:
                move_file(file_path, BASE_DIR / 'archive' / 'temp_files', dry_run)
                moved_count['archive'] += 1
    
    # 결과 출력
    print("\n" + "="*70)
    print("정리 완료!")
    print(f"  Tools: {moved_count['tools']}개")
    print(f"  Rigging: {moved_count['rigging']}개")
    print(f"  Character: {moved_count['character']}개")
    print(f"  Houdini: {moved_count['houdini']}개")
    print(f"  Archive: {moved_count['archive']}개")
    print(f"  총: {sum(moved_count.values())}개 파일 이동")
    print("="*70)
    
    if dry_run:
        print("\n[WARNING] DRY RUN 모드입니다. 실제로 파일이 이동되지 않았습니다.")
        print("          실제 이동을 원하시면 organize_library(dry_run=False)를 실행하세요.")
    
    return moved_count


if __name__ == "__main__":
    # DRY RUN (시뮬레이션)
    print("먼저 시뮬레이션을 실행합니다...\n")
    organize_library(dry_run=True)
    
    print("\n\n실제로 파일을 이동하려면 다음 명령을 실행하세요:")
    print(">>> organize_library(dry_run=False)")

