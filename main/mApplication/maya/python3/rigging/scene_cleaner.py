# -*- coding: utf-8 -*-
"""
Scene Cleaner Tool
Maya 씬에서 불필요한 노드, 플러그인, 데이터를 정리하는 툴
더러운 씬을 깨끗하게! 🧹
"""

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om


class SceneCleaner:
    """Maya 씬 정리 도구"""
    
    WINDOW_NAME = "sceneCleanerWindow"
    WINDOW_TITLE = "Scene Cleaner 🧹"
    VERSION = "1.0"
    
    def __init__(self):
        """초기화"""
        self.results = {}
    
    # ========================================
    # Unknown 노드 관련
    # ========================================
    
    @staticmethod
    def get_unknown_nodes():
        """Unknown 노드 리스트 반환"""
        unknown_nodes = cmds.ls(type='unknown') or []
        unknown_dag = cmds.ls(type='unknownDag') or []
        return unknown_nodes + unknown_dag
    
    @classmethod
    def delete_unknown_nodes(cls, *args):
        """Unknown 노드 삭제"""
        try:
            unknown_nodes = cls.get_unknown_nodes()
            count = len(unknown_nodes)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ Unknown 노드가 없습니다.")
                return 0
            
            # 노드 삭제
            for node in unknown_nodes:
                try:
                    if cmds.objExists(node):
                        cmds.lockNode(node, lock=False)
                        cmds.delete(node)
                except Exception as e:
                    print(f"⚠️ {node} 삭제 실패: {e}")
            
            om.MGlobal.displayInfo(f"🗑️ Unknown 노드 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"Unknown 노드 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # Unknown 플러그인 관련
    # ========================================
    
    @staticmethod
    def get_unknown_plugins():
        """Unknown 플러그인 리스트 반환"""
        try:
            plugins = cmds.unknownPlugin(query=True, list=True) or []
            return plugins
        except:
            return []
    
    @classmethod
    def delete_unknown_plugins(cls, *args):
        """Unknown 플러그인 삭제"""
        try:
            plugins = cls.get_unknown_plugins()
            count = len(plugins)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ Unknown 플러그인이 없습니다.")
                return 0
            
            for plugin in plugins:
                try:
                    cmds.unknownPlugin(plugin, remove=True)
                    print(f"  - {plugin} 삭제됨")
                except Exception as e:
                    print(f"⚠️ {plugin} 삭제 실패: {e}")
            
            om.MGlobal.displayInfo(f"🗑️ Unknown 플러그인 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"Unknown 플러그인 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 사용하지 않는 노드 관련
    # ========================================
    
    @staticmethod
    def delete_unused_nodes(*args):
        """사용하지 않는 노드 삭제 (셰이더, 텍스처 등)"""
        try:
            # MEL 명령으로 사용하지 않는 노드 삭제
            mel.eval('MLdeleteUnused;')
            om.MGlobal.displayInfo("🗑️ 사용하지 않는 노드 삭제 완료!")
            return True
        except Exception as e:
            cmds.warning(f"사용하지 않는 노드 삭제 중 오류: {e}")
            return False
    
    @staticmethod
    def optimize_scene_size(*args):
        """씬 파일 크기 최적화 (Optimize Scene Size)"""
        try:
            mel.eval('OptimizeScene;')
            om.MGlobal.displayInfo("🗑️ 씬 최적화 완료!")
            return True
        except Exception as e:
            cmds.warning(f"씬 최적화 중 오류: {e}")
            return False
    
    # ========================================
    # 빈 그룹/트랜스폼 관련
    # ========================================
    
    @staticmethod
    def get_empty_groups():
        """빈 그룹(자식 없는 트랜스폼) 리스트 반환"""
        all_transforms = cmds.ls(type='transform') or []
        empty_groups = []
        
        # 기본 카메라 제외
        default_cameras = ['persp', 'top', 'front', 'side']
        
        for transform in all_transforms:
            if transform in default_cameras:
                continue
            
            # 자식이 없고, 셰이프도 없는 경우
            children = cmds.listRelatives(transform, children=True, fullPath=True) or []
            shapes = cmds.listRelatives(transform, shapes=True) or []
            
            if not children and not shapes:
                empty_groups.append(transform)
        
        return empty_groups
    
    @classmethod
    def delete_empty_groups(cls, *args):
        """빈 그룹 삭제"""
        try:
            # 여러 번 반복 (중첩된 빈 그룹 처리)
            total_deleted = 0
            
            for _ in range(10):  # 최대 10레벨까지
                empty_groups = cls.get_empty_groups()
                if not empty_groups:
                    break
                
                for group in empty_groups:
                    try:
                        if cmds.objExists(group):
                            cmds.delete(group)
                            total_deleted += 1
                    except:
                        pass
            
            if total_deleted == 0:
                om.MGlobal.displayInfo("✅ 빈 그룹이 없습니다.")
            else:
                om.MGlobal.displayInfo(f"🗑️ 빈 그룹 {total_deleted}개 삭제 완료!")
            
            return total_deleted
        except Exception as e:
            cmds.warning(f"빈 그룹 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 레이어 관련
    # ========================================
    
    @staticmethod
    def get_display_layers():
        """디스플레이 레이어 리스트 (defaultLayer 제외)"""
        layers = cmds.ls(type='displayLayer') or []
        return [l for l in layers if l != 'defaultLayer']
    
    @classmethod
    def delete_display_layers(cls, *args):
        """디스플레이 레이어 삭제"""
        try:
            layers = cls.get_display_layers()
            count = len(layers)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ 디스플레이 레이어가 없습니다.")
                return 0
            
            for layer in layers:
                try:
                    if cmds.objExists(layer):
                        cmds.delete(layer)
                except:
                    pass
            
            om.MGlobal.displayInfo(f"🗑️ 디스플레이 레이어 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"디스플레이 레이어 삭제 중 오류: {e}")
            return 0
    
    @staticmethod
    def get_render_layers():
        """렌더 레이어 리스트 (defaultRenderLayer 제외)"""
        layers = cmds.ls(type='renderLayer') or []
        return [l for l in layers if l != 'defaultRenderLayer']
    
    @classmethod
    def delete_render_layers(cls, *args):
        """렌더 레이어 삭제"""
        try:
            layers = cls.get_render_layers()
            count = len(layers)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ 렌더 레이어가 없습니다.")
                return 0
            
            for layer in layers:
                try:
                    if cmds.objExists(layer):
                        cmds.delete(layer)
                except:
                    pass
            
            om.MGlobal.displayInfo(f"🗑️ 렌더 레이어 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"렌더 레이어 삭제 중 오류: {e}")
            return 0
    
    @staticmethod
    def get_anim_layers():
        """애니메이션 레이어 리스트 (BaseAnimation 제외)"""
        layers = cmds.ls(type='animLayer') or []
        return [l for l in layers if l != 'BaseAnimation']
    
    @classmethod
    def delete_anim_layers(cls, *args):
        """애니메이션 레이어 삭제"""
        try:
            layers = cls.get_anim_layers()
            count = len(layers)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ 애니메이션 레이어가 없습니다.")
                return 0
            
            for layer in layers:
                try:
                    if cmds.objExists(layer):
                        cmds.delete(layer)
                except:
                    pass
            
            om.MGlobal.displayInfo(f"🗑️ 애니메이션 레이어 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"애니메이션 레이어 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 네임스페이스 관련
    # ========================================
    
    @staticmethod
    def get_namespaces():
        """네임스페이스 리스트 (UI, shared 제외)"""
        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        return [ns for ns in namespaces if ns not in ['UI', 'shared']]
    
    @classmethod
    def delete_namespaces(cls, *args):
        """네임스페이스 삭제 (내용물은 루트로 병합)"""
        try:
            namespaces = cls.get_namespaces()
            count = len(namespaces)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ 네임스페이스가 없습니다.")
                return 0
            
            # 깊은 네임스페이스부터 삭제
            namespaces.sort(key=len, reverse=True)
            
            for ns in namespaces:
                try:
                    if cmds.namespace(exists=ns):
                        cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                except Exception as e:
                    print(f"⚠️ {ns} 삭제 실패: {e}")
            
            om.MGlobal.displayInfo(f"🗑️ 네임스페이스 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"네임스페이스 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 히스토리 관련
    # ========================================
    
    @staticmethod
    def delete_all_history(*args):
        """모든 히스토리 삭제"""
        try:
            # 모든 지오메트리 선택
            all_geo = cmds.ls(geometry=True)
            if all_geo:
                transforms = cmds.listRelatives(all_geo, parent=True, fullPath=True) or []
                if transforms:
                    cmds.delete(transforms, constructionHistory=True)
            
            om.MGlobal.displayInfo("🗑️ 모든 히스토리 삭제 완료!")
            return True
        except Exception as e:
            cmds.warning(f"히스토리 삭제 중 오류: {e}")
            return False
    
    @staticmethod
    def delete_non_deformer_history(*args):
        """Deformer가 아닌 히스토리만 삭제"""
        try:
            mel.eval('doBakeNonDefHistory( 1, {"prePost" });')
            om.MGlobal.displayInfo("🗑️ Non-Deformer 히스토리 삭제 완료!")
            return True
        except Exception as e:
            cmds.warning(f"히스토리 삭제 중 오류: {e}")
            return False
    
    # ========================================
    # 스크립트 노드 관련
    # ========================================
    
    @staticmethod
    def get_script_nodes():
        """스크립트 노드 리스트"""
        nodes = cmds.ls(type='script') or []
        # 시스템 기본 노드 제외
        default_nodes = ['uiConfigurationScriptNode', 'sceneConfigurationScriptNode']
        return [n for n in nodes if n not in default_nodes]
    
    @classmethod
    def delete_script_nodes(cls, *args):
        """스크립트 노드 삭제"""
        try:
            nodes = cls.get_script_nodes()
            count = len(nodes)
            
            if count == 0:
                om.MGlobal.displayInfo("✅ 삭제할 스크립트 노드가 없습니다.")
                return 0
            
            for node in nodes:
                try:
                    if cmds.objExists(node):
                        cmds.lockNode(node, lock=False)
                        cmds.delete(node)
                        print(f"  - {node} 삭제됨")
                except Exception as e:
                    print(f"⚠️ {node} 삭제 실패: {e}")
            
            om.MGlobal.displayInfo(f"🗑️ 스크립트 노드 {count}개 삭제 완료!")
            return count
        except Exception as e:
            cmds.warning(f"스크립트 노드 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 중복 이름 관련
    # ========================================
    
    @staticmethod
    def get_duplicate_names():
        """중복된 이름을 가진 오브젝트 리스트"""
        all_obj = cmds.ls(type='transform') or []
        duplicates = []
        
        for obj in all_obj:
            if '|' in obj:
                duplicates.append(obj)
        
        return duplicates
    
    @classmethod
    def select_duplicate_names(cls, *args):
        """중복 이름 오브젝트 선택"""
        duplicates = cls.get_duplicate_names()
        count = len(duplicates)
        
        if count == 0:
            om.MGlobal.displayInfo("✅ 중복된 이름이 없습니다.")
            return []
        
        cmds.select(duplicates)
        om.MGlobal.displayInfo(f"🔍 중복 이름 오브젝트 {count}개 선택됨!")
        return duplicates
    
    # ========================================
    # Turtle 플러그인 관련
    # ========================================
    
    @staticmethod
    def delete_turtle_nodes(*args):
        """Turtle 플러그인 관련 노드 삭제"""
        try:
            turtle_nodes = ['TurtleDefaultBakeLayer', 'TurtleBakeLayerManager', 
                          'TurtleRenderOptions', 'TurtleUIOptions']
            
            deleted = 0
            for node in turtle_nodes:
                if cmds.objExists(node):
                    try:
                        cmds.lockNode(node, lock=False)
                        cmds.delete(node)
                        deleted += 1
                    except:
                        pass
            
            if deleted > 0:
                om.MGlobal.displayInfo(f"🗑️ Turtle 노드 {deleted}개 삭제 완료!")
            else:
                om.MGlobal.displayInfo("✅ Turtle 노드가 없습니다.")
            
            return deleted
        except Exception as e:
            cmds.warning(f"Turtle 노드 삭제 중 오류: {e}")
            return 0
    
    # ========================================
    # 올인원 청소
    # ========================================
    
    @classmethod
    def clean_all(cls, *args):
        """모든 정리 작업 실행"""
        print("\n" + "="*50)
        print("🧹 Scene Cleaner - 전체 정리 시작")
        print("="*50)
        
        results = {}
        
        # 1. Unknown 플러그인 삭제
        print("\n[1/9] Unknown 플러그인 정리 중...")
        results['unknown_plugins'] = cls.delete_unknown_plugins()
        
        # 2. Unknown 노드 삭제
        print("\n[2/9] Unknown 노드 정리 중...")
        results['unknown_nodes'] = cls.delete_unknown_nodes()
        
        # 3. Turtle 노드 삭제
        print("\n[3/9] Turtle 노드 정리 중...")
        results['turtle'] = cls.delete_turtle_nodes()
        
        # 4. 스크립트 노드 삭제
        print("\n[4/9] 스크립트 노드 정리 중...")
        results['script_nodes'] = cls.delete_script_nodes()
        
        # 5. 사용하지 않는 노드 삭제
        print("\n[5/9] 사용하지 않는 노드 정리 중...")
        results['unused'] = cls.delete_unused_nodes()
        
        # 6. 빈 그룹 삭제
        print("\n[6/9] 빈 그룹 정리 중...")
        results['empty_groups'] = cls.delete_empty_groups()
        
        # 7. 디스플레이 레이어 삭제
        print("\n[7/9] 디스플레이 레이어 정리 중...")
        results['display_layers'] = cls.delete_display_layers()
        
        # 8. 렌더 레이어 삭제
        print("\n[8/9] 렌더 레이어 정리 중...")
        results['render_layers'] = cls.delete_render_layers()
        
        # 9. 네임스페이스 삭제
        print("\n[9/9] 네임스페이스 정리 중...")
        results['namespaces'] = cls.delete_namespaces()
        
        print("\n" + "="*50)
        print("✨ 전체 정리 완료!")
        print("="*50 + "\n")
        
        # 결과 다이얼로그
        msg = "🧹 씬 정리 완료!\n\n"
        msg += f"• Unknown 플러그인: {results['unknown_plugins']}개\n"
        msg += f"• Unknown 노드: {results['unknown_nodes']}개\n"
        msg += f"• Turtle 노드: {results['turtle']}개\n"
        msg += f"• 스크립트 노드: {results['script_nodes']}개\n"
        msg += f"• 빈 그룹: {results['empty_groups']}개\n"
        msg += f"• 디스플레이 레이어: {results['display_layers']}개\n"
        msg += f"• 렌더 레이어: {results['render_layers']}개\n"
        msg += f"• 네임스페이스: {results['namespaces']}개\n"
        
        cmds.confirmDialog(title="Scene Cleaner", message=msg, button=["확인"])
        
        return results
    
    # ========================================
    # 씬 분석
    # ========================================
    
    @classmethod
    def analyze_scene(cls, *args):
        """씬 상태 분석 및 리포트"""
        print("\n" + "="*50)
        print("🔍 Scene Cleaner - 씬 분석")
        print("="*50)
        
        report = {}
        
        # Unknown 관련
        report['unknown_plugins'] = cls.get_unknown_plugins()
        report['unknown_nodes'] = cls.get_unknown_nodes()
        
        # 빈 그룹
        report['empty_groups'] = cls.get_empty_groups()
        
        # 레이어
        report['display_layers'] = cls.get_display_layers()
        report['render_layers'] = cls.get_render_layers()
        report['anim_layers'] = cls.get_anim_layers()
        
        # 기타
        report['namespaces'] = cls.get_namespaces()
        report['script_nodes'] = cls.get_script_nodes()
        report['duplicate_names'] = cls.get_duplicate_names()
        
        # 출력
        print(f"\n📌 Unknown 플러그인: {len(report['unknown_plugins'])}개")
        for item in report['unknown_plugins']:
            print(f"   - {item}")
        
        print(f"\n📌 Unknown 노드: {len(report['unknown_nodes'])}개")
        for item in report['unknown_nodes'][:10]:  # 최대 10개만 표시
            print(f"   - {item}")
        if len(report['unknown_nodes']) > 10:
            print(f"   ... 외 {len(report['unknown_nodes'])-10}개")
        
        print(f"\n📌 빈 그룹: {len(report['empty_groups'])}개")
        for item in report['empty_groups'][:10]:
            print(f"   - {item}")
        if len(report['empty_groups']) > 10:
            print(f"   ... 외 {len(report['empty_groups'])-10}개")
        
        print(f"\n📌 디스플레이 레이어: {len(report['display_layers'])}개")
        print(f"📌 렌더 레이어: {len(report['render_layers'])}개")
        print(f"📌 애니메이션 레이어: {len(report['anim_layers'])}개")
        print(f"📌 네임스페이스: {len(report['namespaces'])}개")
        print(f"📌 스크립트 노드: {len(report['script_nodes'])}개")
        print(f"📌 중복 이름: {len(report['duplicate_names'])}개")
        
        print("\n" + "="*50 + "\n")
        
        # 결과 다이얼로그
        total_issues = (len(report['unknown_plugins']) + len(report['unknown_nodes']) + 
                       len(report['empty_groups']) + len(report['display_layers']) +
                       len(report['render_layers']) + len(report['namespaces']) +
                       len(report['script_nodes']))
        
        msg = "🔍 씬 분석 결과\n\n"
        msg += f"• Unknown 플러그인: {len(report['unknown_plugins'])}개\n"
        msg += f"• Unknown 노드: {len(report['unknown_nodes'])}개\n"
        msg += f"• 빈 그룹: {len(report['empty_groups'])}개\n"
        msg += f"• 디스플레이 레이어: {len(report['display_layers'])}개\n"
        msg += f"• 렌더 레이어: {len(report['render_layers'])}개\n"
        msg += f"• 애니메이션 레이어: {len(report['anim_layers'])}개\n"
        msg += f"• 네임스페이스: {len(report['namespaces'])}개\n"
        msg += f"• 스크립트 노드: {len(report['script_nodes'])}개\n"
        msg += f"• 중복 이름: {len(report['duplicate_names'])}개\n"
        msg += f"\n총 정리 대상: {total_issues}개"
        
        cmds.confirmDialog(title="Scene Cleaner - 분석", message=msg, button=["확인"])
        
        return report
    
    # ========================================
    # UI 생성
    # ========================================
    
    @classmethod
    def create_ui(cls):
        """UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(cls.WINDOW_NAME, exists=True):
            cmds.deleteUI(cls.WINDOW_NAME, window=True)
        
        # 새 윈도우 생성
        window = cmds.window(cls.WINDOW_NAME, title=cls.WINDOW_TITLE, widthHeight=(350, 600))
        
        # 메인 레이아웃
        main_scroll = cmds.scrollLayout(verticalScrollBarThickness=16)
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 10))
        
        # 제목
        cmds.separator(height=10, style='none')
        cmds.text(label="🧹 Scene Cleaner", font="boldLabelFont", height=30)
        cmds.text(label="더러운 씬을 깨끗하게!", font="smallPlainLabelFont", height=20)
        cmds.separator(height=10, style='in')
        
        # ========================================
        # 분석 & 전체 정리 섹션
        # ========================================
        cmds.frameLayout(label="🔍 분석 & 전체 정리", collapsable=True, collapse=False,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="씬 분석하기",
            command=cls.analyze_scene,
            height=35,
            backgroundColor=[0.4, 0.6, 0.8],
            annotation="현재 씬의 정리 대상을 분석합니다"
        )
        
        cmds.button(
            label="⚡ 전체 정리 (All Clean)",
            command=cls.clean_all,
            height=45,
            backgroundColor=[0.8, 0.4, 0.4],
            annotation="모든 정리 작업을 한 번에 실행합니다"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # ========================================
        # Unknown 관련 섹션
        # ========================================
        cmds.separator(height=5, style='none')
        cmds.frameLayout(label="❓ Unknown 정리", collapsable=True, collapse=False,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="Unknown 플러그인 삭제",
            command=cls.delete_unknown_plugins,
            height=30,
            backgroundColor=[0.5, 0.5, 0.6],
            annotation="알 수 없는 플러그인 제거"
        )
        
        cmds.button(
            label="Unknown 노드 삭제",
            command=cls.delete_unknown_nodes,
            height=30,
            backgroundColor=[0.5, 0.5, 0.6],
            annotation="알 수 없는 노드 제거"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # ========================================
        # 노드 정리 섹션
        # ========================================
        cmds.separator(height=5, style='none')
        cmds.frameLayout(label="📦 노드 정리", collapsable=True, collapse=False,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="사용하지 않는 노드 삭제",
            command=cls.delete_unused_nodes,
            height=30,
            backgroundColor=[0.5, 0.6, 0.5],
            annotation="사용하지 않는 셰이더, 텍스처 등 삭제"
        )
        
        cmds.button(
            label="빈 그룹 삭제",
            command=cls.delete_empty_groups,
            height=30,
            backgroundColor=[0.5, 0.6, 0.5],
            annotation="자식이 없는 빈 그룹 삭제"
        )
        
        cmds.button(
            label="스크립트 노드 삭제",
            command=cls.delete_script_nodes,
            height=30,
            backgroundColor=[0.5, 0.6, 0.5],
            annotation="스크립트 노드 삭제 (바이러스 제거)"
        )
        
        cmds.button(
            label="Turtle 노드 삭제",
            command=cls.delete_turtle_nodes,
            height=30,
            backgroundColor=[0.5, 0.6, 0.5],
            annotation="Turtle 플러그인 관련 노드 삭제"
        )
        
        cmds.button(
            label="씬 크기 최적화",
            command=cls.optimize_scene_size,
            height=30,
            backgroundColor=[0.5, 0.6, 0.5],
            annotation="전체 씬 최적화 (Optimize Scene Size)"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # ========================================
        # 레이어 섹션
        # ========================================
        cmds.separator(height=5, style='none')
        cmds.frameLayout(label="📑 레이어 정리", collapsable=True, collapse=True,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="디스플레이 레이어 삭제",
            command=cls.delete_display_layers,
            height=30,
            backgroundColor=[0.6, 0.5, 0.5],
            annotation="모든 디스플레이 레이어 삭제"
        )
        
        cmds.button(
            label="렌더 레이어 삭제",
            command=cls.delete_render_layers,
            height=30,
            backgroundColor=[0.6, 0.5, 0.5],
            annotation="모든 렌더 레이어 삭제"
        )
        
        cmds.button(
            label="애니메이션 레이어 삭제",
            command=cls.delete_anim_layers,
            height=30,
            backgroundColor=[0.6, 0.5, 0.5],
            annotation="모든 애니메이션 레이어 삭제"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # ========================================
        # 히스토리 섹션
        # ========================================
        cmds.separator(height=5, style='none')
        cmds.frameLayout(label="📜 히스토리 정리", collapsable=True, collapse=True,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="모든 히스토리 삭제",
            command=cls.delete_all_history,
            height=30,
            backgroundColor=[0.6, 0.5, 0.6],
            annotation="모든 오브젝트의 히스토리 삭제"
        )
        
        cmds.button(
            label="Non-Deformer 히스토리만 삭제",
            command=cls.delete_non_deformer_history,
            height=30,
            backgroundColor=[0.6, 0.5, 0.6],
            annotation="디포머를 제외한 히스토리만 삭제"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # ========================================
        # 기타 섹션
        # ========================================
        cmds.separator(height=5, style='none')
        cmds.frameLayout(label="🔧 기타", collapsable=True, collapse=True,
marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(
            label="네임스페이스 삭제",
            command=cls.delete_namespaces,
            height=30,
            backgroundColor=[0.5, 0.5, 0.5],
            annotation="모든 네임스페이스 삭제 (루트로 병합)"
        )
        
        cmds.button(
            label="중복 이름 오브젝트 선택",
            command=cls.select_duplicate_names,
            height=30,
            backgroundColor=[0.5, 0.5, 0.5],
            annotation="같은 이름을 가진 오브젝트 선택"
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # 하단 정보
        cmds.separator(height=10, style='none')
        cmds.text(label=f"Scene Cleaner v{cls.VERSION}", font="smallPlainLabelFont", 
                 align='center', height=20)
        cmds.separator(height=10, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
        print(f"✅ {cls.WINDOW_TITLE} UI가 열렸습니다.")


def show_ui():
    """UI 표시 (외부 호출용)"""
    SceneCleaner.create_ui()


# 스크립트 직접 실행 시
if __name__ == "__main__":
    show_ui()

