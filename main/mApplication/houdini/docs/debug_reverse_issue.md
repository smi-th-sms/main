# Debug Reverse Issue

## 현재 상황

```
Point 0: (-0.148, 1.642, 0.027) -> Base Line 거리: 0.1453 (더 가까움)
Point 1: (-0.123, 1.616, 0.033) -> Base Line 거리: 0.1637 (더 멀음)

결과: Reverse 안함 (Point 0이 이미 더 가까우므로)
```

## 문제 원인 가능성

### 1. Input 연결 확인

**Attribwrangle18의 Input 연결이 올바른지 확인:**
- Input 0: Target Line (정렬할 라인)
- Input 1: Base Line (기준 라인)

**확인 방법:**
Input 노드를 잘못 연결했을 가능성이 있습니다.

### 2. Root 그룹 기반 판단으로 변경

현재는 **"Base Line에 가장 가까운 endpoint"**를 기준으로 하고 있습니다.
하지만 **"root 그룹이 이미 지정되어 있다면"** 그것을 우선해야 할 수도 있습니다.

**수정된 VEX (Root 그룹 우선):**

```c
// ====================================================================
// Reverse Check with Root Group Priority
// ====================================================================

int num_pts = npoints(0);
int num_prims = nprimitives(0);

printf("\n========================================\n");
printf("Reverse Check (attribwrangle18)\n");
printf("========================================\n");

if (num_pts < 2 || num_prims < 1) {
    printf("[ERROR] Invalid geometry: pts=%d, prims=%d\n", num_pts, num_prims);
    printf("========================================\n\n");
    return;
}

printf("[Geometry Info]\n");
printf("  Total points: %d\n", num_pts);
printf("  Total prims: %d\n", num_prims);

// === 1. Root 그룹이 이미 있는지 확인 ===
int root_pt = -1;
int has_root_group = 0;

for (int i = 0; i < num_pts; i++) {
    if (inpointgroup(0, "root", i)) {
        root_pt = i;
        has_root_group = 1;
        printf("\n[Root Group Found]\n");
        printf("  Root point: %d\n", root_pt);
        break;
    }
}

// 양쪽 끝점 찾기
int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

printf("\n[Endpoint Positions]\n");
printf("  Point 0 (first): (%.3f, %.3f, %.3f)\n", first_pos.x, first_pos.y, first_pos.z);
printf("  Point %d (last): (%.3f, %.3f, %.3f)\n", last_pt, last_pos.x, last_pos.y, last_pos.z);

// Base Line과의 최소 거리 계산
float min_dist_first = 999999;
float min_dist_last = 999999;

for (int i = 0; i < npoints(1); i++) {
    vector base_pos = point(1, "P", i);
    min_dist_first = min(min_dist_first, distance(first_pos, base_pos));
    min_dist_last = min(min_dist_last, distance(last_pos, base_pos));
}

printf("\n[Distance to Base Line]\n");
printf("  Point 0 distance: %.4f\n", min_dist_first);
printf("  Point %d distance: %.4f\n", last_pt, min_dist_last);
printf("  Difference: %.4f\n", abs(min_dist_first - min_dist_last));

// === 2. Reverse 필요 여부 판단 ===
int need_reverse = 0;

if (has_root_group) {
    // Root 그룹이 있으면 root가 Point 0이 아닌 경우 reverse
    if (root_pt != 0) {
        need_reverse = 1;
        printf("\n[Decision - Root Group Priority]\n");
        printf("  Root point %d is NOT Point 0\n", root_pt);
        printf("  Need reverse: YES (to make root Point 0)\n");
    } else {
        printf("\n[Decision - Root Group Priority]\n");
        printf("  Root point is already Point 0\n");
        printf("  Need reverse: NO\n");
    }
} else {
    // Root 그룹이 없으면 Base Line 거리 기준
    need_reverse = (min_dist_last < min_dist_first) ? 1 : 0;
    printf("\n[Decision - Distance Based]\n");
    printf("  No root group found, using distance\n");
    printf("  Need reverse: %s\n", need_reverse ? "YES" : "NO");
}

// === 3. 그룹 생성 ===
if (need_reverse) {
    printf("  Action: Creating 'need_reverse' groups\n");
    
    // 포인트 그룹
    for (int i = 0; i < num_pts; i++) {
        setpointgroup(0, "need_reverse", i, 1, "set");
    }
    printf("    -> Point group created: %d points\n", num_pts);
    
    // 프리미티브 그룹
    for (int i = 0; i < num_prims; i++) {
        setprimgroup(0, "need_reverse", i, 1, "set");
    }
    printf("    -> Prim group created: %d prims\n", num_prims);
    printf("  Result: Groups created, Sort SOP will reverse\n");
} else {
    printf("  Action: No groups created\n");
    if (has_root_group) {
        printf("  Reason: Root is already Point 0\n");
    } else {
        printf("  Reason: Point 0 (%.4f) is already closer than Point %d (%.4f)\n", 
               min_dist_first, last_pt, min_dist_last);
    }
    printf("  Result: Point order is correct, no reverse needed\n");
}

printf("\n========================================\n\n");
```

### 3. Input 검증 코드 추가

Input이 올바른지 확인하는 코드:

```c
// Input 검증
printf("\n[Input Verification]\n");
printf("  Input 0 (Target Line) points: %d\n", npoints(0));
printf("  Input 1 (Base Line) points: %d\n", npoints(1));

if (npoints(1) == 0) {
    printf("  [ERROR] Input 1 (Base Line) is empty!\n");
    printf("  -> Check node connections\n");
    return;
}

// Base Line 중심 위치
vector base_center = {0, 0, 0};
for (int i = 0; i < npoints(1); i++) {
    base_center += point(1, "P", i);
}
base_center /= npoints(1);
printf("  Base Line center: (%.3f, %.3f, %.3f)\n", 
       base_center.x, base_center.y, base_center.z);

// Target Line 중심 위치
vector target_center = (first_pos + last_pos) / 2.0;
printf("  Target Line center: (%.3f, %.3f, %.3f)\n", 
       target_center.x, target_center.y, target_center.z);

float center_dist = distance(base_center, target_center);
printf("  Distance between centers: %.4f\n", center_dist);
```

## 체크리스트

1. ☐ Attribwrangle18의 Input 0이 정렬할 Target Line인가?
2. ☐ Attribwrangle18의 Input 1이 기준 Base Line인가?
3. ☐ Root 그룹이 이미 존재하는가?
4. ☐ Root 그룹이 있다면 어느 포인트인가?
5. ☐ 실제로 어느 포인트가 시작점이 되어야 하는가?

## 디버깅 질문

**이 경우에 실제로 어느 포인트가 시작점이 되어야 하나요?**
- Point 0 (-0.148, 1.642, 0.027)이 맞나요?
- Point 1 (-0.123, 1.616, 0.033)이 맞나요?

**혹시 "root" 그룹이 이미 지정되어 있나요?**
- 있다면 어느 포인트인가요?
- 그게 우선되어야 하나요?




