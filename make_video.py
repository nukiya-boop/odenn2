from PIL import Image, ImageDraw, ImageFont
import os, math, subprocess, tempfile, shutil

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
W, H = 1080, 1920
FPS = 30
IMG_DIR = "/home/user/odenn2/images/"

# 実ファイル名をOSから取得してマッピング
def _img(name):
    for f in os.listdir(IMG_DIR):
        if name in f:
            return os.path.join(IMG_DIR, f)
    raise FileNotFoundError(name)
OUT = "/home/user/odenn2/pr_video.mp4"
TMP = tempfile.mkdtemp()

# 各画像のテロップ設定: (ファイル名, テロップ上, テロップ下, 表示秒数)
SCENES = [
    ("内観",
     "大阪メトロ梅田駅徒歩5分",
     "EST B1F 『おでん×スタンド』",
     4),
    ("釜_0012",
     "本格派おでんを気軽に",
     "リーズナブルな価格で",
     4),
    ("お出汁",
     "丁寧にとった長時間コトコトだし",
     "コクの旨味がしみわたる一品",
     4),
    ("組み合わせ",
     "女子会・デートにも♡",
     "お好みで選べるセットメニュー",
     4),
    ("IMG_0738",
     "スタイリッシュな店内で",
     "気軽に立ち寄りやすい♡",
     3),
    ("IMG_0747",
     "女性一人でも安心",
     "アフターワークにも最適",
     3),
    ("IMG_0752",
     "豊富なラインナップ",
     "ヘルシーなおでんも♡",
     3),
    ("QR",
     "【おでん×スタンド】",
     "大阪メトロ梅田駅徒歩5分 ・ EST B1F",
     5),
]

def fit_cover(img, w, h):
    r = max(w / img.width, h / img.height)
    new_w, new_h = int(img.width * r), int(img.height * r)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - w) // 2
    y = (new_h - h) // 2
    return img.crop((x, y, x + w, y + h))

def draw_text_with_shadow(draw, text, x, y, font, fill, shadow_offset=3):
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=fill)

def find_font(size):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

def make_frame(img_path, top_text, bottom_text, t, duration):
    img = Image.open(img_path).convert("RGBA")
    img = fit_cover(img, W, H)

    # 暗めのオーバーレイ (下部と上部)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    # 上部グラデーション帯
    for i in range(200):
        alpha = int(160 * (1 - i / 200))
        draw_ov.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
    # 下部グラデーション帯
    for i in range(250):
        alpha = int(180 * (1 - i / 250))
        draw_ov.line([(0, H - i), (W, H - i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    # フォント
    font_top = find_font(62)
    font_bottom = find_font(54)

    # フェードイン・アウト
    fade = 0.5
    if t < fade:
        alpha_factor = t / fade
    elif t > duration - fade:
        alpha_factor = (duration - t) / fade
    else:
        alpha_factor = 1.0
    alpha = int(255 * alpha_factor)

    # 上部テロップ
    bbox = draw.textbbox((0, 0), top_text, font=font_top)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    ty = 120
    draw.text((tx + 3, ty + 3), top_text, font=font_top, fill=(0, 0, 0, int(180 * alpha_factor)))
    draw.text((tx, ty), top_text, font=font_top, fill=(255, 255, 255, alpha))

    # 下部テロップ
    bbox2 = draw.textbbox((0, 0), bottom_text, font=font_bottom)
    bw = bbox2[2] - bbox2[0]
    bx = (W - bw) // 2
    by = H - 220
    draw.text((bx + 3, by + 3), bottom_text, font=font_bottom, fill=(0, 0, 0, int(180 * alpha_factor)))
    draw.text((bx, by), bottom_text, font=font_bottom, fill=(255, 230, 100, alpha))

    return img.convert("RGB")

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
    "-crf", "18",
    "-preset", "fast",
    OUT
]
subprocess.run(cmd, check=True)
shutil.rmtree(TMP)
print(f"完成: {OUT}")
