# Render the PDF to PNG page images and a 4x5 contact sheet.
import subprocess, sys, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "CSIT6000V_VerifiableTutor_v2.pdf")
OUT = os.path.join(HERE, "pages")
os.makedirs(OUT, exist_ok=True)
subprocess.run(["pdftoppm", "-png", "-r", "110", PDF, os.path.join(OUT, "page")], check=True)

files = sorted(f for f in os.listdir(OUT) if f.startswith("page-") and f.endswith(".png"))
files.sort(key=lambda f: int(f.split("-")[1].split(".")[0]))
print("pages", len(files))
cols, rows = 4, 5
tw, th = 480, 270
sheet = Image.new("RGB", (cols * tw, rows * th), (255, 255, 255))
for i, f in enumerate(files):
    im = Image.open(os.path.join(OUT, f)).convert("RGB")
    im = im.resize((tw, th), Image.LANCZOS)
    sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
sheet.save(os.path.join(HERE, "contact-sheet.png"))
print("contact", sheet.size)
