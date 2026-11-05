# Recomprime public/img/* a JPEG (máx. 1600 px de ancho, calidad 80). Uso: python3 scripts/compress-images.py
from pathlib import Path
from PIL import Image

for src in sorted(Path(__file__).resolve().parent.parent.joinpath("public/img").iterdir()):
    if src.suffix.lower() not in {".jpg", ".png"}:
        continue
    im = Image.open(src).convert("RGB")
    im.thumbnail((1600, 1600))
    out = src.with_suffix(".jpg")
    im.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    if out != src:
        src.unlink()
    print(out.name, out.stat().st_size)
