from PIL import Image

src = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_fb6j1tfb6j1tfb6j.jfif"
out = r"E:\script\pythonWorkSpace\pattern_output\pattern_white_background_removed.png"
im = Image.open(src).convert("RGBA")
pix = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, _ = pix[x, y]
        distance = 255 - min(r, g, b)
        pix[x, y] = (r, g, b, max(0, min(255, distance * 8)))
im.save(out)
print(out)
