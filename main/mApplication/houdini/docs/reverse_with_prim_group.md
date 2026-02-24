# Point Reordering with Primitive Group

## Attribute Wrangle - Primitive Group 버전

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Determine if Reverse is Needed - Create Primitive Group
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

// Reverse가 필요하면 모든 프리미티브를 그룹에 추가
if (need_reverse) {
    for (int i = 0; i < num_prims; i++) {
        setprimgroup(0, "need_reverse", i, 1, "set");
    }
    printf("  -> Created 'need_reverse' prim group (%d prims)\n", num_prims);
} else {
    printf("  -> No reverse needed\n");
}
```

## Sort SOP 설정

**Point Sort** 탭:
- **Reverse Point Sort** ✓ 체크
- **Primitive Group**: `need_reverse`

## 차이점

**Point Group 방식:**
- 포인트 단위로 그룹 생성
- 모든 포인트를 그룹에 추가해야 함
- `setpointgroup(0, "name", point_num, 1, "set")`

**Primitive Group 방식:**
- 프리미티브 단위로 그룹 생성
- 프리미티브만 그룹에 추가 (더 간단)
- `setprimgroup(0, "name", prim_num, 1, "set")`

## 장점

✅ **더 간단한 코드** - 포인트 루프 대신 프리미티브만 체크  
✅ **ForEach와 자연스러운 호환** - Primitive 단위로 처리  
✅ **메모리 효율** - 프리미티브 개수가 포인트 개수보다 적음  
✅ **Sort SOP 호환** - Primitive Group을 직접 지원  

## 검증

Geometry Spreadsheet에서:
1. **Primitives** 탭 열기
2. **Group** 컬럼에서 `need_reverse` 확인
3. 그룹이 있으면 해당 primitive가 표시됨




