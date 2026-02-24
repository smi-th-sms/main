# Add Connection Vertex to Target Line

## 목표

Target Line의 0번 포인트(이미 Base Line에 가장 가까운 endpoint) 앞에 새로운 vertex를 추가하고, 해당 vertex를 Base Line과의 접점으로 이동시킵니다.

## Attribute Wrangle (Detail mode)

**설정:**
- Run Over: **Detail (only once)**
- Input 0: Target Line (이미 Point 0이 Base Line에 가장 가까움)
- Input 1: Base Line

**VEX Code:**
```c
// ====================================================================
// Add Connection Vertex at Point 0 and Move to Closest Position on Base Line
// ====================================================================

int num_pts = npoints(0);

if (num_pts < 1) {
    printf("[ERROR] No points in Target Line\n");
    return;
}

int num_prims = nprimitives(0);
if (num_prims != 1) {
    printf("[ERROR] Expected 1 primitive, found %d\n", num_prims);
    return;
}

printf("\n========================================\n");
printf("Add Connection Vertex\n");
printf("========================================\n");

// === STEP 1: Point 0의 위치와 Base Line과의 접점 찾기 ===
vector root_pos = point(0, "P", 0);
printf("\n[Step 1] Find Closest Point on Base Line\n");
printf("  Root position (Point 0): (%.3f, %.3f, %.3f)\n", 
       root_pos.x, root_pos.y, root_pos.z);

// xyzdist로 Base Line과 가장 가까운 지점 찾기
int prim_num;
vector uv;
vector closest_pos = xyzdist(1, root_pos, prim_num, uv);

float contact_dist = distance(root_pos, closest_pos);

printf("  Closest point on Base Line: (%.3f, %.3f, %.3f)\n", 
       closest_pos.x, closest_pos.y, closest_pos.z);
printf("  Distance: %.4f\n", contact_dist);
printf("  Base prim: %d, UV: (%.3f, %.3f)\n", prim_num, uv.x, uv.y);

// === STEP 2: 새 포인트 생성 (처음엔 Point 0와 같은 위치) ===
printf("\n[Step 2] Create New Point\n");

int new_pt = addpoint(0, root_pos);
printf("  Created Point %d at (%.3f, %.3f, %.3f)\n", 
       new_pt, root_pos.x, root_pos.y, root_pos.z);

// === STEP 3: 기존 Primitive의 Vertex 정보 저장 ===
printf("\n[Step 3] Save Existing Primitive Vertices\n");

int old_prim = 0;
int old_vtxs[] = primvertices(0, old_prim);
int old_pts[];
resize(old_pts, len(old_vtxs));

for (int i = 0; i < len(old_vtxs); i++) {
    old_pts[i] = vertexpoint(0, old_vtxs[i]);
}

printf("  Saved %d vertices from old primitive\n", len(old_pts));

// === STEP 4: 기존 Primitive 삭제 ===
printf("\n[Step 4] Remove Old Primitive\n");

removeprim(0, old_prim, 0); // 0 = 포인트는 유지
printf("  Removed primitive %d (points preserved)\n", old_prim);

// === STEP 5: 새 Primitive 생성 (새 포인트가 맨 앞) ===
printf("\n[Step 5] Create New Primitive\n");

int new_prim = addprim(0, "polyline");

// 새 포인트를 맨 앞에 추가
addvertex(0, new_prim, new_pt);
printf("  Added vertex for new Point %d (connection point)\n", new_pt);

// 기존 포인트들 추가
for (int i = 0; i < len(old_pts); i++) {
    addvertex(0, new_prim, old_pts[i]);
}

printf("  Created new primitive with %d vertices\n", len(old_pts) + 1);

// === STEP 6: 새 포인트를 Base Line 접점으로 이동 ===
printf("\n[Step 6] Move New Point to Contact Position\n");

setpointattrib(0, "P", new_pt, closest_pos);

printf("  Moved Point %d to (%.3f, %.3f, %.3f)\n", 
       new_pt, closest_pos.x, closest_pos.y, closest_pos.z);

// === STEP 7: 검증 ===
printf("\n[Step 7] Verification\n");

printf("  Total points: %d (was %d)\n", npoints(0), num_pts);
printf("  Total primitives: %d\n", nprimitives(0));

int new_prim_vtxs[] = primvertices(0, new_prim);
printf("  New primitive vertices: %d\n", len(new_prim_vtxs));

printf("\n  Vertex order:\n");
for (int i = 0; i < len(new_prim_vtxs); i++) {
    int pt = vertexpoint(0, new_prim_vtxs[i]);
    vector pos = point(0, "P", pt);
    printf("    Vertex %d -> Point %d: (%.3f, %.3f, %.3f)", 
           i, pt, pos.x, pos.y, pos.z);
    if (i == 0) {
        printf(" <- NEW CONNECTION POINT");
    }
    printf("\n");
}

printf("\n========================================\n");
printf("Complete!\n");
printf("========================================\n\n");
```

## 작동 방식

1. **Point 0** (이미 Base Line에 가장 가까운 endpoint)의 위치 확인
2. **xyzdist**로 Base Line 상의 가장 가까운 접점 찾기
3. Point 0와 같은 위치에 **새 포인트 생성**
4. 기존 primitive의 vertex 순서 저장
5. 기존 primitive **삭제** (포인트는 유지)
6. **새 primitive 생성**:
   - 맨 앞: 새 포인트 (connection point)
   - 그 다음: Point 0, 1, 2, 3...
7. 새 포인트를 Base Line 접점으로 **이동**

## 결과

**Before:**
```
Target Line: P0 -- P1 -- P2 -- P3 -- P4
```

**After:**
```
Target Line: Pnew(at contact) -- P0 -- P1 -- P2 -- P3 -- P4
                ↓
            (Base Line 접점)
```

## 검증

Geometry Spreadsheet에서:
1. **Points** 탭: 새 포인트(마지막 번호)가 Base Line 접점에 있는지 확인
2. **Primitives** 탭: Vertex 개수가 1 증가했는지 확인
3. **Vertices** 탭: 첫 번째 vertex가 새 포인트를 가리키는지 확인

## 참고

- `xyzdist(geometry, point, &prim, &uv)`: geometry 상의 가장 가까운 위치 반환
- `addpoint(geo, position)`: 새 포인트 생성
- `removeprim(geo, prim_num, and_points)`: primitive 삭제
- `addprim(geo, "polyline")`: polyline primitive 생성
- `addvertex(geo, prim, point)`: primitive에 vertex 추가




