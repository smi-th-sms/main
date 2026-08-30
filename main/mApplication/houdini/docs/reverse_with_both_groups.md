# Point Reordering with Both Point and Primitive Groups

## Attribute Wrangle - 포인트 + 프리미티브 그룹 생성

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Determine if Reverse is Needed - Create Both Groups
// ====================================================================

int num_pts = npoints(0);
int num_prims = nprimitives(0);

if (num_pts < 2 || num_prims < 1) {
    return;
}

// 양쪽 끝점 찾기
int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

// Base Line과의 최소 거리 계산
float min_dist_first = 999999;
float min_dist_last = 999999;

for (int i = 0; i < npoints(1); i++) {
    vector base_pos = point(1, "P", i);
    min_dist_first = min(min_dist_first, distance(first_pos, base_pos));
    min_dist_last = min(min_dist_last, distance(last_pos, base_pos));
}

// Reverse 필요 여부 판단
int need_reverse = (min_dist_last < min_dist_first) ? 1 : 0;

printf("[Reverse Check]\n");
printf("  First pt dist: %.4f\n", min_dist_first);
printf("  Last pt dist: %.4f\n", min_dist_last);
printf("  Need reverse: %s\n", need_reverse ? "YES" : "NO");

// Reverse가 필요하면 포인트 그룹과 프리미티브 그룹 모두 생성
if (need_reverse) {
    // 포인트 그룹 생성
    for (int i = 0; i < num_pts; i++) {
        setpointgroup(0, "need_reverse", i, 1, "set");
    }
    printf("  -> Created 'need_reverse' point group (%d points)\n", num_pts);
    
    // 프리미티브 그룹 생성
    for (int i = 0; i < num_prims; i++) {
        setprimgroup(0, "need_reverse", i, 1, "set");
    }
    printf("  -> Created 'need_reverse' prim group (%d prims)\n", num_prims);
} else {
    printf("  -> No reverse needed (no groups created)\n");
}
```

## Sort SOP 설정

**Point Sort** 탭:
- **Reverse Point Sort** ✓ 체크
- **Point Group**: `need_reverse` (포인트 그룹 사용)
- 또는 **Primitive Group**: `need_reverse` (프리미티브 그룹 사용)

둘 중 하나를 선택하거나, 둘 다 설정 가능합니다.

## 두 그룹을 모두 생성하는 이유

1. **Point Group**:
   - 포인트 단위 작업에 사용
   - Blast SOP, Attribute Wrangle 등에서 포인트 필터링
   - `@group_need_reverse` 같은 조건문에서 사용

2. **Primitive Group**:
   - 프리미티브 단위 작업에 사용
   - Sort SOP, Subdivide 등에서 프리미티브 필터링
   - ForEach 등에서 프리미티브 단위로 처리

## 검증

**Geometry Spreadsheet:**

1. **Points** 탭:
   - **Group** 컬럼에서 `need_reverse` 확인
   - Reverse 필요한 경우 모든 포인트에 그룹 표시

2. **Primitives** 탭:
   - **Group** 컬럼에서 `need_reverse` 확인
   - Reverse 필요한 경우 모든 프리미티브에 그룹 표시

## 활용 예시

**Point Group 사용:**
```c
// Attribute Wrangle (Run Over: Points)
if (@group_need_reverse) {
    // Reverse가 필요한 라인의 포인트들에만 적용
    // ...
}
```

**Primitive Group 사용:**
```c
// Attribute Wrangle (Run Over: Primitives)
if (@group_need_reverse) {
    // Reverse가 필요한 라인의 프리미티브들에만 적용
    // ...
}
```

**Sort SOP:**
- Primitive Group 또는 Point Group 선택 가능
- 두 그룹이 같은 이름이므로 유연하게 사용 가능




