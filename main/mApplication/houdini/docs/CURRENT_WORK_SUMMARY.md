# Houdini Line Connection Work Summary

## 완료된 작업

### 1. attribwrangle18 - Reverse 판단 및 그룹 생성
**목적:** Target Line의 끝점 중 Base Line에 가장 가까운 점을 Point 0으로 만들기

**코드 (최종 버전):**
```c
int num_pts = npoints(0);
int num_prims = nprimitives(0);

if (num_pts < 2 || num_prims < 1) {
    return;
}

int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

// xyzdist로 Base Line primitive 상의 가장 가까운 지점까지 거리 계산
int prim_first, prim_last;
vector uv_first, uv_last;

vector closest_first = xyzdist(1, first_pos, prim_first, uv_first);
vector closest_last = xyzdist(1, last_pos, prim_last, uv_last);

float dist_first = distance(first_pos, closest_first);
float dist_last = distance(last_pos, closest_last);

int need_reverse = (dist_last < dist_first) ? 1 : 0;

if (need_reverse) {
    for (int i = 0; i < num_pts; i++) {
        setpointgroup(0, "need_reverse", i, 1, "set");
    }
    for (int i = 0; i < num_prims; i++) {
        setprimgroup(0, "need_reverse", i, 1, "set");
    }
}
```

**설정:**
- Run Over: Detail (only once)
- Input 0: Target Line
- Input 1: Base Line

### 2. sort1 (reverse3) - Point 순서 반전
**목적:** need_reverse 그룹이 있으면 포인트 순서 반전

**Sort SOP 설정:**
- Point Sort 탭
- Reverse Point Sort: ✓ 체크
- Primitive Group: `need_reverse`

### 3. 연결 Vertex 추가 (진행 중 - 문제 발생)
**목적:** Target Line Point 0 앞에 vertex 추가하고 Base Line 접점으로 이동

**노드 구성:**
```
Target Line -> attribwrangle18 -> sort1(reverse3) -> [새 Wrangle]
                     ↓                                     ↓
Base Line -----------┴─────────────────────────────────────┘
              (Input 1)
```

**시도한 코드:**
```c
int num_pts = npoints(0);
int num_prims = nprimitives(0);

if (num_pts < 1 || num_prims != 1 || npoints(1) == 0) {
    return;
}

vector root_pos = point(0, "P", 0);

int contact_prim;
vector contact_uv;
vector contact_pos = xyzdist(1, root_pos, contact_prim, contact_uv);

int new_pt = addpoint(0, root_pos);

int old_vtxs[] = primvertices(0, 0);
int old_pts[];
resize(old_pts, len(old_vtxs));

for (int i = 0; i < len(old_vtxs); i++) {
    old_pts[i] = vertexpoint(0, old_vtxs[i]);
}

removeprim(0, 0, 0);

int new_prim = addprim(0, "polyline");
addvertex(0, new_prim, new_pt);

for (int i = 0; i < len(old_pts); i++) {
    addvertex(0, new_prim, old_pts[i]);
}

setpointattrib(0, "P", new_pt, contact_pos);
```

**발생한 문제:**
- "새 vertex가 base line과의 접점에 없고 더 멀리 있어"
- 정확한 문제 상황 불명확

## 최종 목표

**원하는 결과:**
```
Base Line: ────●────●────●────
                ↓ (연결점)
          Connection Vertex
                ↓
        Target P0 ─ P1 ─ P2 ─ P3 (가지)
```

- Base Line을 trunk로
- Target Line들을 branch로
- 나중에 bone 생성 시 올바른 트리 구조 형성

## 새 대화에서 확인할 사항

1. **새 vertex의 실제 위치가 어디인지** (시각적으로 확인)
2. **원하는 위치는 정확히 어디인지**
3. **xyzdist 결과가 올바른지**
4. **혹시 다른 노드가 영향을 주는지**

## 참고 파일

- `houdini_integration/reverse_with_both_groups.md` - Reverse 그룹 생성 방법
- `houdini_integration/add_connection_vertex.md` - Vertex 추가 방법
- `houdini_integration/verify_point_order.md` - Point 순서 검증 방법




