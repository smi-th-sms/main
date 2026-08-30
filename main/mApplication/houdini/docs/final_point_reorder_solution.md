# Houdini Point Reordering - Final Solution (Sort SOP)

## 최종 해결 방법

**Attribute Wrangle + Sort SOP (Reverse Point Sort)**

이 방법이 가장 간단하고 효율적입니다.

## 노드 구성

```
[Input 0: Target Line] ─┐
                         ├─> [Attrib Wrangle] -> [Sort SOP] -> [Output]
[Input 1: Base Line] ────┘
```

## Step 1: Attribute Wrangle (Detail mode)

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Determine if Reverse is Needed and Create Group
// ====================================================================

int num_pts = npoints(0);

if (num_pts < 2) {
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

printf("[Point Reorder Check]\n");
printf("  First point dist: %.4f\n", min_dist_first);
printf("  Last point dist: %.4f\n", min_dist_last);
printf("  Need reverse: %s\n", need_reverse ? "YES" : "NO");

// Reverse가 필요하면 모든 포인트를 그룹에 추가
if (need_reverse) {
    for (int i = 0; i < num_pts; i++) {
        setpointgroup(0, "need_reverse", i, 1, "set");
    }
    printf("  -> Created 'need_reverse' group (%d points)\n", num_pts);
} else {
    printf("  -> No reverse needed\n");
}
```

## Step 2: Sort SOP

**설정:**
1. Sort SOP 생성
2. **Point Sort** 탭:
   - **Reverse Point Sort** 체크
   - **Point Group** 입력: `need_reverse`
3. (선택) **Point Sort** → **By X/Y/Z** 등 체크하여 추가 정렬 가능

## 작동 원리

- **그룹이 있으면** (`need_reverse`가 생성됨):
  - Sort SOP가 해당 그룹의 포인트 순서를 반전
  - Point 0 ↔ Point N-1 교체
  
- **그룹이 없으면**:
  - Sort SOP가 아무것도 안함 (원본 유지)

## 장점

✅ **포인트 번호 실제 재할당** - Sort SOP는 포인트 번호를 물리적으로 변경  
✅ **한 노드로 해결** - Reverse + Sort를 동시에 처리  
✅ **ForEach 완벽 호환** - 각 iteration마다 조건부 실행  
✅ **추가 정렬 가능** - X/Y/Z 기준 정렬, Random 등 추가 옵션  
✅ **Expression 불필요** - 그룹만으로 조건 처리  

## ForEach에서 사용

```
ForEach Loop (각 Target Line마다)
  └─> [Attrib Wrangle] (need_reverse 그룹 생성 여부 판단)
      └─> [Sort SOP] (Reverse Point Sort on need_reverse group)
      └─> [다음 작업들...]
```

- Line A: 마지막 점이 Base에 가까움 → 그룹 생성 → 포인트 반전
- Line B: 첫 점이 이미 Base에 가까움 → 그룹 없음 → 원본 유지
- Line C: 마지막 점이 Base에 가까움 → 그룹 생성 → 포인트 반전

## 검증

Geometry Spreadsheet로 확인:
1. **Points** 탭 열기
2. **Group** 컬럼에서 `need_reverse` 확인
3. Point 0의 위치가 Base Line에 가장 가까운지 확인
4. Point 번호가 0, 1, 2, 3... 순서대로 정렬되었는지 확인

## 다른 Sort 옵션 (필요시)

- **By Point Number**: 포인트 번호 기준 정렬 (기본값)
- **By Proximity to Point**: 특정 포인트로부터 거리순
- **By Attribute**: Attribute 값 기준 정렬
- **Random**: 랜덤 섞기
- **Shift**: 포인트 번호를 N만큼 shift

## 최종 결과

**Before:**
- Point 0: (10, 20, 5) - Base Line까지 거리: 15.5
- Point 4: (2, 3, 1) - Base Line까지 거리: 2.3

**After:**
- Point 0: (2, 3, 1) - Base Line까지 거리: 2.3 ✓
- Point 4: (10, 20, 5) - Base Line까지 거리: 15.5

포인트가 실제로 재번호화되어 Point 0이 Base Line에 가장 가깝게 됩니다!




