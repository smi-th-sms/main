# Houdini Point Reordering - Group-Based Reverse Method

## 노드 구성 (가장 간단한 방법)

```
[Input 0: Target Line] ─┐
                         ├─> [Attrib Wrangle] -> [Reverse SOP] -> [Output]
[Input 1: Base Line] ────┘
```

## 작동 원리

1. Attribute Wrangle에서 reverse 필요 여부 판단
2. 필요하면 **모든 포인트를 "need_reverse" 그룹에 추가**
3. 필요 없으면 그룹을 **비워둠**
4. Reverse SOP의 **Source Group**에 "need_reverse" 입력
5. 그룹이 비어있으면 → Reverse 실행 안됨
6. 그룹에 포인트가 있으면 → Reverse 실행

## Step 1: Attribute Wrangle

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Determine Reverse and Create Group
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

printf("[Reverse Check]\n");
printf("  First pt dist: %.4f\n", min_dist_first);
printf("  Last pt dist: %.4f\n", min_dist_last);
printf("  Need reverse: %s\n", need_reverse ? "YES" : "NO");

// Reverse가 필요하면 모든 포인트를 그룹에 추가
if (need_reverse) {
    for (int i = 0; i < num_pts; i++) {
        setpointgroup(0, "need_reverse", i, 1, "set");
    }
    printf("  -> Created 'need_reverse' group with %d points\n", num_pts);
} else {
    // 그룹을 비워둠 (또는 생성하지 않음)
    printf("  -> No group created (no reverse needed)\n");
}
```

## Step 2: Reverse SOP

**설정:**
1. Reverse SOP 생성
2. **Reverse U** 체크
3. **Source Group** 파라미터에 입력:
   ```
   need_reverse
   ```
4. **Enable은 항상 켜둠** (그룹이 비어있으면 자동으로 아무것도 안함)

## 장점

✅ **Switch SOP 불필요** - 노드 하나 절약  
✅ **Expression 불필요** - 단순히 그룹 이름만 입력  
✅ **ForEach와 완벽 호환** - 각 iteration마다 조건부 실행  
✅ **시각적 확인 용이** - Geometry Spreadsheet에서 그룹 확인 가능  
✅ **자동으로 skip** - 빈 그룹은 Reverse가 건너뜀  

## ForEach에서 사용 예시

```
ForEach Loop
  └─> [Attrib Wrangle] (각 line마다 need_reverse 그룹 생성/삭제)
      └─> [Reverse SOP] (Source Group: need_reverse)
      └─> ... 다음 작업들
```

각 iteration마다:
- Line A: reverse 필요 → 그룹 생성 → Reverse 실행
- Line B: reverse 불필요 → 그룹 없음 → Reverse skip
- Line C: reverse 필요 → 그룹 생성 → Reverse 실행

## 디버깅

Geometry Spreadsheet에서 확인:
1. **Points** 탭 열기
2. **Group** 컬럼에서 `need_reverse` 확인
3. 그룹이 있으면 포인트들이 표시됨
4. 그룹이 없으면 아무것도 표시 안됨

## 참고

- `setpointgroup(geo, "name", point, value, "set")` 
  - value = 1: 그룹에 추가
  - value = 0: 그룹에서 제거
- Reverse SOP는 Source Group이 비어있거나 없으면 전체 지오메트리를 건드리지 않음




