"""
Valorex Instagram スライド生成サーバー
起動: python generate.py
アクセス: http://localhost:5000
"""

import json
import base64
import os
from pathlib import Path
from flask import Flask, request, Response, send_file
import anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
LOGO_FILE = "fe7b576e4455358a0be7c2ed3465326f.avif"
IMAGE_DIR = BASE_DIR / "画像"
ACCOUNT = "@valorex_mgp"

# スライドインデックス(0始まり)に対応する画像ファイル名
SLIDE_IMAGES = [
    "img_cover.jpg",   # slide 1: 表紙
    "img_case.jpg",    # slide 2: 問題提起
    "img_wallet.jpg",  # slide 3: 本文①
    "img_case.jpg",    # slide 4: 本文②
    "img_cover.jpg",   # slide 5: CTA
]

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# Claude API プロンプト
# ─────────────────────────────────────────────

PROMPT_TEMPLATE = """\
あなたはValorex（本革スマホケース・財布・革小物ブランド）のInstagramコンテンツライターです。

ブランド情報:
- ターゲット: 30歳以上の男女
- 雰囲気: 高級感×親しみやすさ（Bonaventura / Delvaux調）
- 言語: 日英混在（日本語メイン、英語はおしゃれなアクセント）

テーマ「{theme}」について、5枚のInstagramリール/ストーリー用スライドコンテンツを作成してください。

以下のJSON形式のみで返してください（```json 等のマークダウン不要、説明文不要）:

{{
  "slides": [
    {{
      "type": "cover",
      "en_label": "英語ラベル（例: Genuine Leather / The Art of Craft）3〜5単語",
      "ja_title": "日本語メインタイトル（改行は\\nで表現。2〜4語×1〜2行）",
      "ja_sub": "短いサブコピー（20文字以内）"
    }},
    {{
      "type": "problem",
      "en_label": "英語フレーズ（3〜5単語）",
      "ja_heading": "問題提起・共感の見出し（15文字以内）",
      "points": ["共感ポイント1（25文字以内）", "共感ポイント2（25文字以内）", "共感ポイント3（25文字以内）"]
    }},
    {{
      "type": "content",
      "en_label": "英語フレーズ（3〜5単語）",
      "ja_heading": "本文①の見出し（15文字以内）",
      "points": ["ポイント1（30文字以内）", "ポイント2（30文字以内）", "ポイント3（30文字以内）"]
    }},
    {{
      "type": "content",
      "en_label": "英語フレーズ（3〜5単語）",
      "ja_heading": "本文②の見出し（15文字以内）",
      "points": ["ポイント1（30文字以内）", "ポイント2（30文字以内）", "ポイント3（30文字以内）"]
    }},
    {{
      "type": "cta",
      "en_label": "英語フレーズ（3〜5単語）",
      "ja_heading": "まとめ・締めの言葉（20文字以内）",
      "ja_body": "フォロー・購買を促す文章（40〜60文字）",
      "cta_text": "プロフィールへ ▶"
    }}
  ]
}}"""


# ─────────────────────────────────────────────
# ロゴ（Base64埋め込み）
# ─────────────────────────────────────────────

def get_logo_b64() -> str:
    path = BASE_DIR / LOGO_FILE
    if path.exists():
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:image/avif;base64,{data}"
    return ""


def get_product_images() -> list:
    """スライドごとの製品画像をBase64リストで返す"""
    result = []
    for fname in SLIDE_IMAGES:
        path = IMAGE_DIR / fname
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("utf-8")
            result.append(f"data:image/jpeg;base64,{data}")
        else:
            result.append("")
    return result


# ─────────────────────────────────────────────
# CSS（スライド共通スタイル）
# ─────────────────────────────────────────────

SLIDE_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garant:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=Noto+Serif+JP:wght@200;300;400;500&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --cream:       #FEF6F0;
  --brown-dark:  #1C1008;
  --brown-mid:   #6B4F3A;
  --brown-light: #A8856C;
  --gold:        #C4973E;
  --gold-light:  #E8D5B7;
  --white-soft:  #FFFAF7;
}

/* ── スライド本体 ── */
.slide {
  width: 1080px;
  height: 1920px;
  background: var(--cream);
  position: relative;
  font-family: 'Cormorant Garant', 'Noto Serif JP', serif;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 背景装飾グラデーション */
.slide::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 80% 15%, rgba(196,151,62,0.07) 0%, transparent 55%),
    radial-gradient(ellipse at 15% 85%, rgba(196,151,62,0.05) 0%, transparent 50%);
  pointer-events: none;
}

/* ── ヘッダー ── */
.slide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 64px 80px 0;
  flex-shrink: 0;
}

.logo-img {
  height: 52px;
  width: auto;
  object-fit: contain;
}

.slide-num {
  font-family: 'Cormorant Garant', serif;
  font-size: 26px;
  font-weight: 300;
  color: var(--brown-light);
  letter-spacing: 0.15em;
}

/* ── ボディ ── */
.slide-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 96px;
  position: relative;
}

/* ── フッター ── */
.slide-footer {
  flex-shrink: 0;
  padding: 0 80px 72px;
  text-align: center;
}

.footer-line {
  height: 1px;
  background: var(--gold-light);
  margin-bottom: 36px;
}

.account-tag {
  font-family: 'Cormorant Garant', serif;
  font-size: 30px;
  font-weight: 300;
  color: var(--brown-mid);
  letter-spacing: 0.12em;
}

/* ── 共通パーツ ── */
.en-label {
  font-family: 'Cormorant Garant', serif;
  font-size: 26px;
  font-weight: 300;
  letter-spacing: 0.38em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 32px;
}

.gold-line {
  width: 72px;
  height: 1px;
  background: var(--gold);
  margin-bottom: 48px;
}

.gold-line-center {
  width: 72px;
  height: 1px;
  background: var(--gold);
  margin: 0 auto 40px;
}

.ja-title-large {
  font-family: 'Noto Serif JP', 'Cormorant Garant', serif;
  font-size: 92px;
  font-weight: 300;
  color: var(--brown-dark);
  line-height: 1.35;
  letter-spacing: 0.06em;
  margin-bottom: 52px;
}

.ja-sub {
  font-family: 'Noto Serif JP', serif;
  font-size: 32px;
  font-weight: 300;
  color: var(--brown-mid);
  letter-spacing: 0.12em;
  line-height: 1.7;
}

/* 装飾スライド番号 */
.slide-num-deco {
  font-family: 'Cormorant Garant', serif;
  font-size: 220px;
  font-weight: 300;
  color: rgba(196,151,62,0.09);
  line-height: 1;
  position: absolute;
  top: 120px;
  right: 48px;
  pointer-events: none;
  letter-spacing: -0.02em;
}

.ja-heading {
  font-family: 'Noto Serif JP', serif;
  font-size: 64px;
  font-weight: 400;
  color: var(--brown-dark);
  line-height: 1.4;
  letter-spacing: 0.05em;
  margin-bottom: 56px;
}

/* 問題提起: シンプルポイントリスト */
.points-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 44px;
}

.point-item {
  display: flex;
  align-items: flex-start;
  gap: 32px;
}

.point-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--gold);
  flex-shrink: 0;
  margin-top: 20px;
}

.point-text {
  font-family: 'Noto Serif JP', serif;
  font-size: 40px;
  font-weight: 300;
  color: var(--brown-dark);
  line-height: 1.6;
  letter-spacing: 0.04em;
}

/* コンテンツ: 番号付きポイント */
.numbered-points {
  display: flex;
  flex-direction: column;
  gap: 52px;
}

.numbered-point {}

.point-label {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 12px;
}

.point-num {
  font-family: 'Cormorant Garant', serif;
  font-size: 30px;
  font-weight: 300;
  color: var(--gold);
  letter-spacing: 0.1em;
  flex-shrink: 0;
}

.point-line {
  flex: 1;
  height: 1px;
  background: var(--gold-light);
}

.point-content {
  font-family: 'Noto Serif JP', serif;
  font-size: 36px;
  font-weight: 300;
  color: var(--brown-dark);
  line-height: 1.65;
  letter-spacing: 0.04em;
  padding-left: 54px;
}

/* CTA スライド */
.cta-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  justify-content: space-between;
}

.cta-top {
  text-align: center;
}

.cta-heading {
  font-family: 'Noto Serif JP', serif;
  font-size: 68px;
  font-weight: 300;
  color: var(--brown-dark);
  line-height: 1.4;
  letter-spacing: 0.06em;
  margin-bottom: 52px;
}

.cta-body {
  font-family: 'Noto Serif JP', serif;
  font-size: 32px;
  font-weight: 300;
  color: var(--brown-mid);
  line-height: 1.9;
  letter-spacing: 0.06em;
  margin-bottom: 72px;
}

.cta-button {
  display: inline-block;
  border: 1px solid var(--gold);
  padding: 28px 88px;
  font-family: 'Cormorant Garant', 'Noto Serif JP', serif;
  font-size: 30px;
  font-weight: 400;
  color: var(--gold);
  letter-spacing: 0.2em;
}

.cta-bottom {
  text-align: center;
}

.cta-logo {
  height: 60px;
  width: auto;
  object-fit: contain;
  opacity: 0.75;
  display: block;
  margin: 0 auto 28px;
}

.cta-brand {
  font-family: 'Cormorant Garant', serif;
  font-size: 40px;
  font-weight: 300;
  letter-spacing: 0.45em;
  color: var(--brown-dark);
  text-transform: uppercase;
}

/* ── 製品画像 ── */
.cover-img-wrap {
  width: 100%;
  height: 620px;
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.cover-img-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 220px;
  background: linear-gradient(to bottom, transparent, #FEF6F0);
}

.slide-product-img {
  width: 100%;
  height: 340px;
  object-fit: cover;
  object-position: center;
  margin-bottom: 44px;
  display: block;
  flex-shrink: 0;
}

.cta-product-img {
  width: 580px;
  height: 420px;
  object-fit: cover;
  object-position: center;
  margin: 0 auto 52px;
  display: block;
}
"""

GALLERY_CSS = """
body {
  background: #241C18;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 56px;
  padding: 64px 40px;
  min-height: 100vh;
}

.gallery-title {
  font-family: 'Cormorant Garant', serif;
  font-size: 17px;
  font-weight: 300;
  letter-spacing: 0.35em;
  text-transform: uppercase;
  color: #C4973E;
}

.slide-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.slide-wrapper {
  width: 432px;
  height: 768px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 24px 80px rgba(0,0,0,0.55);
}

.slide-wrapper .slide {
  transform: scale(0.4);
  transform-origin: top left;
  position: absolute;
  top: 0;
  left: 0;
}

.btn-fullsize {
  font-family: 'Cormorant Garant', serif;
  font-size: 12px;
  font-weight: 300;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: #C4973E;
  border: 1px solid #C4973E;
  padding: 9px 26px;
  background: none;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: all 0.25s;
}

.btn-fullsize:hover {
  background: #C4973E;
  color: #241C18;
}
"""


# ─────────────────────────────────────────────
# スライドパーツ
# ─────────────────────────────────────────────

def _header(logo_b64: str, num: int, total: int) -> str:
    logo = (f'<img class="logo-img" src="{logo_b64}" alt="Valorex">'
            if logo_b64 else '<span style="font-family:\'Cormorant Garant\',serif;font-size:28px;font-weight:300;letter-spacing:.4em;color:#1C1008;">VALOREX</span>')
    return f"""
    <div class="slide-header">
      {logo}
      <span class="slide-num">0{num} / 0{total}</span>
    </div>"""


def _footer() -> str:
    return f"""
    <div class="slide-footer">
      <div class="footer-line"></div>
      <span class="account-tag">{ACCOUNT}</span>
    </div>"""


def render_cover(s: dict, num: int, total: int, logo_b64: str, product_img: str = "") -> str:
    title_html = s.get("ja_title", "").replace("\\n", "<br>").replace("\n", "<br>")
    img_html = ""
    if product_img:
        img_html = f"""
  <div class="cover-img-wrap">
    <img class="cover-img" src="{product_img}" alt="">
    <div class="cover-img-fade"></div>
  </div>"""
    return f"""
<div class="slide">
  {_header(logo_b64, num, total)}
  {img_html}
  <div class="slide-body">
    <div class="en-label">{s.get("en_label","")}</div>
    <div class="gold-line"></div>
    <div class="ja-title-large">{title_html}</div>
    <div class="ja-sub">{s.get("ja_sub","")}</div>
  </div>
  {_footer()}
</div>"""


def render_problem(s: dict, num: int, total: int, logo_b64: str, product_img: str = "") -> str:
    pts = "".join(
        f'<li class="point-item"><span class="point-dot"></span>'
        f'<span class="point-text">{p}</span></li>'
        for p in s.get("points", [])
    )
    img_html = f'<img class="slide-product-img" src="{product_img}" alt="">' if product_img else ""
    return f"""
<div class="slide">
  <div class="slide-num-deco">0{num}</div>
  {_header(logo_b64, num, total)}
  <div class="slide-body">
    {img_html}
    <div class="en-label">{s.get("en_label","")}</div>
    <div class="gold-line"></div>
    <div class="ja-heading">{s.get("ja_heading","")}</div>
    <ul class="points-list">{pts}</ul>
  </div>
  {_footer()}
</div>"""


def render_content(s: dict, num: int, total: int, logo_b64: str, product_img: str = "") -> str:
    pts = "".join(f"""
    <div class="numbered-point">
      <div class="point-label">
        <span class="point-num">0{i+1}</span>
        <div class="point-line"></div>
      </div>
      <div class="point-content">{p}</div>
    </div>""" for i, p in enumerate(s.get("points", [])))
    img_html = f'<img class="slide-product-img" src="{product_img}" alt="">' if product_img else ""
    return f"""
<div class="slide">
  <div class="slide-num-deco">0{num}</div>
  {_header(logo_b64, num, total)}
  <div class="slide-body">
    {img_html}
    <div class="en-label">{s.get("en_label","")}</div>
    <div class="gold-line"></div>
    <div class="ja-heading">{s.get("ja_heading","")}</div>
    <div class="numbered-points">{pts}</div>
  </div>
  {_footer()}
</div>"""


def render_cta(s: dict, num: int, total: int, logo_b64: str, product_img: str = "") -> str:
    cta_logo = (f'<img class="cta-logo" src="{logo_b64}" alt="Valorex">' if logo_b64 else "")
    img_html = f'<img class="cta-product-img" src="{product_img}" alt="">' if product_img else ""
    return f"""
<div class="slide">
  {_header(logo_b64, num, total)}
  <div class="slide-body">
    <div class="cta-wrapper">
      <div class="cta-top">
        {img_html}
        <div class="gold-line-center"></div>
        <div class="en-label" style="text-align:center;">{s.get("en_label","")}</div>
        <div class="gold-line-center"></div>
        <div class="cta-heading">{s.get("ja_heading","")}</div>
        <div class="cta-body">{s.get("ja_body","")}</div>
        <div class="cta-button">{s.get("cta_text","プロフィールへ ▶")}</div>
      </div>
      <div class="cta-bottom">
        {cta_logo}
        <div class="cta-brand">Valorex</div>
      </div>
    </div>
  </div>
  {_footer()}
</div>"""


def build_slide_html(s: dict, num: int, total: int, logo_b64: str, product_img: str = "") -> str:
    t = s.get("type", "content")
    if t == "cover":
        return render_cover(s, num, total, logo_b64, product_img)
    elif t == "problem":
        return render_problem(s, num, total, logo_b64, product_img)
    elif t == "cta":
        return render_cta(s, num, total, logo_b64, product_img)
    else:
        return render_content(s, num, total, logo_b64, product_img)


def build_standalone_page(slide_html: str, num: int) -> str:
    """フルサイズ（1080×1920）の単体スライドHTMLを生成"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>Valorex Slide {num:02d}</title>
<style>
{SLIDE_BASE_CSS}
body {{ margin: 0; background: #FEF6F0; }}
</style>
</head>
<body>
{slide_html}
</body>
</html>"""


def render_gallery_page(slides_data: dict, theme: str, logo_b64: str) -> str:
    slides = slides_data.get("slides", [])
    total = len(slides)
    product_imgs = get_product_images()

    cards_html = []
    standalone_pages = []

    for i, s in enumerate(slides, 1):
        img = product_imgs[i - 1] if i - 1 < len(product_imgs) else ""
        html = build_slide_html(s, i, total, logo_b64, img)
        standalone = build_standalone_page(html, i)
        standalone_pages.append(standalone)
        cards_html.append(f"""
<div class="slide-card">
  <div class="slide-wrapper">{html}</div>
  <a href="#" class="btn-fullsize" onclick="openSlide({i-1});return false;">Full Size</a>
</div>""")

    cards = "\n".join(cards_html)

    # 各スライドの standalone HTML を JSON 文字列として埋め込む
    pages_js = "const SLIDES = [\n" + ",\n".join(
        json.dumps(p, ensure_ascii=False) for p in standalone_pages
    ) + "\n];"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>Valorex — {theme}</title>
<style>
{SLIDE_BASE_CSS}
{GALLERY_CSS}
</style>
</head>
<body>
<div class="gallery-title">Valorex — {theme}</div>
{cards}
<script>
{pages_js}
function openSlide(idx) {{
  const w = window.open('', '_blank');
  w.document.write(SLIDES[idx]);
  w.document.close();
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
# Flask ルート
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(BASE_DIR / "index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    theme = data.get("theme", "").strip()
    if not theme:
        return {"error": "テーマを入力してください"}, 400

    prompt = PROMPT_TEMPLATE.format(theme=theme)

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            raw = stream.get_final_message().content[0].text.strip()

        # ```json ... ``` ブロックを除去
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0].strip()

        slides_data = json.loads(raw)

    except json.JSONDecodeError as e:
        return {"error": f"JSON解析エラー: {e}"}, 500
    except anthropic.APIError as e:
        return {"error": f"API エラー: {e}"}, 500

    logo_b64 = get_logo_b64()
    html = render_gallery_page(slides_data, theme, logo_b64)
    return Response(html, mimetype="text/html; charset=utf-8")


# ─────────────────────────────────────────────
# 起動
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Valorex スライドジェネレーター起動")
    print("  -> http://localhost:5000")
    app.run(debug=True, port=5000)
