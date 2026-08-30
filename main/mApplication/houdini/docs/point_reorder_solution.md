# Houdini Point Reordering Solution

## 목표
Target Line의 포인트를 재정렬하여 Base Line과 가장 가까운 endpoint가 Point 0이 되도록 함

## 방법: Attribute Wrangle + Reverse SOP

### 노드 구성
```
[Input 0: Target Line] ─┐
                         ├─> [Attrib Wrangle] -> [Reverse SOP] -> [Output]
[Input 1: Base Line] ────┘
```

### Step 1: Attribute Wrangle (attribwrangle11)

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Determine if Reverse is Needed
// ====================================================================

int num_pts = npoints(0);

if (num_pts < 2) {
    i@need_reverse = 0;
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
if (min_dist_last < min_dist_first) {
    i@need_reverse = 1;  // 마지막 포인트가 Base Line에 더 가까움
    printf("REVERSE NEEDED - Last point (%.4f) is closer than first (%.4f)\n", 
           min_dist_last, min_dist_first);
} else {
    i@need_reverse = 0;  // Point 0이 이미 Base Line에 가까움
    printf("NO REVERSE - First point (%.4f) is already closer\n", min_dist_first);
}
```

### Step 2: Reverse SOP

**설정:**
1. Reverse SOP 노드 생성
2. **Reverse U** 체크
3. **Enable** 파라미터에 다음 expression 입력:
   ```
   detail("../attribwrangle11", "need_reverse", 0)
   ```
   (attribwrangle11을 실제 노드 이름으로 변경)

이렇게 하면 `need_reverse`가 1일 때만 Reverse가 실행됩니다.

### Step 3: Sort SOP (선택사항)

포인트 번호를 실제로 재정렬하려면:
1. Sort SOP 추가
2. **Sort by**: Point Number
3. 이렇게 하면 포인트가 순서대로 0, 1, 2... 재할당됩니다.

## 장점
- ✅ 포인트를 삭제/재생성하지 않음
- ✅ 노드 기반 접근으로 시각적으로 관리 가능
- ✅ 조건부 실행으로 불필요한 연산 방지
- ✅ 디버깅 용이

## 참고
- Reverse SOP는 primitive의 vertex 순서를 반전시킵니다
- Sort SOP는 포인트 번호를 재할당합니다
- Detail attribute는 geometry 전체에 하나의 값을 저장합니다




