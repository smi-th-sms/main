# Houdini Point Reordering - Switch SOP Method

## 노드 구성 (수정된 버전)

```
[Input 0: Target Line] ─┐
                         ├─> [Attrib Wrangle] ─┬─> [Switch SOP] -> [Output]
[Input 1: Base Line] ────┘                     │         ↑
                                               │         │
                                               └─[Reverse]┘
```

## Step 1: Attribute Wrangle (Detail mode)

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line
- Input 1: Base Line

**VEX Code:**
```c
// Determine if Reverse is Needed
int num_pts = npoints(0);

if (num_pts < 2) {
    i@need_reverse = 0;
    return;
}

int first_pt = 0;
int last_pt = num_pts - 1;

vector first_pos = point(0, "P", first_pt);
vector last_pos = point(0, "P", last_pt);

float min_dist_first = 999999;
float min_dist_last = 999999;

for (int i = 0; i < npoints(1); i++) {
    vector base_pos = point(1, "P", i);
    min_dist_first = min(min_dist_first, distance(first_pos, base_pos));
    min_dist_last = min(min_dist_last, distance(last_pos, base_pos));
}

if (min_dist_last < min_dist_first) {
    i@need_reverse = 1;
    printf("REVERSE NEEDED: last=%.4f < first=%.4f\n", min_dist_last, min_dist_first);
} else {
    i@need_reverse = 0;
    printf("NO REVERSE: first=%.4f <= last=%.4f\n", min_dist_first, min_dist_last);
}
```

## Step 2: Reverse SOP

**설정:**
- 위의 Attribute Wrangle에 연결
- **Reverse U** 체크
- **Enable은 항상 켜둠** (expression 불필요)

## Step 3: Switch SOP

**설정:**
1. Switch SOP 생성
2. **Input 0**: Attribute Wrangle 출력 (원본)
3. **Input 1**: Reverse SOP 출력 (반전된 버전)
4. **Select Input** 파라미터를 **Expression**으로 변경
5. Expression 입력:

**Hscript:**
```
detail(-1, "need_reverse", 0)
```

또는 **Python:**
```python
hou.pwd().inputs()[0].geometry().attribValue("need_reverse")
```

## 작동 원리

- `need_reverse = 0` → Switch가 Input 0 선택 (원본 유지)
- `need_reverse = 1` → Switch가 Input 1 선택 (반전된 버전)

## 디버깅

Switch SOP의 **Select Input** 값을 확인하려면:
1. Switch SOP 선택
2. **Info** 탭에서 현재 선택된 Input 확인
3. Geometry Spreadsheet에서 `need_reverse` attribute 확인

## 대안: Python SOP

Switch SOP도 작동하지 않으면 Python SOP 사용:

```python
node = hou.pwd()
geo = node.geometry()
upstream_node = node.inputs()[0]
upstream_geo = upstream_node.geometry()

need_reverse = upstream_geo.attribValue("need_reverse")

if need_reverse:
    # Reverse logic
    for prim in geo.prims():
        if prim.type() == hou.primType.Polygon or prim.type() == hou.primType.NURBSCurve:
            vertices = list(prim.vertices())
            vertices.reverse()
            # Rebuild primitive with reversed vertices
            # (더 복잡한 코드 필요)
```

하지만 Switch SOP 방법이 훨씬 간단하고 안정적입니다!




