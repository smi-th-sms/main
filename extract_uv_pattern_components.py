from PIL import Image
import numpy as np
import json
import os

src = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_m7oljqm7oljqm7ol.jfif"
out_dir = r"E:\script\pythonWorkSpace\pattern_output\c130_components"
os.makedirs(out_dir, exist_ok=True)
rgba_path = os.path.join(out_dir, "c130_pattern_components_texture.png")
data_path = os.path.join(out_dir, "c130_pattern_components.json")

im = Image.open(src).convert("RGBA")
arr = np.asarray(im).copy()
rgb = arr[:, :, :3]
spread = rgb.max(axis=2) - rgb.min(axis=2)
mask = ~((spread <= 10) & (rgb.min(axis=2) >= 185))
arr[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
Image.fromarray(arr, "RGBA").save(rgba_path)

h, w = mask.shape
seen = np.zeros((h, w), dtype=np.uint8)
components = []
for y in range(h):
    for x in np.flatnonzero(mask[y] & (seen[y] == 0)).tolist():
        if seen[y, x]: continue
        stack = [(x, y)]; seen[y, x] = 1; pixels = []
        while stack:
            px, py = stack.pop(); pixels.append((px, py))
            for nx, ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = 1; stack.append((nx, ny))
        if len(pixels) < 500: continue
        p = np.asarray(pixels); x0, y0 = p.min(axis=0); x1, y1 = p.max(axis=0)
        if (x1-x0) < 20 or (y1-y0) < 15: continue
        pixset = set(pixels); edges = []
        for px, py in pixels:
            if (px, py-1) not in pixset: edges.append(((px, py), (px+1, py)))
            if (px+1, py) not in pixset: edges.append(((px+1, py), (px+1, py+1)))
            if (px, py+1) not in pixset: edges.append(((px+1, py+1), (px, py+1)))
            if (px-1, py) not in pixset: edges.append(((px, py+1), (px, py)))
        nxt = {}
        for a, z in edges: nxt.setdefault(a, []).append(z)
        loops = []
        while nxt:
            start = next(iter(nxt)); cur = start; loop = []
            while True:
                loop.append(cur); outs = nxt.get(cur)
                if not outs: break
                cur = outs.pop()
                if not outs: del nxt[loop[-1]]
                if cur == start: break
            if len(loop) >= 8: loops.append(loop)
        if loops:
            components.append({"index": len(components)+1, "bbox": [int(x0), int(y0), int(x1), int(y1)], "polygon": max(loops, key=len), "pixels": len(pixels)})

components.sort(key=lambda c: (c["bbox"][1], c["bbox"][0]))
for i, c in enumerate(components, 1): c["index"] = i
with open(data_path, "w", encoding="utf-8") as f:
    json.dump({"width": w, "height": h, "texture": rgba_path, "components": components}, f)
print("components", len(components), "texture", rgba_path, "data", data_path)
