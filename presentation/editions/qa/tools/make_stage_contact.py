from pathlib import Path
from PIL import Image, ImageDraw

ED = Path(__file__).resolve().parents[2]
QA = ED / "qa"
SRC = ED / "stage-html" / "exports" / "png"
OUT = QA / "contact-sheets"
OUT.mkdir(parents=True, exist_ok=True)

TILE_W, TILE_H = 640, 360
COLS, ROWS = 3, 4
PAD = 12
SHEET_W = COLS * TILE_W + (COLS + 1) * PAD
SHEET_H = ROWS * TILE_H + (ROWS + 1) * PAD
BG = (12, 12, 14)
tiles = []
for i in range(1, 21):
    img = Image.open(SRC / f"slide-{i:02d}.png").convert("RGB").resize((TILE_W, TILE_H), Image.LANCZOS)
    tiles.append((i, img))

for sheet_idx in (0, 1):
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), BG)
    draw = ImageDraw.Draw(sheet)
    for slot, (idx, img) in enumerate(tiles[sheet_idx * 10:(sheet_idx + 1) * 10]):
        col = slot % COLS
        row = slot // COLS
        x = PAD + col * (TILE_W + PAD)
        y = PAD + row * (TILE_H + PAD)
        sheet.paste(img, (x, y))
        draw.rectangle([x, y, x + 54, y + 26], fill=(0, 0, 0))
        draw.text((x + 8, y + 7), f"{idx:02d}", fill=(255, 255, 255))
    path = OUT / f"stage-contact-{sheet_idx + 1}.png"
    sheet.save(path)
    print(path, sheet.size)
