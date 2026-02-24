# Verify Point Order After Reverse

## 문제 상황

포인트가 2개인 경우, Sort SOP 이후에도 Point 0이 Base Line에 가장 가까운 점이 아닌 경우가 발생

## 디버깅: 검증용 Attribute Wrangle

Sort SOP **이후**에 추가하여 결과를 검증합니다.

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line (Sort 후)
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Verify Point Order After Reverse/Sort
// ====================================================================

int num_pts = npoints(0);

printf("\n========================================\n");
printf("VERIFICATION: Point Order Check\n");
printf("========================================\n");

if (num_pts < 2) {
    printf("[WARNING] Less than 2 points: %d\n", num_pts);
    return;
}

printf("\n[Current Point Order]\n");

// 모든 포인트와 Base Line까지의 거리 계산
for (int i = 0; i < num_pts; i++) {
    vector pos = point(0, "P", i);
    
    float min_dist = 999999;
    for (int j = 0; j < npoints(1); j++) {
        vector base_pos = point(1, "P", j);
        min_dist = min(min_dist, distance(pos, base_pos));
    }
    
    printf("  Point %d: (%.3f, %.3f, %.3f) -> Base dist: %.4f", 
           i, pos.x, pos.y, pos.z, min_dist);
    
    if (i == 0) {
        printf(" <- SHOULD BE CLOSEST");
    }
    printf("\n");
}

// 끝점들 체크
int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

float dist_first = 999999;
float dist_last = 999999;

for (int i = 0; i < npoints(1); i++) {
    vector base_pos = point(1, "P", i);
    dist_first = min(dist_first, distance(first_pos, base_pos));
    dist_last = min(dist_last, distance(last_pos, base_pos));
}

printf("\n[Endpoint Check]\n");
printf("  Point 0 (first): %.4f\n", dist_first);
printf("  Point %d (last): %.4f\n", last_pt, dist_last);

// 검증 결과
printf("\n[Result]\n");
if (dist_first < dist_last) {
    printf("  ✓ CORRECT - Point 0 is closest to Base\n");
} else if (dist_first > dist_last) {
    printf("  ✗ ERROR - Point %d is closer (%.4f < %.4f)\n", 
           last_pt, dist_last, dist_first);
    printf("  -> Reverse did NOT work properly!\n");
} else {
    printf("  = EQUAL - Both endpoints have same distance (%.4f)\n", dist_first);
}

// 포인트가 2개인 특수 케이스 체크
if (num_pts == 2) {
    printf("\n[Special Case: 2 Points]\n");
    printf("  Point 0 should be closest: %.4f\n", dist_first);
    printf("  Point 1 should be farthest: %.4f\n", dist_last);
    
    if (dist_first > dist_last) {
        printf("  ✗ FAILED - Need to reverse again!\n");
    }
}

// need_reverse 그룹 존재 여부 확인
int has_point_group = 0;
int has_prim_group = 0;

for (int i = 0; i < num_pts; i++) {
    if (inpointgroup(0, "need_reverse", i)) {
        has_point_group = 1;
        break;
    }
}

for (int i = 0; i < nprimitives(0); i++) {
    if (inprimgroup(0, "need_reverse", i)) {
        has_prim_group = 1;
        break;
    }
}

printf("\n[Group Check]\n");
printf("  Point group 'need_reverse': %s\n", has_point_group ? "EXISTS" : "NOT FOUND");
printf("  Prim group 'need_reverse': %s\n", has_prim_group ? "EXISTS" : "NOT FOUND");

printf("\n========================================\n\n");
```

## Sort SOP 설정 재확인

Sort SOP에서 다음 설정이 올바른지 확인:

### Point Sort 탭:
1. **Reverse Point Sort** ✓ 체크되어 있는지
2. **Point Group** 또는 **Primitive Group**: `need_reverse` 입력되어 있는지
3. **Point Sort** 아래의 **By** 옵션은 기본값 유지

### 주의사항:
- **Point Group**과 **Primitive Group** 중 하나만 사용
- 일반적으로 **Primitive Group** 사용 권장
- 두 필드에 동시에 입력하면 충돌 가능

## 대안: 강제 Reverse (조건부)

만약 Sort SOP가 작동하지 않는다면, Attribute Wrangle에서 직접 처리:

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line

**VEX Code:**
```c
// 강제 Reverse - 조건 확인 후 primitive 재구성
int num_pts = npoints(0);
if (num_pts < 2) return;

// Base Line과의 거리 확인
int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

float dist_first = 999999;
float dist_last = 999999;

for (int i = 0; i < npoints(1); i++) {
    vector base_pos = point(1, "P", i);
    dist_first = min(dist_first, distance(first_pos, base_pos));
    dist_last = min(dist_last, distance(last_pos, base_pos));
}

// Reverse 필요한 경우에만 실행
if (dist_last < dist_first) {
    printf("FORCE REVERSE: last (%.4f) < first (%.4f)\n", dist_last, dist_first);
    
    // 기존 primitive vertex 저장
    int old_vtxs[] = primvertices(0, 0);
    int old_pts[];
    resize(old_pts, len(old_vtxs));
    
    for (int i = 0; i < len(old_vtxs); i++) {
        old_pts[i] = vertexpoint(0, old_vtxs[i]);
    }
    
    // Primitive 삭제
    removeprim(0, 0, 0);
    
    // 역순으로 새 Primitive 생성
    int new_prim = addprim(0, "polyline");
    for (int i = len(old_pts) - 1; i >= 0; i--) {
        addvertex(0, new_prim, old_pts[i]);
    }
    
    printf("  -> Reversed %d vertices\n", len(old_pts));
}
```

## 디버깅 순서

1. **Reverse 판단 Wrangle** 실행 → Textport에서 로그 확인
2. **Sort SOP** 설정 확인 → Primitive Group: `need_reverse`
3. **검증 Wrangle** 실행 → Textport에서 결과 확인
4. 문제 발견 시 → Sort SOP 설정 재조정 또는 강제 Reverse 사용




