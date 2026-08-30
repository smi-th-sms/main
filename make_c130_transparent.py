from PIL import Image

src = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_m7oljqm7oljqm7ol.jfif"
out = r"E:\script\pythonWorkSpace\pattern_output\c130_flight_suit_pattern_transparent.png"
im = Image.open(src).convert("RGBA")
pix = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, _ = pix[x, y]
        spread = max(r, g, b) - min(r, g, b)
        light_gray = spread <= 10 and min(r, g, b) >= 185
        pix[x, y] = (r, g, b, 0 if light_gray else 255)
im.save(out)
print(out)
