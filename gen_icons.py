#!/usr/bin/env python3
"""從品牌 Logo 產生網站與 PWA 所需的全部圖片 (需要 Pillow 與 numpy: pip install pillow numpy)
用法:  python gen_icons.py
來源:  icons/logo-source.webp  (透明背景的橫式 Logo；要換 Logo 就直接覆蓋這個檔案，PNG/WEBP 皆可)
輸出:  ./icons/
  logo.png           頁首用橫式 Logo (原色)
  logo-white.png     頁尾深色底用 (白色版)
  logo-mark.png      只有 SH 字樣圖案的標誌
  icon-*.png         PWA 圖示 (any)
  icon-maskable-*    PWA 圖示 (maskable，Android 自適應圖示)
  apple-touch-icon   iOS 主畫面圖示
  favicon-32.png / favicon.ico
"""
import os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")
SOURCE = os.path.join(OUT, "logo-source.webp")

BRAND = (46, 90, 111)      # #2E5A6F  Logo 主色 (圖示底色)
WHITE = (255, 255, 255)
MARK_RIGHT_GAP = 0.5       # 判斷「圖案」與「文字」之間空白的寬度比例 (相對於圖案高度)


def trim(img, pad=0):
    """依透明度裁掉四周空白"""
    box = img.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    img = img.crop(box)
    if pad:
        canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
        canvas.paste(img, (pad, pad))
        return canvas
    return img


def recolor(img, rgb):
    """保留 alpha，整張改成單一顏色"""
    out = Image.new("RGBA", img.size, rgb + (0,))
    out.putalpha(img.getchannel("A"))
    return out


def extract_mark(img):
    """取出最左邊那組連續的圖案 (SH 標誌)，以欄位空白為分界"""
    a = np.array(img.getchannel("A")) > 30
    cols = a.any(axis=0)
    xs = np.where(cols)[0]
    start = xs[0]
    gap_limit = max(8, int(img.height * 0.12))
    end, gap = start, 0
    for x in range(start, len(cols)):
        if cols[x]:
            end, gap = x, 0
        else:
            gap += 1
            if gap > gap_limit:
                break
    return trim(img.crop((start, 0, end + 1, img.height)))


def fit_center(mark, size, ratio):
    """把標誌縮放到畫布的 ratio 比例並置中 (以較長邊為準)"""
    target = int(size * ratio)
    s = min(target / mark.width, target / mark.height)
    m = mark.resize((max(1, int(mark.width * s)), max(1, int(mark.height * s))), Image.LANCZOS)
    return m, ((size - m.width) // 2, (size - m.height) // 2)


def app_icon(mark_white, size, maskable=False):
    SS = 4  # 超取樣
    S = size * SS
    ratio = 0.50 if maskable else 0.64       # maskable 內容須在中央 80% 安全區內
    bg = Image.new("RGBA", (S, S), BRAND + (255,))
    m, pos = fit_center(mark_white, S, ratio)
    bg.alpha_composite(m, pos)
    bg = bg.resize((size, size), Image.LANCZOS)
    if maskable:
        return bg                              # 滿版，不裁角
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


def main():
    if not os.path.exists(SOURCE):
        raise SystemExit(f"找不到來源 Logo: {SOURCE}")
    src = trim(Image.open(SOURCE).convert("RGBA"))
    mark = extract_mark(src)
    mark_white = recolor(mark, WHITE)

    # --- 網站用 Logo ---
    h = 120  # 約 2x 解析度，頁首以 CSS 縮小至 40~48px 高
    wide = src.resize((int(src.width * h / src.height), h), Image.LANCZOS)
    wide.save(os.path.join(OUT, "logo.png"), optimize=True)
    recolor(wide, WHITE).save(os.path.join(OUT, "logo-white.png"), optimize=True)
    mk = mark.resize((int(mark.width * h / mark.height), h), Image.LANCZOS)
    mk.save(os.path.join(OUT, "logo-mark.png"), optimize=True)

    # --- PWA 圖示 ---
    for s in (72, 96, 128, 144, 152, 192, 384, 512):
        app_icon(mark_white, s).save(os.path.join(OUT, f"icon-{s}.png"), optimize=True)
    for s in (192, 512):
        app_icon(mark_white, s, maskable=True).save(os.path.join(OUT, f"icon-maskable-{s}.png"), optimize=True)

    # iOS：不可透明、系統自行裁圓角
    app_icon(mark_white, 180, maskable=True).convert("RGB").save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)

    # Favicon
    app_icon(mark_white, 32).save(os.path.join(OUT, "favicon-32.png"))
    app_icon(mark_white, 64).save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])

    print("完成！已輸出到:", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  -", f)


if __name__ == "__main__":
    main()
