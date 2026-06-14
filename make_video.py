from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math, subprocess, tempfile, shutil

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
W, H = 1080, 1920
FPS = 30
IMG_DIR = "/home/user/odenn2/images/"
OUT = "/home/user/odenn2/pr_video.mp4"
TMP = tempfile.mkdtemp()

def _img(name):
    # 赤丸マーク済み画像
    if name == "IMG_0752_marked":
        marked_path = "/tmp/img0752_marked.jpg"
        if not os.path.exists(marked_path):
            _make_marked_img(marked_path)
        return marked_path
    for f in os.listdir(IMG_DIR):
        if name in f:
            return os.path.join(IMG_DIR, f)
    raise FileNotFoundError(name)

def _make_marked_img(out_path):
    for f in os.listdir(IMG_DIR):
        if "IMG_0752" in f:
            src = os.path.join(IMG_DIR, f)
            break
    img = Image.open(src).convert("RGBA")
    iw, ih = img.size  # 1080x1350
    draw = ImageDraw.Draw(img)
    # 「おでん×スタンド 三徳六味」: 中央やや下
    cx1, cy1, r1 = int(iw * 0.50), int(ih * 0.60), 90
    draw.ellipse([cx1-r1, cy1-r1, cx1+r1, cy1+r1], outline=(255, 30, 30, 255), width=8)
    # 「E-07」: 中央右上
    cx2, cy2, r2 = int(iw * 0.62), int(ih * 0.38), 60
    draw.ellipse([cx2-r2, cy2-r2, cx2+r2, cy2+r2], outline=(255, 30, 30, 255), width=8)
    img.convert("RGB").save(out_path, quality=95)

# (キーワード, テロップ上, テロップ下, 秒数)  ※下テロップNoneで非表示
SCENES = [
    ("内観",      "大阪メトロ梅田駅 徒歩5分",         "EST 『おでん×スタンド』",   4),
    ("釜_0012",   "本格派おでんを気軽に",              "リーズナブルな価格で",       4),
    ("お出汁",    "丁寧にとった長時間コトコトだし",    "コクの旨味がしみわたる一品", 4),
    ("組み合わせ","女子会・デートにも",                "お好みで選べるコース料理",   4),
    ("IMG_0738",  "スタイリッシュな店内で",            "気軽に立ち寄りやすい",       3),
    ("IMG_0747",  "女性一人でも安心",                  "仕事おわりに至福のひとときを", 3),
    ("IMG_0752_marked", "大阪メトロ梅田からすぐ",     "おでん×スタンド",            3),
    ("QR",        None,                                None,                         5),
]

def find_font(size, bold=True):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

def ease_out(t):
    return 1 - (1 - t) ** 3

def fit_contain_blurred(img, w, h):
    """黒背景 + オリジナル比率で中央配置"""
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    r_fit = min(w / img.width, h / img.height)
    fw, fh = int(img.width * r_fit), int(img.height * r_fit)
    fg = img.resize((fw, fh), Image.LANCZOS).convert("RGBA")
    fx = (w - fw) // 2
    fy = (h - fh) // 2
    bg.paste(fg, (fx, fy), fg)
    return bg

def draw_telop(base, top_text, bottom_text, alpha_factor):
    """おしゃれテロップを描画して返す"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    a = alpha_factor  # 0.0〜1.0

    # ===== 上部テロップエリア =====
    if top_text:
        font_sub = find_font(32)
        font_main = find_font(56)

        # 半透明の帯
        band_h = 200
        band = Image.new("RGBA", (W, band_h), (0, 0, 0, int(160 * a)))
        layer.paste(band, (0, 0), band)

        # 細いゴールドライン
        line_alpha = int(200 * a)
        draw.line([(60, 155), (W - 60, 155)], fill=(200, 170, 100, line_alpha), width=1)

        # テキスト（白・細め）
        bbox = draw.textbbox((0, 0), top_text, font=font_main)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2
        ty = 80
        # 薄いドロップシャドウ
        draw.text((tx + 2, ty + 2), top_text, font=font_main, fill=(0, 0, 0, int(100 * a)))
        draw.text((tx, ty), top_text, font=font_main, fill=(255, 255, 255, int(255 * a)))

    # ===== 下部テロップエリア =====
    if bottom_text:
        font_bottom = find_font(44)
        font_accent = find_font(26)

        # 下部グラデーション帯
        grad_h = 280
        for i in range(grad_h):
            row_a = int(190 * (1 - i / grad_h) * a)
            draw.line([(0, H - grad_h + i), (W, H - grad_h + i)], fill=(10, 8, 6, row_a))

        # アクセントライン（上）
        line_alpha = int(180 * a)
        draw.line([(60, H - 230), (W - 60, H - 230)], fill=(200, 170, 100, line_alpha), width=1)

        # メインテキスト
        bbox = draw.textbbox((0, 0), bottom_text, font=font_bottom)
        bw = bbox[2] - bbox[0]
        bx = (W - bw) // 2
        by = H - 200
        draw.text((bx + 2, by + 2), bottom_text, font=font_bottom, fill=(0, 0, 0, int(100 * a)))
        draw.text((bx, by), bottom_text, font=font_bottom, fill=(230, 200, 140, int(255 * a)))

        # アクセントライン（下）
        draw.line([(60, H - 130), (W - 60, H - 130)], fill=(200, 170, 100, line_alpha), width=1)


    return layer

def make_frame(img_path, top_text, bottom_text, t, duration):
    img = Image.open(img_path).convert("RGBA")
    frame = fit_contain_blurred(img, W, H)

    # フェードイン・アウト + スライドイン
    fade_in = 0.6
    fade_out = 0.5
    if t < fade_in:
        raw = t / fade_in
        alpha_factor = ease_out(raw)
    elif t > duration - fade_out:
        alpha_factor = (duration - t) / fade_out
    else:
        alpha_factor = 1.0
    alpha_factor = max(0.0, min(1.0, alpha_factor))

    # テロップ描画
    if top_text or bottom_text:
        telop = draw_telop(frame, top_text, bottom_text, alpha_factor)
        frame = Image.alpha_composite(frame, telop)

    # シーン全体フェード（最初と最後）
    if t < 0.3:
        black = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.3))))
        frame = Image.alpha_composite(frame, black)
    elif t > duration - 0.3:
        remain = duration - t
        black = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - remain / 0.3))))
        frame = Image.alpha_composite(frame, black)

    return frame.convert("RGB")

# フレーム生成
print("フレーム生成中...")
frame_idx = 0
for scene_i, (fname, top, bottom, dur) in enumerate(SCENES):
    img_path = _img(fname)
    n_frames = dur * FPS
    for f in range(n_frames):
        t = f / FPS
        frame = make_frame(img_path, top, bottom, t, dur)
        frame.save(os.path.join(TMP, f"frame_{frame_idx:05d}.png"))
        frame_idx += 1
    print(f"  シーン {scene_i+1}/{len(SCENES)} 完了")

# FFmpegで動画化
print("動画エンコード中...")
cmd = [
    FFMPEG, "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(TMP, "frame_%05d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "17",
    "-preset", "fast",
    OUT
]
subprocess.run(cmd, check=True)
shutil.rmtree(TMP)
print(f"完成: {OUT}")
