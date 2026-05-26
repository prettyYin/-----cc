"""一次性脚本：从 sprite 生成多尺寸 .ico 应用图标。

跑法（项目根目录）：
    python build/make_ico.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src_png = root / "src" / "assets" / "sprites" / "idle" / "frame_01.png"
    out_ico = root / "src" / "assets" / "icons" / "xiledi.ico"

    if not src_png.exists():
        raise SystemExit(f"[make_ico] 源图不存在：{src_png}")

    out_ico.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src_png).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(out_ico, format="ICO", sizes=sizes)
    print(f"[make_ico] 已生成 {out_ico}（{out_ico.stat().st_size // 1024} KB）")


if __name__ == "__main__":
    main()
