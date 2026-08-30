# ================================================================================
# I N T E G R A T E D   J O I N T   T O O L S   M A N A G E R
# ================================================================================
# Maya Python 2025. 통합된 조인트 툴 관리자
# 
# 기능 요약:
# 1) Joint Position Estimator - old mesh와 new mesh의 바인드 조인트 데이터를 통한 새로운 조인트 위치 추정
# 2) Joint Tree Duplicator - root 조인트 하이라키에 네임스페이스 추가 및 복제
# 3) Pole Vector Generator - 3개 오브젝트를 통한 pole vector 위치 계산 및 로케이터 생성
# 4) Aim Chain Tool - 선택된 오브젝트 리스트의 순차적 aim 실행
# 
# 특징:
# - 모든 툴의 통합 관리
# - 공유 root joint 관리
# - 결과값 연동 (position estimator → duplicated joints에 적용)
# - 통합 로그 시스템
# ================================================================================

import os
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import numpy as np
import json
import math
from functools import partial

# ===== 전역 상태 관리 =====
global_state = {
    'root_joint': 'root',
    'source_mesh': 'body_lod0_mesh',
    'target_mesh': '',
    'estimated_positions': {},
    'duplicator_state': {
        'orig_root': '',
        'ns_root': '',
        'dup_root': '',
        'mapping': {},
        'parents': {}
    },
    'pv_sets': [],
    'aim_sets': [],
    'settings': {  # 새로 추가
        'auto_load_pv_path': '',
        'auto_load_aim_path': ''
    }
}

# ===== 유틸리티 함수 =====
def get_descendant_joints(root):
    res=[]
    def dfs(j):
        res.append(j)
        for c in cmds.listRelatives(j, c=1, type='joint') or []:
            dfs(c)
    dfs(root); return res

def safe_unparent_world(joints):
    """already world child면 parent(w=True) skip"""
    for j in joints:
        parent = cmds.listRelatives(j, p=True)
        if not parent:
            # 이미 world child임 → 언패런트 불요
            continue
        try:
            cmds.parent(j, w=True)
        except Exception as e:
            # 에러는 통합 로그로 전달(치명 아님)
            self.logmsg(f"[WARN] {j} 언패런트 실패: {e}")

def mesh_world_points(mesh):
    """정점 월드 좌표 Nx3 numpy array 반환"""
    dag = om2.MSelectionList().add(mesh).getDagPath(0)
    pts = om2.MFnMesh(dag).getPoints(om2.MSpace.kWorld)
    return np.array([[v.x, v.y, v.z] for v in pts])

def get_dup_parents(dup_root):
    dup_joints = get_descendant_joints(dup_root)
    parents = {
        j: cmds.listRelatives(j, p=True, type='joint')[0]
            if cmds.listRelatives(j, p=True, type='joint') else None
        for j in dup_joints
    }
    return parents

def estimate_joint_pos(jnt, src_mesh, tgt_mesh, k=10, src_pts=None, tgt_pts=None):
    """단일 조인트의 위치 추정"""
    if not all(cmds.objExists(x) for x in [jnt, src_mesh, tgt_mesh]):
        return None
    jp = np.array(cmds.xform(jnt, q=1, ws=1, t=1))
    src_pts = src_pts if src_pts is not None else mesh_world_points(src_mesh)
    tgt_pts = tgt_pts if tgt_pts is not None else mesh_world_points(tgt_mesh)

    d = np.linalg.norm(src_pts - jp, axis=1)
    idx = np.argpartition(d, k)[:k]
    w = 1.0/(d[idx]+1e-8)
    offset = ((tgt_pts[idx]-src_pts[idx])*w[:,None]).sum(0)/w.sum()
    return (jp+offset).tolist()

def create_triangle_plane(name="pv_visual_plane"):
    """
    1x1 polyPlane 생성 후 하나의 vertex를 삭제하여 삼각형으로 만듭니다.
    mesh 노드명 반환.
    """
    if cmds.objExists(name):
        cmds.delete(name)
    plane, plane_shape = cmds.polyPlane(name=name, w=1, h=1, sx=1, sy=1)
    # 4번째 vertex(인덱스3) 삭제
    cmds.delete('%s.vtx[3]' % plane)
    return plane, plane_shape

def connect_triangle_points(guide_shape, node_names):
    """
    guide_shape: 메쉬 shape 노드명 (예: pv_visual_planeShape)
    node_names: [jointA, pv_loc, jointC] - worldSpace translate 연결
    """
    for idx, obj in enumerate(node_names):
        try:
            cmds.connectAttr(
                f'{obj}.translate',
                f'{guide_shape}.controlPoints[{idx}]',
                force=True
            )
        except Exception as e:
            print(f"[WARN] {obj}→triangle cp{idx} 연결 실패: {e}")

def short_path(joint):
    try:
        long_list = cmds.ls(joint, l=True)
        if not long_list:
            return joint.split(':')[-1]
        long_name = long_list[0]    # 반드시 첫번째 요소만! (string)
        parts = [p.split(':')[-1] for p in long_name.split('|') if p]
        return '|'.join(parts)
    except Exception:
        return joint.split(':')[-1]

def collect_estimates(root, src_mesh, tgt_mesh, k=10):
    src_pts, tgt_pts = mesh_world_points(src_mesh), mesh_world_points(tgt_mesh)
    result = {}
    for j in get_descendant_joints(root):
        p = estimate_joint_pos(j, src_mesh, tgt_mesh, k, src_pts, tgt_pts)
        result[short_path(j)] = p
    return result

# ===== Joint Tree Duplicator 함수 =====
def apply_namespace_to_tree(root, namespace):
    # 원본 트리에 namespace(예: 'orig') 적용
    if not cmds.namespace(exists=namespace):
        cmds.namespace(addNamespace=namespace)

    joint_list = cmds.listRelatives(root, ad=True, type='joint', f=True) or []
    joint_list.append(root)  # 루트를 마지막에 추가

    ns_joints = []
    for j in joint_list:
        short = j.split("|")[-1]
        if ":" not in short:
            try:
                ns_joint = cmds.rename(j, f"{namespace}:{short}")
                ns_joints.append(ns_joint)
            except RuntimeError:
                ns_joints.append(j)
        else:
            ns_joints.append(j)

    ns_root = ns_joints[-1]
    return ns_root, ns_joints

def duplicate_from_namespace_tree(ns_root):
    """네임스페이스 적용된 트리를 복제하고, 복제본에 'dup' 네임스페이스 지정"""
    # 1. 복제
    dup_root = cmds.duplicate(ns_root, rc=True)[0]

    # 2. 자식 중 joint만 남김
    for n in cmds.listRelatives(dup_root, ad=True, f=True) or []:
        if cmds.nodeType(n) != 'joint':
            try:
                cmds.delete(n)
            except Exception:
                pass

    namespace = "dup"
    
    if not cmds.namespace(exists=namespace):
        cmds.namespace(addNamespace=namespace)
        
    joint_list = cmds.listRelatives(dup_root, ad=True, type='joint', f=True) or []
    joint_list.append(dup_root)
    
    ns_joints = []
    # 3. 'dup' 네임스페이스를 복제 트리에 적용
    for j in joint_list:
        short = j.split("|")[-1]
        if ":" not in short:
            try:
                ns_joint = cmds.rename(j, f"{namespace}:{short}")
                ns_joints.append(ns_joint)
            except RuntimeError:
                ns_joints.append(j)
        else:
            ns_joints.append(j)

    return ns_joints[-1], ns_joints

def build_mapping_and_parents(ns_root, dup_root):
    ns_joints  = get_descendant_joints(ns_root)
    dup_joints = get_descendant_joints(dup_root)
    ns_dict  = {short_path(j): j for j in ns_joints}
    dup_dict = {short_path(j): j for j in dup_joints}
    mapping  = {ns_dict[k]: dup_dict[k] for k in ns_dict.keys() & dup_dict.keys()}
    parents  = {d: (cmds.listRelatives(d, p=True, type='joint')[0]
                    if cmds.listRelatives(d, p=True, type='joint') else None)
                for d in dup_joints}
    return mapping, parents

def safe_ls(obj, **kwargs):
    """안전한 ls 명령어"""
    try:
        result = cmds.ls(obj, **kwargs)
        return result if result else []
    except:
        return []

def safe_list_relatives(obj, **kwargs):
    """안전한 listRelatives 명령어"""
    try:
        result = cmds.listRelatives(obj, **kwargs)
        return result if result else []
    except:
        return []

def unparent_world(joints):
    """조인트들을 월드로 언페어런트 (루트 포함)"""
    # 루트 조인트도 포함하여 정렬 (깊이 순서대로)
    all_joints = sorted(joints, key=lambda x: x.count('|'))[::-1]
    safe_unparent_world(all_joints)

def duplicate_joint_tree_with_namespace(root, orig_ns='orig', dup_ns='dup'):
    # 원본 트리에 네임스페이스 적용
    ns_root, ns_joints = apply_namespace_to_tree(root, orig_ns)
    # 복제본을 만들고 dup 네임스페이스 부여
    dup_root, dup_joints = duplicate_from_namespace_tree(ns_root)
    # 계층 매핑 (short_path 등을 활용)
    mapping, parents = build_mapping_and_parents(ns_root, dup_root)
    # 루트 조인트도 포함하여 world unparent
    all_dup_joints = [dup_root] + dup_joints
    unparent_world(all_dup_joints)
    return ns_root, dup_root, mapping, parents

# ===== Pole Vector 함수 =====
def create_polevector_for_chain(mid_chain, logcb=None):
    """3개 조인트 체인에 대한 pole vector 로케이터 생성"""
    if len(mid_chain) != 3:
        if logcb: logcb(f"[ERROR] 세 조인트가 필요합니다 : {mid_chain}")
        return None
    if not all(cmds.objExists(j) for j in mid_chain):
        if logcb: logcb(f"[ERROR] 존재하지 않는 조인트 포함 : {mid_chain}")
        return None

    positions = []
    for j in mid_chain:
        pos = cmds.xform(j, q=True, ws=True, t=True)
        if not pos or len(pos) != 3:
            if logcb: logcb(f"[ERROR] 위치 조회 실패 : {j} → {pos}")
            return None
        positions.append(pos)

    a, b, c = positions
    om_a, om_b, om_c = om2.MVector(a), om2.MVector(b), om2.MVector(c)
    ab, ac = om_b - om_a, om_c - om_a
    proj = om_a + ac * ((ab * ac) / (ac * ac)) if (ac * ac) else om_b
    pv_dir = (om_b - proj).normal() if (om_b - proj).length() else om2.MVector(0, 1, 0)
    pole_pos = om_b + pv_dir * (ac.length() * 0.5)

    loc_name = f"{mid_chain[1]}_pv_loc"
    if cmds.objExists(loc_name):
        cmds.delete(loc_name)
    cmds.spaceLocator(name=loc_name)
    cmds.xform(loc_name, ws=True, t=(pole_pos.x, pole_pos.y, pole_pos.z))

    if logcb:
        logcb(f"[OK] {mid_chain[1]} → {loc_name} {tuple(round(x,2) for x in pole_pos)}")
    return loc_name

# ===== Aim Chain 함수 =====
def calc_aim_rotation_enhanced(src_pos, tgt_pos, upref_pos, aimA, upA, wut, wuv):
    """향상된 Aim 회전 계산"""
    src, tgt = om2.MVector(src_pos), om2.MVector(tgt_pos)
    aim = (tgt - src).normal()
    
    if wut == 'object' and upref_pos:
        up_vec = (om2.MVector(upref_pos) - src).normal()
    elif wut == 'vector' and wuv:
        up_vec = om2.MVector(*wuv).normal()
    else:
        up_vec = om2.MVector(0, 1, 0)
        
    side = (aim ^ up_vec).normal()
    true_up = (side ^ aim).normal()
    
    def xx(v, a): return v if not a.startswith('-') else -v
    x = xx({'x':aim, 'y':true_up, 'z':side}[aimA[-1]], aimA)
    y = xx({'x':aim, 'y':true_up, 'z':side}[upA[-1]], upA)
    z = (x ^ y).normal()
    
    m = om2.MMatrix([x.x,x.y,x.z,0, y.x,y.y,y.z,0, z.x,z.y,z.z,0, 0,0,0,1])
    q = om2.MTransformationMatrix(m).rotation()
    eul = q.asEulerRotation() if hasattr(q,'asEulerRotation') else q
    return [math.degrees(eul.x), math.degrees(eul.y), math.degrees(eul.z)]

def get_settings_file_path():
    """설정 파일 경로 반환 (Maya 사용자 디렉토리 내)"""
    try:
        maya_app_dir = cmds.internalVar(userAppDir=True)
        settings_dir = os.path.join(maya_app_dir, "integrated_joint_tools")
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
        return os.path.join(settings_dir, "settings.json")
    except:
        return os.path.join(os.path.expanduser("~"), "integrated_joint_tools_settings.json")

def save_settings():
    """설정을 파일에 저장"""
    try:
        settings_path = get_settings_file_path()
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(global_state['settings'], f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 설정 저장 실패: {e}")
        return False

def load_settings():
    """설정을 파일에서 불러오기"""
    try:
        settings_path = get_settings_file_path()
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                loaded_settings = json.load(f)
            global_state['settings'].update(loaded_settings)
            return True
    except Exception as e:
        print(f"[ERROR] 설정 불러오기 실패: {e}")
    return False

def get_namespace(node):
    """오브젝트 이름에서 네임스페이스(':'포함)만 반환, 없으면 빈 문자열."""
    if ':' in node:
        return node.rsplit('|', 1)[-1].rsplit(':', 1)[0] + ':'
    return ''

def transfer_skin_weights_auto_namespace(source_mesh, target_mesh, example_joint):
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma

    # 1. 소스 skinCluster/조인트
    src_hist = cmds.listHistory(source_mesh)
    src_skins = cmds.ls(src_hist, type="skinCluster")
    if not src_skins:
        raise RuntimeError(f"'{source_mesh}'에서 skinCluster를 찾을 수 없습니다.")
    src_skin = src_skins[0]
    src_joints = cmds.skinCluster(src_skin, q=True, inf=True)

    # 2. 선택된 바인드 조인트에서 네임스페이스 추출
    namespace = get_namespace(example_joint)
    if not namespace:
        raise RuntimeError("3번째(조인트) 선택 오브젝트에 네임스페이스가 없습니다.")

    # 3. 타겟용 바인드 조인트 리스트 생성 (네임스페이스 자동 부여)
    target_joints = [namespace + j.split(':')[-1] for j in src_joints]
    not_exists = [j for j in target_joints if not cmds.objExists(j)]
    if not_exists:
        raise RuntimeError(f"다음 네임스페이스 조인트가 신에 존재하지 않습니다: {not_exists}")

    # 4. 타겟 메쉬에 바인드
    tgt_hist = cmds.listHistory(target_mesh)
    tgt_skins = cmds.ls(tgt_hist, type="skinCluster")
    if not tgt_skins:
        cmds.skinCluster(target_joints, target_mesh, toSelectedBones=True, normalizeWeights=1, maximumInfluences=len(target_joints))
        tgt_hist = cmds.listHistory(target_mesh)
        tgt_skins = cmds.ls(tgt_hist, type="skinCluster")
    tgt_skin = tgt_skins[0]

    # 5. 소스→타겟 조인트 매핑 딕셔너리
    joint_map = dict(zip(src_joints, target_joints))

    # 6. 소스 버텍스-weight 추출
    sel_list = om.MSelectionList(); sel_list.add(src_skin)
    skinObj = sel_list.getDependNode(0)
    skinFn = oma.MFnSkinCluster(skinObj)
    infPaths = skinFn.influenceObjects()
    src_infNames = [infPaths[i].partialPathName() for i in range(len(infPaths))]
    selM = om.MSelectionList(); selM.add(source_mesh)
    dag = selM.getDagPath(0)
    meshFn = om.MFnMesh(dag); num_verts = meshFn.numVertices
    compFn = om.MFnSingleIndexedComponent()
    comp = compFn.create(om.MFn.kMeshVertComponent); compFn.addElements(range(num_verts))
    weights, infCount = skinFn.getWeights(dag, comp)

    # 7. 타겟 skinCluster의 조인트 인덱스맵
    tgt_sel = om.MSelectionList(); tgt_sel.add(tgt_skin)
    tgt_skinObj = tgt_sel.getDependNode(0)
    tgt_skinFn = oma.MFnSkinCluster(tgt_skinObj)
    tgt_infPaths = tgt_skinFn.influenceObjects()
    tgt_infNames = [tgt_infPaths[i].partialPathName() for i in range(len(tgt_infPaths))]
    tgt_infIndices = {name: i for i, name in enumerate(tgt_infNames)}
    map_indices = []
    for src_joint in src_infNames:
        tgt_joint = joint_map.get(src_joint)
        idx = tgt_infIndices.get(tgt_joint, -1)
        if idx == -1:
            raise RuntimeError(f"조인트 자동 매핑 오류: {src_joint} → {tgt_joint} 할당 불가")
        map_indices.append(idx)

    # 8. 가중치 재배열 및 정규화(버텍스별)
    from maya.api.OpenMaya import MDoubleArray
    tgt_infCount = len(tgt_infNames)
    tgt_weights = MDoubleArray(num_verts * tgt_infCount, 0.0)
    for v in range(num_verts):
        src_row = weights[v*infCount:(v+1)*infCount]
        merged = [0.0] * tgt_infCount
        for src_idx, tgt_idx in enumerate(map_indices):
            merged[tgt_idx] = src_row[src_idx]
        total = sum(merged)
        if total == 0.0:
            merged[0] = 1.0
            total = 1.0
        normed = [w / total for w in merged]
        for i, w in enumerate(normed):
            tgt_weights[v * tgt_infCount + i] = w

    # 9. 타겟에 적용
    tgt_M = om.MSelectionList(); tgt_M.add(target_mesh)
    tgt_dag = tgt_M.getDagPath(0)
    tgt_compFn = om.MFnSingleIndexedComponent()
    tgt_comp = tgt_compFn.create(om.MFn.kMeshVertComponent)
    tgt_compFn.addElements(range(num_verts))
    tgt_skinFn.setWeights(tgt_dag, tgt_comp, om.MIntArray(range(tgt_infCount)), tgt_weights, normalize=False)
    print(f"Skin weights copied with namespace \"{namespace}\" successfully.")

def mirror_object_position_cmds(source, target, axis='x'):
    """
    source: 기준 오브젝트 이름(str)
    target: 미러 좌표를 적용할 오브젝트 이름(str)
    axis: 'x', 'y', 'z' 중 하나 (기본 X축)
    """
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    pos = cmds.xform(source, q=True, ws=True, t=True)
    mirrored = list(pos)
    mirrored[idx] *= -1
    cmds.xform(target, ws=True, t=mirrored)
    print("[MIRROR] {}의 위치 {} → {}(미러): {}".format(source, pos, target, mirrored))

def find_side_pair_name(name, direction='l2r'):
    """
    name: ex) 'calf_l_pv_loc'
    direction: 'l2r' or 'r2l'
    """
    if name.endswith("_pv_loc"):
        base = name[:-7]  # '_pv_loc' 제거
        suffix = "_pv_loc"
    else:
        base = name
        suffix = ""
    # 이제 base에서 side만 치환
    pairs = [
        ('left', 'right'), ('Left', 'Right'), ('LEFT', 'RIGHT'),
        ('right', 'left'), ('Right', 'Left'), ('RIGHT', 'LEFT'),
        ('_l_', '_r_'), ('_r_', '_l_'), ('.l_', '.r_'), ('.r_', '.l_'),
        ('_L_', '_R_'), ('_R_', '_L_'), ('_l', '_r'), ('_r', '_l'),
        ('_L', '_R'), ('_R', '_L')
    ]
    new_name = base
    for left, right in pairs:
        if direction == 'l2r':
            before, after = left, right
        else:
            before, after = right, left
        if before in new_name:
            return new_name.replace(before, after, 1) + suffix
    # 마지막 단어 l/r
    if direction == 'l2r':
        if new_name.endswith('_l'):
            return new_name[:-2] + '_r' + suffix
    else:
        if new_name.endswith('_r'):
            return new_name[:-2] + '_l' + suffix
    return None

def load_metahuman_patterns():
    """메타휴먼 네이밍 패턴 json 파일을 불러온다."""
    json_path = os.path.join(os.path.dirname(__file__), "Json", "metahuman_joint_patterns.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"패턴 파일이 존재하지 않습니다: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        patterns = json.load(f)
    return patterns

def test_metahuman_patterns_load_and_save():
    """패턴 저장/로드 기능 체크용 테스트 함수 (콘솔 출력)"""
    try:
        patterns = load_metahuman_patterns()
        print("[TEST] 패턴 로드 성공:", patterns)
        # 저장 테스트 (임시 파일)
        test_path = os.path.join(os.path.dirname(__file__), "Json", "test_patterns.json")
        with open(test_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
        print(f"[TEST] 패턴 저장 성공: {test_path}")
        os.remove(test_path)
        print("[TEST] 임시 파일 삭제 완료")
    except Exception as e:
        print(f"[TEST] 패턴 로드/저장 실패: {e}")

# ===== 메인 UI 클래스 =====
class IntegratedJointToolsManager:
    def __init__(self):
        self.window_name = "IntegratedJointToolsManager"
        self.log_field = None
        self.build_ui()

    def logmsg(self, msg):
        if self.log_field:
            prev = cmds.scrollField(self.log_field, q=True, tx=True)
            cmds.scrollField(self.log_field, e=True, tx=prev + ('' if prev.endswith('\n') or not prev else '\n') + msg)
        # print(msg)  # <-- 테스트 시 print 유지(완전히 콘솔 출력을 막으려면 생략 또는 redirect)

    def redirect_stdout_to_log(self):
        class LogRedirector(object):
            def __init__(self, tool):
                self.tool = tool
            def write(self, txt):
                if txt.strip():
                    self.tool.logmsg(txt.strip())
            def flush(self): pass
        sys.stdout = LogRedirector(self)
        sys.stderr = LogRedirector(self)
    
    def build_ui(self):
        """메인 UI 구성"""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        cmds.window(self.window_name, t="Metahuman Body Transfer Manager", wh=(600, 800))
        main_col = cmds.columnLayout(adjustableColumn=True, rs=8)

        # === 공유 root joint 선택 섹션 ===
        cmds.frameLayout(l="공유 Root Joint 설정", cll=True, cl=False, parent=main_col)
        cmds.text(l="모든 툴에서 사용할 공통 Root Joint를 설정하세요", align='left')
        
        root_row = cmds.rowLayout(nc=3, cw3=(80, 350, 80), adj=2)
        cmds.text(l="Root Joint:", w=80)
        self.root_tf = cmds.textField(tx='root')
        cmds.button(l="선택", w=80, c=self.pick_root_joint, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(main_col)

        # === Joint Position Estimator 섹션 ===
        cmds.frameLayout(l="1. Joint Position Estimator", cll=True, cl=False, parent=main_col)
        
        estimate_column = cmds.columnLayout(adjustableColumn=True, rs=5)
        
        # Source Mesh
        src_row = cmds.rowLayout(nc=3, cw3=(80, 350, 80), adj=2)
        cmds.text(l="Source:", w=80)
        self.src_tf = cmds.textField(tx='body_lod0_mesh')
        cmds.button(l="선택", w=80, c=self.pick_source_mesh, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(estimate_column)
        
        # Target Mesh
        tgt_row = cmds.rowLayout(nc=3, cw3=(80, 350, 80), adj=2)
        cmds.text(l="Target:", w=80)
        self.tgt_tf = cmds.textField(tx='')
        cmds.button(l="선택", w=80, c=self.pick_target_mesh, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(estimate_column)
        
        cmds.button(l="위치 추정 실행", h=30, c=self.run_position_estimation, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(estimate_column)
        
        cmds.setParent(main_col)

        # === Joint Tree Duplicator 섹션 ===
        cmds.frameLayout(l="2. Joint Tree Duplicator", cll=True, cl=False, parent=main_col)
        cmds.text(l="원본 조인트에 'orig:' 네임스페이스를 적용하고 복제본에 'dup:' 네임스페이스를 적용합니다", align='left')

        cmds.button(l="조인트 트리 복제 실행", h=30, c=self.run_tree_duplication, bgc=(0.56, 0.79, 0.76))
        cmds.button(l="추정된 위치를 복제본에 적용", h=30, c=self.apply_estimated_positions, bgc=(0.56, 0.79, 0.76))

        # === Pole Vector Generator 섹션 ===
        cmds.frameLayout(l="3. Pole Vector Generator", cll=True, cl=True, parent=main_col)
        
        cmds.text(l="조인트 3개 선택 후 추가 → 전체 생성", align='left')
        
        pv_column = cmds.columnLayout(adjustableColumn=True, rs=5)

        # 1줄: 세트 관리 (3개)
        pv_row1 = cmds.rowLayout(nc=3, cw3=(100, 100, 100))
        cmds.button(l="3개 추가", w=100, c=self.add_pv_set, bgc=(0.87, 0.68, 0.09))
        cmds.button(l="선택삭제", w=100, c=self.remove_pv_selected)
        cmds.button(l="전체삭제", w=100, c=self.clear_pv_all)
        cmds.setParent(pv_column)

        # 2줄: 파일 관리 (2개)
        pv_row2 = cmds.rowLayout(nc=2, cw2=(150, 150))
        cmds.button(label="저장", w=150, c=self.save_pv_list)
        cmds.button(label="불러오기", w=150, c=self.load_pv_list)
        cmds.setParent(pv_column)
        
        # Pole Vector Generator 섹션에 추가(적당한 위치에 삽입)
        pv_mirror_row = cmds.rowLayout(nc=2, cw2=[110, 180])
        cmds.text(l="미러 방향:", w=110, parent=pv_mirror_row)
        self.pv_mirror_dir = cmds.optionMenuGrp(label="", parent=pv_mirror_row, cw2=(0, 160))
        cmds.menuItem(label="L → R")
        cmds.menuItem(label="R → L")
        cmds.setParent(pv_column)

        pv_row3 = cmds.rowLayout(nc=1, adj=1)
        self.pv_list = cmds.textScrollList(h=100)
        cmds.setParent(pv_column)

        cmds.setParent(main_col)

        # 3줄: 실행 (1개)
        pv_row4 = cmds.rowLayout(nc=1, adj=1)
        cmds.button(l="PV 생성", h=35, c=self.create_all_pv, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(main_col)
        
        pv_row5 = cmds.rowLayout(nc=1, adj=1)
        cmds.button(
            l="PV 미러 실행 (좌↔우)",
            c=lambda *_: self.mirror_all_pv_locators(axis='x'),
            bgc=(0.56, 0.79, 0.76)
        )
        cmds.setParent(main_col)
        
        # === Aim Chain Tool 섹션 ===
        cmds.frameLayout(l="4. Aim Chain Tool", cll=True, cl=True, parent=main_col)
        
        aim_column = cmds.columnLayout(adjustableColumn=True, rs=5)
        
        # Aim 설정
        aim_row1 = cmds.rowLayout(nc=6, cw3=(100, 100, 100))
        self.aim_axis = cmds.optionMenuGrp(l='Aim:', cw2=(30, 100))
        for ax in ['x', '-x', 'y', '-y', 'z', '-z']:
            cmds.menuItem(label=ax)
        self.up_axis = cmds.optionMenuGrp(l='Up:', cw2=(20, 100))
        for ax in ['y', '-y', 'x', '-x', 'z', '-z']:
            cmds.menuItem(label=ax)
        self.wut = cmds.optionMenuGrp(l='UpType:', cw2=(40, 100))
        for typ in ['scene', 'vector', 'object']:
            cmds.menuItem(label=typ)
        cmds.setParent(aim_column)
        
        aim_row2 = cmds.rowLayout(nc=2, cw2=(150, 150))
        # World Up Vector
        self.wuv_tf = cmds.textFieldGrp(l='UpVector:', tx='0,1,0', cw2=(50, 50))
        cmds.setParent(aim_column)
        
        # 회전축 체크박스
        aim_row3 = cmds.rowLayout(nc=4, cw4=(70, 70, 70, 70))
        cmds.text(l="적용축:", w=70)
        self.chk_x = cmds.checkBox(l='X', v=True)
        self.chk_y = cmds.checkBox(l='Y', v=True)
        self.chk_z = cmds.checkBox(l='Z', v=True)
        cmds.setParent(aim_column)
        
        pv_option_row = cmds.rowLayout(nc=2, cw2=(50, 150))
        cmds.text(l="PV 옵션:", w=70)
        self.chk_delete_pv = cmds.checkBox(l='Aim 실행 후 PV 로케이터 삭제', v=True)
        cmds.setParent(aim_column)
        
        # Aim 리스트 관리
        # 1줄: 세트 관리 (3개)
        aim_row4 = cmds.rowLayout(nc=3, cw3=(100, 100, 100))
        cmds.button(l="Aim체인 추가", w=100, c=self.add_aim_chain, bgc=(0.87, 0.68, 0.09))
        cmds.button(l="선택삭제", w=100, c=self.remove_aim_selected)
        cmds.button(l="전체삭제", w=100, c=self.clear_aim_all)
        cmds.setParent(aim_column)

        # 2줄: 파일 관리 (2개)
        aim_row5 = cmds.rowLayout(nc=3, cw3=(100, 100, 100))
        cmds.button(label="저장", w=100, c=self.save_aim_list)
        cmds.button(label="불러오기", w=100, c=self.load_aim_list)
        cmds.setParent(aim_column)

        aim_row6 = cmds.rowLayout(nc=1, adj=1)
        self.aim_list = cmds.textScrollList(h=100)
        cmds.setParent(aim_column)

        cmds.setParent(main_col)

        aim_row7 = cmds.rowLayout(nc=1, adj=1)
        cmds.button(l="Aim 실행", c=self.run_all_aim, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(main_col)

        # === 최종 정리 섹션 ===
        cmds.frameLayout(l="5. 최종 정리", cll=True, cl=False, parent=main_col)
        
        final_column = cmds.columnLayout(adjustableColumn=True, rs=5)
        
        fl_row = cmds.rowLayout(nc=1, adj=1)
        cmds.button(l="하이라키 복원 및 정리", h=30, c=self.restore_hierarchy_and_cleanup, bgc=(0.56, 0.79, 0.76))
        cmds.setParent(final_column)
        
        cmds.setParent(main_col)

        cmds.frameLayout(l="자동 불러오기 설정", cll=True, cl=True, parent=main_col)
        autoload_column = cmds.columnLayout(adjustableColumn=True, rs=5)
    
        # PV 자동 불러오기 경로
        pv_auto_row = cmds.rowLayout(nc=3, cw3=(100, 300, 80))
        cmds.text(l="PV 자동경로:", w=100)
        self.pv_auto_path_tf = cmds.textField(tx=global_state['settings'].get('auto_load_pv_path', ''))
        cmds.button(l="찾기", w=80, c=self.browse_pv_auto_path)
        cmds.setParent(autoload_column)
        
        # Aim 자동 불러오기 경로
        aim_auto_row = cmds.rowLayout(nc=3, cw3=(100, 300, 80))
        cmds.text(l="Aim 자동경로:", w=100)
        self.aim_auto_path_tf = cmds.textField(tx=global_state['settings'].get('auto_load_aim_path', ''))
        cmds.button(l="찾기", w=80, c=self.browse_aim_auto_path)
        cmds.setParent(autoload_column)
        
        # 설정 저장 버튼
        auto_load_row = cmds.rowLayout(nc=1, adj=1)
        cmds.button(l="자동 불러오기 설정 저장", h=25, c=self.save_auto_load_settings)
        cmds.setParent(autoload_column)
        
        cmds.setParent(main_col)
        
        # Joint Tree Duplicator 섹션 하단 등 적합 위치에 배치
        cmds.button(
            l="스킨웨이트 복사 (NS 매핑)", h=32,
            c=self.exec_transfer_skin_weights,
            bgc=(0.56, 0.79, 0.76)
        )
        cmds.setParent(main_col)

        # === 로그 섹션 ===
        cmds.frameLayout(l="로그", cll=True, cl=False, parent=main_col)
        self.log_field = cmds.scrollField(h=200, ed=False, ww=True)

        cmds.showWindow(self.window_name)
        self.logmsg("[INFO] 통합 조인트 툴 매니저가 시작되었습니다.")
        
        # 설정 불러오기 및 자동 로드 실행
        if load_settings():
            self.logmsg("[INFO] 설정 불러오기 완료")
            
            # PV 세트 자동 불러오기
            if self.auto_load_pv_sets():
                pass  # 이미 로그 메시지 출력됨
            
            # Aim 세트 자동 불러오기  
            if self.auto_load_aim_sets():
                pass  # 이미 로그 메시지 출력됨
        else:
            self.logmsg("[INFO] 기본 설정으로 시작합니다.")

    # === 콜백 함수들 ===
    def pick_root_joint(self, *_):
        """Root Joint 선택"""
        sel = [x for x in cmds.ls(sl=True, type='joint')]
        if sel:
            root_name = sel[0].split("|")[-1]
            cmds.textField(self.root_tf, e=True, tx=root_name)
            global_state['root_joint'] = root_name
            self.logmsg(f"[INFO] Root Joint 설정: {root_name}")

    def pick_source_mesh(self, *_):
        """Source Mesh 선택"""
        sel = [x for x in cmds.ls(sl=True, type='transform')]
        if sel and cmds.listRelatives(sel[0], shapes=True, type='mesh'):
            mesh_name = sel[0].split("|")[-1]
            cmds.textField(self.src_tf, e=True, tx=mesh_name)
            global_state['source_mesh'] = mesh_name
            self.logmsg(f"[INFO] Source Mesh 설정: {mesh_name}")

    def pick_target_mesh(self, *_):
        """Target Mesh 선택"""
        sel = [x for x in cmds.ls(sl=True, type='transform')]
        if sel and cmds.listRelatives(sel[0], shapes=True, type='mesh'):
            mesh_name = sel[0].split("|")[-1]
            cmds.textField(self.tgt_tf, e=True, tx=mesh_name)
            global_state['target_mesh'] = mesh_name
            self.logmsg(f"[INFO] Target Mesh 설정: {mesh_name}")

    def run_position_estimation(self, *_):
        """위치 추정 실행"""
        root = global_state.get('root_joint', '')
        src = global_state.get('source_mesh', '')
        tgt = global_state.get('target_mesh', '')

        if not (root and cmds.objExists(root) and cmds.nodeType(root) == 'joint'):
            self.logmsg("[ERROR] Root Joint가 올바르지 않습니다.")
            return
        if not (src and cmds.objExists(src) and cmds.listRelatives(src, shapes=True, type='mesh')):
            self.logmsg("[ERROR] Source Mesh가 올바르지 않습니다.")
            return
        if not (tgt and cmds.objExists(tgt) and cmds.listRelatives(tgt, shapes=True, type='mesh')):
            self.logmsg("[ERROR] Target Mesh가 올바르지 않습니다.")
            return

        self.logmsg("[INFO] 위치 추정 계산 중...")
        estimates = collect_estimates(root, src, tgt, k=10)
        global_state['estimated_positions'] = estimates

        for j, p in estimates.items():
            if p:
                self.logmsg(f"{j:>20} -> {tuple(round(v, 3) for v in p)}")
            else:
                self.logmsg(f"{j:>20} -> (추정 실패)")
        
        self.logmsg("[DONE] 위치 추정 완료.")

    def run_tree_duplication(self, *_):
        """조인트 트리 복제 실행"""
        root = global_state.get('root_joint', '')
        
        if not (root and cmds.objExists(root) and cmds.nodeType(root) == 'joint'):
            self.logmsg("[ERROR] Root Joint가 올바르지 않습니다.")
            return

        self.logmsg(f"[INFO] '{root}' 트리에 'orig:' 네임스페이스 적용 및 'dup:' 복제 시작...")

        try:
            # 'orig' 네임스페이스로 고정
            ns_root, dup_root, mapping, parents = duplicate_joint_tree_with_namespace(root, 'orig')

            global_state['duplicator_state'] = {
                'orig_root': root,
                'ns_root': ns_root,
                'dup_root': dup_root,
                'mapping': mapping,
                'parents': parents
            }

            self.logmsg(f"[OK] 네임스페이스 적용 완료 → {ns_root}")
            self.logmsg(f"[OK] 복제 완료 → {dup_root}")
            self.logmsg(f" 조인트 수: {len(mapping)} | 월드 언페어런트 완료")

        except Exception as e:
            self.logmsg(f"[ERROR] 복제 중 오류 발생: {e}")


    def apply_estimated_positions(self, *_):
        est = global_state.get('estimated_positions', {})
        map_ = global_state.get('duplicator_state', {}).get('mapping', {})
        if not est or not map_:
            self.logmsg("[ERROR] 위치 추정·복제를 먼저 실행하세요."); return
        applied = 0
        for ns_joint, dup_joint in map_.items():
            key = short_path(ns_joint)
            pos = est.get(key)
            if not pos:
                self.logmsg(f"[WARN] 위치값 없음: {dup_joint} (key={key})")
                continue
            try:
                cmds.xform(dup_joint, ws=True, t=pos)
                applied += 1
            except Exception as e:
                self.logmsg(f"[ERROR] {dup_joint} 적용실패: {e}")
        self.logmsg(f"[DONE] 위치 적용: {applied}/{len(map_)}")

    def add_pv_set(self, *_):
        """PV 세트 추가"""
        sel = [j for j in cmds.ls(selection=True, type='joint')]
        if len(sel) != 3:
            self.logmsg("[ERROR] 정확히 3개의 조인트를 선택하세요.")
            return

        entry = [x.split("|")[-1] for x in sel]
        if entry in global_state['pv_sets']:
            self.logmsg(f"[SKIP] 이미 존재하는 PV 세트: {entry}")
            return

        global_state['pv_sets'].append(entry)
        self.refresh_pv_list()
        self.logmsg(f"[ADD] PV 세트 추가: {entry}")

    def remove_pv_selected(self, *_):
        """선택된 PV 세트 삭제 (여러 개 선택 가능)"""
        sel_idx = cmds.textScrollList(self.pv_list, q=True, selectIndexedItem=True)
        if not sel_idx:
            self.logmsg("[ERROR] 삭제할 PV 항목을 선택하세요.")
            return

        # 여러 개 선택된 항목을 역순으로 삭제 (인덱스 오류 방지)
        for i in sorted([idx - 1 for idx in sel_idx], reverse=True):
            global_state['pv_sets'].pop(i)
        
        self.refresh_pv_list()
        self.logmsg(f"[DEL] {len(sel_idx)}개 PV 세트 삭제")

    def clear_pv_all(self, *_):
        """모든 PV 세트 삭제"""
        count = len(global_state['pv_sets'])
        global_state['pv_sets'] = []
        self.refresh_pv_list()
        self.logmsg(f"[CLEAR] 전체 PV 세트 삭제: {count}개")

    def refresh_pv_list(self):
        """PV 리스트 새로고침"""
        cmds.textScrollList(self.pv_list, e=True, removeAll=True)
        for s, m, e in global_state['pv_sets']:
            cmds.textScrollList(self.pv_list, e=True, append=f"{s} | {m} | {e}")

    def create_pv_and_visual_plane(self, pv_set):
        """
        pv_set: [jointA, jointB, jointC] (polevector 생성 대상)
        - jointA: 시작 조인트
        - jointB: 중간(폴벡터 기준)/PV를 생성할 조인트
        - jointC: 끝 조인트
        """
        # 1. pole vector locator 생성
        pv_loc_name = create_polevector_for_chain(pv_set, logcb=self.logmsg)
        # 2. plane mesh 생성 (고유 네이밍)
        plane_name = f"{pv_set[1]}_pvGuide_plane"
        plane, plane_shape = create_triangle_plane(plane_name)
        # 3. 연결: jointA, pv_loc, jointC → plane 각 vertex
        connect_triangle_points(
            f"{plane}Shape",
            [pv_set[0], pv_loc_name, pv_set[2]]
        )
        self.logmsg(f"[OK] PV 로케이터+가이드 plane 연결: {pv_set} → {plane}")

    def delete_pv_guides(self):
        """PV 가이드 mesh(삼각형 plane)들 삭제"""
        try:
            all_transforms = cmds.ls(type="transform") or []
            # 네임스페이스 안전 고려, 이름 끝 비교
            pv_guides = [obj for obj in all_transforms if obj.split(":")[-1].endswith("_pvGuide_plane")]
            if pv_guides:
                cmds.delete(pv_guides)
                self.logmsg(f"[CLEANUP] {len(pv_guides)}개의 PV 가이드(plane) 삭제 완료")
                return len(pv_guides)
            else:
                self.logmsg("[INFO] 삭제할 PV 가이드가 없습니다.")
                return 0
        except Exception as e:
            self.logmsg(f"[ERROR] PV 가이드 삭제 실패: {e}")
            return 0

    def create_all_pv(self, *_):
        """모든 PV 생성"""
        pv_sets = global_state['pv_sets']
        if not pv_sets:
            
            self.logmsg("[ERROR] 생성할 PV 세트가 없습니다.")
            return

        self.logmsg(f"[INFO] PoleVector {len(pv_sets)}개 생성 시작...")
        success_count = 0

        for pv_set in pv_sets:
            if not all(cmds.objExists(j) for j in pv_set):
                self.logmsg(f"[SKIP] 조인트 없음: {pv_set}")
                continue

            try:
                loc_name = create_polevector_for_chain(pv_set, logcb=self.logmsg)
                if loc_name:
                    success_count += 1
                self.create_pv_and_visual_plane(pv_set)
            except Exception as e:
                self.logmsg(f"[ERROR] PV 생성 실패 {pv_set}: {e}")
                self.logmsg(f"[ERROR] PV+가이드 생성 실패 {pv_set}: {e}")

        self.logmsg(f"[DONE] PoleVector 생성 완료: {success_count}/{len(pv_sets)}개")

    def add_aim_chain(self, *_):
        """Aim 체인 추가"""
        sel = cmds.ls(sl=True)
        if not sel or len(sel) < 2:
            self.logmsg("[ERROR] 최소 2개 이상의 오브젝트를 선택하세요.")
            return

        aimA = cmds.optionMenuGrp(self.aim_axis, q=True, v=True)
        upA = cmds.optionMenuGrp(self.up_axis, q=True, v=True)
        wut = cmds.optionMenuGrp(self.wut, q=True, v=True)
        wuV = self._parse_vec(self.wuv_tf, "0,1,0")
        applyAxes = self._get_enabled_axes()

        if wut == "object":
            if len(sel) < 3:
                self.logmsg("[ERROR] object up: 최소 3개(aim pair 2개+up object 1개) 선택 필요")
                return
            upObj = sel[-1]
            items = sel[:-1]
            for i in range(len(items) - 1):
                global_state['aim_sets'].append({
                    "startJoint": items[i], "endJoint": items[i+1],
                    "aimAxis": aimA, "upAxis": upA, "worldUpType": wut,
                    "worldUpVector": wuV, "upObject": upObj, "applyAxes": applyAxes
                })
            self.logmsg(f"[ADD] {len(items)-1}개 aim pair 등록 (upObj:{upObj})")
        else:
            items, targets = sel[:-1], sel[1:]
            for i in range(len(items)):
                global_state['aim_sets'].append({
                    "startJoint": items[i], "endJoint": targets[i],
                    "aimAxis": aimA, "upAxis": upA, "worldUpType": wut,
                    "worldUpVector": wuV, "upObject": None, "applyAxes": applyAxes
                })
            self.logmsg(f"[ADD] {len(items)}개 aim pair 등록")
        
        self.refresh_aim_list()

    def remove_aim_selected(self, *_):
        """선택된 Aim 세트 삭제"""
        sel_idx = cmds.textScrollList(self.aim_list, q=True, selectIndexedItem=True)
        if not sel_idx:
            self.logmsg("[ERROR] 삭제할 Aim 항목을 선택하세요.")
            return

        for i in sorted([idx - 1 for idx in sel_idx], reverse=True):
            global_state['aim_sets'].pop(i)
        
        self.refresh_aim_list()
        self.logmsg(f"[DEL] {len(sel_idx)}개 aim 세트 삭제")

    def clear_aim_all(self, *_):
        """모든 Aim 세트 삭제"""
        count = len(global_state['aim_sets'])
        global_state['aim_sets'] = []
        self.refresh_aim_list()
        self.logmsg(f"[CLEAR] 전체 Aim 세트 삭제: {count}개")

    def refresh_aim_list(self):
        """Aim 리스트 새로고침"""
        cmds.textScrollList(self.aim_list, e=True, removeAll=True)
        for row in global_state['aim_sets']:
            s, e = row['startJoint'], row['endJoint']
            aimA, upA, wuT = row['aimAxis'], row['upAxis'], row['worldUpType']
            upObj = row.get('upObject')
            applyAxes = row.get('applyAxes', [])
            applyaxstr = "".join("xyz"[i] for i in applyAxes)
            upstr = f", upObj={upObj}" if upObj else ""
            axs = f", 축:{applyaxstr}" if applyaxstr else ""
            cmds.textScrollList(self.aim_list, e=True, append=f"{s}→{e} (aim:{aimA}, up:{upA}, wuT:{wuT}{upstr}{axs})")

    def run_all_aim(self, *_):
        """모든 Aim 실행"""
        aim_sets = global_state['aim_sets']
        if not aim_sets:
            self.logmsg("[ERROR] 실행할 Aim 세트가 없습니다.")
            return
        self.logmsg(f"[INFO] Aim Chain {len(aim_sets)}개 실행 시작...")
        success_count = 0
        for setcfg in aim_sets:
            joint, tgt_joint = setcfg['startJoint'], setcfg['endJoint']
            aimA, upA, wuT, wuV, upObj = setcfg['aimAxis'], setcfg['upAxis'], setcfg['worldUpType'], setcfg['worldUpVector'], setcfg.get("upObject")
            applyAxes = setcfg.get('applyAxes', [0, 1, 2])
            if not (cmds.objExists(joint) and cmds.objExists(tgt_joint)):
                self.logmsg(f"[SKIP] 없는 조인트 {joint}/{tgt_joint}")
                continue
            using_pv_locator = upObj and upObj.endswith('_pv_loc') and cmds.objExists(upObj)
            try:
                src_pos = cmds.xform(joint, q=True, ws=True, t=True)
                tgt_pos = cmds.xform(tgt_joint, q=True, ws=True, t=True)
                upref_pos = cmds.xform(upObj, q=True, ws=True, t=True) if (upObj and cmds.objExists(upObj)) else None
                rot_deg = calc_aim_rotation_enhanced(src_pos, tgt_pos, upref_pos, aimA, upA, wuT, wuV)
                oldrot = cmds.xform(joint, q=True, ws=True, rotation=True)
                newrot = list(oldrot)
                if 0 in applyAxes: newrot[0] = rot_deg[0]
                if 1 in applyAxes: newrot[1] = rot_deg[1]
                if 2 in applyAxes: newrot[2] = rot_deg[2]
                cmds.xform(joint, ws=True, rotation=newrot)
                success_count += 1
                pv_indicator = " [PV사용]" if using_pv_locator else ""
                self.logmsg(f"[OK] {joint}→{tgt_joint} {tuple(round(x,1) for x in newrot)}{pv_indicator}")
            except Exception as e:
                self.logmsg(f"[ERROR] {joint}→{tgt_joint}: {e}")
        self.logmsg(f"[DONE] Aim Chain 실행 완료: {success_count}/{len(aim_sets)}개")
        # === Aim 외 패턴 적용 ===
        try:
            patterns = load_metahuman_patterns()
            rotate_match_patterns = patterns.get("rotate_match_patterns", [])
            dup_joints = cmds.ls("dup:*", type="joint") or []
            aim_joints = set([cfg['startJoint'] for cfg in global_state['aim_sets']])
            target_joints = [j for j in dup_joints if any(pat in j for pat in rotate_match_patterns) and j not in aim_joints]
            # === 하이라키 기반 dup 부모 찾기용 orig_map/dup_map 생성 ===
            dup_state = global_state.get('duplicator_state', {})
            dup_root = dup_state.get('dup_root', '')
            orig_ns_root = dup_state.get('orig_root', '')
            # orig 네임스페이스 조인트 전체
            orig_ns_joints = []
            if orig_ns_root and cmds.objExists(f"orig:{orig_ns_root}"):
                orig_ns_joints = cmds.ls("orig:*", type="joint")
            # dup 전체 (루트 포함)
            all_dup_joints = [dup_root] + dup_joints if dup_root and dup_root not in dup_joints else dup_joints
            orig_map = {short_path(j): j for j in orig_ns_joints}
            dup_map = {short_path(j): j for j in all_dup_joints}
            match_count = 0
            for joint in target_joints:
                # dup 조인트의 네임스페이스를 orig:로 치환
                if joint.startswith("dup:"):
                    orig_joint_name = "orig:" + joint[len("dup:"):]
                else:
                    orig_joint_name = joint.replace("dup:", "orig:")
                orig_joint = orig_joint_name if orig_joint_name in orig_ns_joints else None
                if not orig_joint:
                    self.logmsg(f"[SKIP] {joint} → orig 네임스페이스 조인트 매핑 없음 (예상:{orig_joint_name})")
                    continue
                orig_parent = cmds.listRelatives(orig_joint, p=True, type='joint')
                if not orig_parent:
                    self.logmsg(f"[SKIP] {joint} → orig 부모 없음")
                    continue
                parent_name = orig_parent[0]
                # dup 부모 이름도 네임스페이스 치환
                if parent_name.startswith("orig:"):
                    dup_parent_name = "dup:" + parent_name[len("orig:"):]
                else:
                    dup_parent_name = parent_name.replace("orig:", "dup:")
                dup_parent = dup_map.get(short_path(dup_parent_name))
                if not dup_parent:
                    self.logmsg(f"[SKIP] {joint} → dup 부모 매핑 없음 (parent_name:{dup_parent_name})")
                    continue
                try:
                    cmds.matchTransform(joint, dup_parent, rot=True)
                    self.logmsg(f"[MATCH] {joint} → {dup_parent} : matchTransform(rot=True) 성공")
                    match_count += 1
                except Exception as e:
                    self.logmsg(f"[FAIL] {joint} → {dup_parent} : matchTransform(rot=True) 실패: {e}")
            self.logmsg(f"[INFO] 패턴 적용 대상 {len(target_joints)}개 중 {match_count}개 조인트에 상위 rotate match 시도 완료 (matchTransform, 네임스페이스 치환)")
        except Exception as e:
            self.logmsg(f"[ERROR] 패턴 적용 중 오류: {e}")
        def get_all_descendants(joint, all_joints):
            """joint의 모든 하위 dup 조인트를 리스트로 반환"""
            descendants = []
            children = cmds.listRelatives(joint, c=True, type='joint') or []
            for child in children:
                if child in all_joints:
                    descendants.append(child)
                    descendants.extend(get_all_descendants(child, all_joints))
            return descendants

        child_rotate_follow_patterns = patterns.get("child_rotate_follow_patterns", [])
        target_joints_1 = [j for j in dup_joints if any(pat in j for pat in rotate_match_patterns) and j not in aim_joints]
        target_joints_3 = [j for j in dup_joints if any(pat in j for pat in child_rotate_follow_patterns) and j not in aim_joints]
        all_targets = set(target_joints_1 + target_joints_3)
        match_count = 0

        for joint in all_targets:
            # dup 조인트의 네임스페이스를 orig:로 치환
            if joint.startswith("dup:"):
                orig_joint_name = "orig:" + joint[len("dup:"):]
            else:
                orig_joint_name = joint.replace("dup:", "orig:")
            orig_joint = orig_joint_name if orig_joint_name in orig_ns_joints else None
            if not orig_joint:
                self.logmsg(f"[SKIP] {joint} → orig 네임스페이스 조인트 매핑 없음 (예상:{orig_joint_name})")
                continue
            orig_parent = cmds.listRelatives(orig_joint, p=True, type='joint')
            if not orig_parent:
                self.logmsg(f"[SKIP] {joint} → orig 부모 없음")
                continue
            parent_name = orig_parent[0]
            # dup 부모 이름도 네임스페이스 치환
            if parent_name.startswith("orig:"):
                dup_parent_name = "dup:" + parent_name[len("orig:"):]
            else:
                dup_parent_name = parent_name.replace("orig:", "dup:")
            dup_parent = dup_map.get(short_path(dup_parent_name))
            if not dup_parent:
                self.logmsg(f"[SKIP] {joint} → dup 부모 매핑 없음 (parent_name:{dup_parent_name})")
                continue
            # 하위 조인트 포함 orientConstraint + matchTransform
            descendants = get_all_descendants(joint, dup_joints)
            to_constrain = [joint] + descendants
            constraints = []
            for c_joint in to_constrain:
                try:
                    con = cmds.orientConstraint(dup_parent, c_joint, mo=True)[0]
                    constraints.append(con)
                    self.logmsg(f"[ORIENT] {c_joint} → {dup_parent} : orientConstraint(mo=1) 적용")
                except Exception as e:
                    self.logmsg(f"[FAIL] {c_joint} → {dup_parent} : orientConstraint 실패: {e}")
            # 부모 matchTransform
            try:
                cmds.matchTransform(joint, dup_parent, rot=True)
                self.logmsg(f"[MATCH] {joint} → {dup_parent} : matchTransform(rot=True) 성공")
                match_count += 1
            except Exception as e:
                self.logmsg(f"[FAIL] {joint} → {dup_parent} : matchTransform(rot=True) 실패: {e}")
            # constraint 해제
            for con in constraints:
                try:
                    cmds.delete(con)
                    self.logmsg(f"[CLEAN] {con} 삭제 완료")
                except Exception as e:
                    self.logmsg(f"[FAIL] {con} 삭제 실패: {e}")
        self.logmsg(f"[INFO] 2/3번 패턴 적용 대상 {len(all_targets)}개 중 {match_count}개 조인트에 상위 rotate match 시도 완료 (orientConstraint+matchTransform)")
        # === PV 로케이터 삭제 옵션 확인 (모든 Aim 작업 완료 후 실행) ===
        delete_pv_option = cmds.checkBox(self.chk_delete_pv, q=True, v=True)
        if delete_pv_option:
            deleted_loc = self.delete_pv_locators()
            deleted_guides = self.delete_pv_guides()
            if deleted_loc > 0 or deleted_guides > 0:
                self.logmsg(f"[INFO] Aim 실행 후 {deleted_loc}개 PV 로케이터, {deleted_guides}개 PV 가이드 정리 완료")
        else:
            self.logmsg("[INFO] PV 가이드/로케이터 삭제 옵션이 꺼져 있어 모두 유지됩니다.")

    def restore_hierarchy_and_cleanup(self, *_):
        dup_state = global_state.get('duplicator_state', {})
        dup_root = dup_state.get('dup_root', '')

        # dup 네임스페이스 기준 복제 트리 전체 탐색
        if not dup_root or not cmds.objExists(dup_root):
            self.logmsg("[ERROR] 복제 트리 루트가 존재하지 않습니다.")
            return

        # 'dup' 네임스페이스 전체 조인트 수집 (루트 포함)
        dup_namespace = "dup"  # 하드코딩
        dup_joints = cmds.ls(f"{dup_namespace}:*", type="joint")
        if not dup_joints:
            self.logmsg("[ERROR] dup 네임스페이스 복제 조인트가 없습니다."); 
            return

        # 루트 조인트도 포함하여 모든 dup 조인트 수집
        all_dup_joints = [dup_root] + dup_joints if dup_root not in dup_joints else dup_joints

        # 1. 모든 dup 조인트 world로 언패런트 (루트 포함)
        safe_unparent_world(sorted(all_dup_joints, key=lambda x: x.count('|'))[::-1])

        # 2. 부모-자식 관계 재구축 ('orig' 네임스페이스 기준)
        orig_ns_root = dup_state.get('orig_root', '')
        orig_ns_joints = []
        if orig_ns_root and cmds.objExists(f"orig:{orig_ns_root}"):
            orig_ns_joints = cmds.ls("orig:*", type="joint")  # 'orig' 하드코딩

        # short_path: {short_name: full_name} 형태 생성
        orig_map = {short_path(j): j for j in orig_ns_joints}
        dup_map = {short_path(j): j for j in all_dup_joints}

        restored = 0
        for k in orig_map.keys():
            orig_parent = cmds.listRelatives(orig_map[k], p=True, type='joint')
            dup_joint = dup_map.get(k.split('|')[-1])
            parent_joint = None
            if orig_parent:
                parent_short = short_path(orig_parent[0]).split('|')[-1]
                parent_joint = dup_map.get(parent_short)
            if dup_joint and parent_joint:
                try:
                    cmds.parent(dup_joint, parent_joint)
                    restored += 1
                except Exception as e:
                    self.logmsg(f"[WARN] {dup_joint} parent to {parent_joint} 실패: {e}")

        self.logmsg(f"[OK] 복제본 하이라키 복원 완료 ({restored}/{len(dup_map)})")
        
        # ────────────────────────────────────────────────
        # orig 네임스페이스 정리 --> 노드는 남기고 네임스페이스만 제거
        # ────────────────────────────────────────────────
        try:
            if cmds.namespace(exists='orig'):
                # 중첩 네임스페이스도 강제 병합하여 루트로 이동
                cmds.namespace(removeNamespace='orig',
                               mergeNamespaceWithRoot=True,
                               force=True)
                self.logmsg("[OK] 'orig' 네임스페이스만 깨끗하게 제거 완료")
            else:
                self.logmsg("[INFO] 'orig' 네임스페이스가 이미 존재하지 않습니다.")
        except Exception as e:
            self.logmsg(f"[WARN] 'orig' 네임스페이스 제거 실패: {e}")

    def delete_pv_locators(self):
        """PV 로케이터들을 찾아서 삭제 (개선된 버전)"""
        try:
            # 방법 1: List Comprehension 사용 (가장 안정적)
            all_transforms = cmds.ls(type="transform") or []
            pv_locs = [obj for obj in all_transforms if obj.endswith("_pv_loc")]
            
            # 네임스페이스가 있는 경우 추가 체크
            if not pv_locs:
                pv_locs = [obj for obj in all_transforms 
                           if obj.split(":")[-1].endswith("_pv_loc")]
            
            if not pv_locs:
                self.logmsg("[INFO] 삭제할 PV 로케이터가 없습니다.")
                return 0
                
            # 실제로 로케이터인지 확인 (안전장치)
            actual_pv_locs = []
            for loc in pv_locs:
                shapes = cmds.listRelatives(loc, shapes=True, type='locator')
                if shapes:
                    actual_pv_locs.append(loc)
            
            if actual_pv_locs:
                cmds.delete(actual_pv_locs)
                self.logmsg(f"[CLEANUP] {len(actual_pv_locs)}개의 PV 로케이터 삭제 완료")
                return len(actual_pv_locs)
            else:
                self.logmsg("[INFO] 삭제할 PV 로케이터가 없습니다.")
                return 0
                
        except Exception as e:
            self.logmsg(f"[ERROR] PV 로케이터 삭제 실패: {e}")
            return 0

    def _parse_vec(self, field, default="0,1,0"):
        """벡터 파싱"""
        txt = cmds.textFieldGrp(field, q=True, text=True)
        try:
            return [float(x) for x in txt.replace(",", " ").split()]
        except:
            return [float(x) for x in default.replace(",", " ").split()]

    def _get_enabled_axes(self):
        """활성화된 축 반환"""
        return [i for i, chk in enumerate([self.chk_x, self.chk_y, self.chk_z]) 
                if cmds.checkBox(chk, q=True, v=True)]
    def save_pv_list(self, *_):
        pv_sets = global_state['pv_sets']
        if not pv_sets:
            self.logmsg("[ERROR] 저장할 PV 세트가 없습니다."); return
        path = cmds.fileDialog2(fm=0, cap="PV 세트 저장", ff="*.json")
        if not path: return
        try:
            with open(path[0], "w", encoding="utf-8") as f:
                json.dump(pv_sets, f, ensure_ascii=False, indent=2)
            self.logmsg(f"[SAVE] PV 세트 저장 완료: {path[0]}")
        except Exception as e:
            self.logmsg(f"[ERROR] 저장 실패: {e}")
    def load_pv_list(self, *_):
        path = cmds.fileDialog2(fm=1, cap="PV 세트 불러오기", ff="*.json")
        if not path: return
        try:
            with open(path[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            global_state['pv_sets'] = [list(x) for x in data if isinstance(x, list) and len(x) == 3]
            self.refresh_pv_list()
            self.logmsg(f"[LOAD] PV 세트 불러오기 완료: {len(global_state['pv_sets'])}개")
        except Exception as e:
            self.logmsg(f"[ERROR] 불러오기 실패: {e}")
    def save_aim_list(self, *_):
        aim_sets = global_state['aim_sets']
        if not aim_sets:
            self.logmsg("[ERROR] 저장할 Aim 세트가 없습니다."); return
        path = cmds.fileDialog2(fm=0, cap="Aim체인 저장", ff="*.json")
        if not path: return
        try:
            with open(path[0], "w", encoding="utf-8") as f:
                json.dump(aim_sets, f, ensure_ascii=False, indent=2)
            self.logmsg(f"[SAVE] Aim 세트 저장 완료: {path[0]}")
        except Exception as e:
            self.logmsg(f"[ERROR] 저장 실패: {e}")
    def load_aim_list(self, *_):
        path = cmds.fileDialog2(fm=1, cap="Aim체인 불러오기", ff="*.json")
        if not path: return
        try:
            with open(path[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            global_state['aim_sets'] = [dict(x) for x in data if isinstance(x, dict) and 'startJoint' in x]
            self.refresh_aim_list()
            self.logmsg(f"[LOAD] Aim 세트 불러오기 완료: {len(global_state['aim_sets'])}개")
        except Exception as e:
            self.logmsg(f"[ERROR] 불러오기 실패: {e}")
    def auto_load_pv_sets(self):
        """설정된 경로에서 PV 세트 자동 불러오기"""
        auto_path = global_state['settings'].get('auto_load_pv_path', '')
        if not auto_path or not os.path.exists(auto_path):
            return False
        
        try:
            with open(auto_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded_sets = [list(x) for x in data if isinstance(x, list) and len(x) == 3]
            if loaded_sets:
                global_state['pv_sets'] = loaded_sets
                self.refresh_pv_list()
                self.logmsg(f"[AUTO-LOAD] PV 세트 자동 불러오기 완료: {len(loaded_sets)}개")
                return True
        except Exception as e:
            self.logmsg(f"[ERROR] PV 자동 불러오기 실패: {e}")
        
        return False

    def auto_load_aim_sets(self):
        """설정된 경로에서 Aim 세트 자동 불러오기"""
        auto_path = global_state['settings'].get('auto_load_aim_path', '')
        if not auto_path or not os.path.exists(auto_path):
            return False
        
        try:
            with open(auto_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded_sets = [dict(x) for x in data if isinstance(x, dict) and 'startJoint' in x]
            if loaded_sets:
                global_state['aim_sets'] = loaded_sets
                self.refresh_aim_list()
                self.logmsg(f"[AUTO-LOAD] Aim 세트 자동 불러오기 완료: {len(loaded_sets)}개")
                return True
        except Exception as e:
            self.logmsg(f"[ERROR] Aim 자동 불러오기 실패: {e}")
        
        return False
    def browse_pv_auto_path(self, *_):
        """PV 자동 불러오기 경로 찾기"""
        path = cmds.fileDialog2(fm=1, cap="PV 자동 불러오기 파일 선택", ff="*.json")
        if path:
            cmds.textField(self.pv_auto_path_tf, e=True, tx=path[0])
            self.logmsg(f"[INFO] PV 자동 경로 설정: {path[0]}")

    def browse_aim_auto_path(self, *_):
        """Aim 자동 불러오기 경로 찾기"""
        path = cmds.fileDialog2(fm=1, cap="Aim 자동 불러오기 파일 선택", ff="*.json")
        if path:
            cmds.textField(self.aim_auto_path_tf, e=True, tx=path[0])
            self.logmsg(f"[INFO] Aim 자동 경로 설정: {path[0]}")

    def save_auto_load_settings(self, *_):
        """자동 불러오기 설정 저장"""
        pv_path = cmds.textField(self.pv_auto_path_tf, q=True, tx=True).strip()
        aim_path = cmds.textField(self.aim_auto_path_tf, q=True, tx=True).strip()
        
        global_state['settings']['auto_load_pv_path'] = pv_path
        global_state['settings']['auto_load_aim_path'] = aim_path
        
        if save_settings():
            self.logmsg("[SAVE] 자동 불러오기 설정 저장 완료")
        else:
            self.logmsg("[ERROR] 자동 불러오기 설정 저장 실패")
    
    def exec_transfer_skin_weights(self, *_):
        """UI에서 소스/타겟/네임스페이스조인트 선택 → 스킨 전송 실행"""
        src = global_state['source_mesh']
        tgt = global_state['target_mesh']
        dup_joint = global_state['duplicator_state']['dup_root']
        try:
            transfer_skin_weights_auto_namespace(src, tgt, dup_joint)
            self.logmsg("[OK] 스킨웨이트 자동 복사 완료")
        except Exception as e:
            self.logmsg(f"[ERROR] 스킨웨이트 복사 실패: {e}")
    
    def mirror_all_pv_locators(self, axis='x', *_):
        pv_sets = global_state.get('pv_sets', [])
        if not pv_sets:
            self.logmsg('[INFO] [미러] 등록된 PV 세트가 없습니다.')
            return

        dir_val = cmds.optionMenuGrp(self.pv_mirror_dir, q=True, v=True)
        direction = 'l2r' if "L" in dir_val and "R" in dir_val and dir_val[0].upper() == 'L' else 'r2l'
        mirror_count = 0

        for _, mid, _ in pv_sets:
            mid = mid.strip()
            if direction == 'l2r':
                # '_l' 또는 'left' (대소문자 포함)이 실제 mid 이름에 포함된 경우만 미러
                if any(s in mid.lower() for s in ['_l', 'left']):
                    left_loc  = f"{mid}_pv_loc"
                    right_loc = find_side_pair_name(left_loc, direction='l2r')
                    # 실제 mid가 'l'계열이어야만 소스 → 타깃 미러
                    if cmds.objExists(left_loc) and right_loc and cmds.objExists(right_loc):
                        mirror_object_position_cmds(left_loc, right_loc, axis=axis)
                        self.logmsg(f"[MIRROR-L2R] {left_loc} → {right_loc} ({axis}축)")
                        mirror_count += 1
            elif direction == 'r2l':
                if any(s in mid.lower() for s in ['_r', 'right']):
                    right_loc = f"{mid}_pv_loc"
                    left_loc = find_side_pair_name(right_loc, direction='r2l')
                    # 실제 mid가 'r'계열이어야만 소스 → 타깃 미러
                    if cmds.objExists(right_loc) and left_loc and cmds.objExists(left_loc):
                        mirror_object_position_cmds(right_loc, left_loc, axis=axis)
                        self.logmsg(f"[MIRROR-R2L] {right_loc} → {left_loc} ({axis}축)")
                        mirror_count += 1
        if mirror_count == 0:
            self.logmsg(f'[INFO] [미러] 실행 가능한 {direction.upper()} PV locator 쌍이 없습니다.')
        else:
            self.logmsg(f"[DONE] {mirror_count}개 PV locator 미러 완료")

# ===== 실행 =====
def launch_integrated_joint_tools():
    """통합 조인트 툴 실행"""
    global tool_manager
    tool_manager = IntegratedJointToolsManager()

# 툴 실행
launch_integrated_joint_tools()