import base64
import html
import math
import random
from urllib.parse import quote

import streamlit as st
from indexer import (build_index, search, get_snippet, tokenize,
                     grow_index, make_overview)

st.set_page_config(page_title="Space Search", page_icon="🚀")


# ---------- procedurally generated sky ----------

def to_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def circle(x, y, r, fill, opacity):
    return (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" '
            f'fill="{fill}" opacity="{opacity:.2f}"/>')


def star_colour(rng):
    r = rng.random()
    if r < 0.55:
        return "#ffffff"
    if r < 0.75:
        return "#cfdcff"   # blue-white
    if r < 0.90:
        return "#ffeccc"   # warm white
    if r < 0.97:
        return "#ffc58a"   # orange
    return "#ff9d8a"       # red


def make_starfield(w=1920, h=1080, seed=7):
    """Random stars, with half of them crowded into a tilted Milky Way band."""
    rng = random.Random(seed)
    ang = math.radians(-28)
    cx, cy = w * 0.5, h * 0.55
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           'preserveAspectRatio="xMidYMid slice">']
    count = 0
    while count < 1300:
        if rng.random() < 0.5:
            t = rng.uniform(-0.75, 0.75) * w
            s = rng.gauss(0, h * 0.1)
            x = cx + t * math.cos(ang) - s * math.sin(ang)
            y = cy + t * math.sin(ang) + s * math.cos(ang)
        else:
            x, y = rng.uniform(0, w), rng.uniform(0, h)
        if not (0 <= x <= w and 0 <= y <= h):
            continue
        r = rng.choice([0.5, 0.6, 0.7, 0.8, 0.9, 1.1, 1.4])  # most are tiny
        out.append(circle(x, y, r, star_colour(rng), rng.uniform(0.25, 0.9)))
        count += 1
    out.append("</svg>")
    return to_uri("".join(out))


def make_twinkle(seed=1, n=45, w=1920, h=1080):
    """Bright stars that each twinkle at their own speed (SVG animation)."""
    rng = random.Random(seed)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           'preserveAspectRatio="xMidYMid slice"><defs>'
           '<radialGradient id="g"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>'
           '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>']
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(1.2, 2.4)
        col = star_colour(rng)
        dur, offset = rng.uniform(2.5, 7), rng.uniform(0, 7)
        out.append(
            '<g><animate attributeName="opacity" values=".25;1;.25" '
            f'dur="{dur:.1f}s" begin="-{offset:.1f}s" repeatCount="indefinite"/>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r * 5:.1f}" fill="url(#g)" opacity=".35"/>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{col}"/>'
        )
        if r > 1.9:  # a few get faint diffraction spikes
            L = r * 6
            out.append(f'<path d="M{x - L:.0f} {y:.0f}H{x + L:.0f}M{x:.0f} {y - L:.0f}V{y + L:.0f}" '
                       f'stroke="{col}" stroke-width=".6" opacity=".45"/>')
        out.append("</g>")
    out.append("</svg>")
    return to_uri("".join(out))


def make_galaxy(size=1000, seed=11):
    """A spiral galaxy: bright core, two unequal arms, dust lanes, pink star-forming knots."""
    rng = random.Random(seed)
    c, R, wind = size / 2, size * 0.47, 7.0

    def arm():
        return 0.0 if rng.random() < 0.58 else 3.0  # two arms, deliberately unequal

    def spiral_point(scale):
        r = R
        while r >= R:
            r = rng.expovariate(1 / scale)
        if rng.random() < 0.2:  # loose disc stars between the arms
            th = rng.uniform(0, 2 * math.pi)
        else:
            th = arm() + wind * r / R + rng.gauss(0, 0.2)
        return c + r * math.cos(th), c + r * math.sin(th), r

    def on_arm(r_lo, r_hi, offset=0.0, spread=0.08):
        r = rng.uniform(r_lo, r_hi)
        th = arm() + wind * r / R + offset + rng.gauss(0, spread)
        return c + r * math.cos(th), c + r * math.sin(th)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}"><defs>'
           '<filter id="b" x="-30%" y="-30%" width="160%" height="160%">'
           '<feGaussianBlur stdDeviation="9"/></filter>'
           '<radialGradient id="core"><stop offset="0" stop-color="#fff6e0"/>'
           '<stop offset=".3" stop-color="#ffc878" stop-opacity=".7"/>'
           '<stop offset="1" stop-color="#ff9a4a" stop-opacity="0"/></radialGradient>'
           '</defs>']

    # soft blue glow along the arms, plus pink star-forming knots
    out.append('<g filter="url(#b)">')
    for _ in range(170):
        x, y, _r = spiral_point(190)
        out.append(circle(x, y, rng.uniform(16, 38), "#8fa8ff", rng.uniform(0.05, 0.10)))
    for _ in range(22):
        x, y = on_arm(120, R * 0.9)
        out.append(circle(x, y, rng.uniform(6, 14), "#ff8fb8", rng.uniform(0.12, 0.25)))
    out.append("</g>")

    # dark dust lanes on the inner edge of the arms
    out.append('<g filter="url(#b)">')
    for _ in range(70):
        x, y = on_arm(70, R * 0.85, offset=-0.28, spread=0.06)
        out.append(circle(x, y, rng.uniform(8, 20), "#04060e", rng.uniform(0.10, 0.20)))
    out.append("</g>")

    out.append(f'<circle cx="{c}" cy="{c}" r="170" fill="url(#core)" opacity=".85"/>')

    # the stars themselves
    warm = ["#ffe2b0", "#ffd9a0", "#fff1d6"]
    cool = ["#ffffff", "#cfe0ff", "#aac4ff", "#dce8ff", "#ffe9c9"]
    for _ in range(1500):
        x, y, r = spiral_point(150)
        if r < 70:
            col = rng.choice(warm)
        elif rng.random() < 0.05:
            col = "#ff9cc0"
        else:
            col = rng.choice(cool)
        out.append(circle(x, y, rng.uniform(0.5, 1.7), col, rng.uniform(0.4, 1)))
    for _ in range(350):  # dense bulge
        out.append(circle(c + rng.gauss(0, 36), c + rng.gauss(0, 36),
                          rng.uniform(0.5, 1.5), rng.choice(warm), rng.uniform(0.5, 1)))
    out.append("</svg>")
    return to_uri("".join(out))


CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Hanken+Grotesk:wght@400;500;600&display=swap');

:root {
  color-scheme: dark;
  --bg: #05080f;
  --card: rgba(14, 20, 40, .80);
  --line: #26325a;
  --text: #e9edf7;
  --muted: #94a0c2;
  --accent: #ffb454;
  --serif: 'Fraunces', Georgia, serif;
  --sans: 'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif;
}

/* ---------- the sky ---------- */
.stApp {
  background-color: var(--bg) !important;
  background-image:
    url("__STARS__"),
    radial-gradient(520px 190px at 14% 76%, rgba(170, 160, 255, .13), transparent 70%),
    radial-gradient(640px 230px at 33% 64%, rgba(200, 175, 255, .17), transparent 70%),
    radial-gradient(760px 260px at 52% 54%, rgba(220, 200, 255, .20), transparent 70%),
    radial-gradient(560px 200px at 72% 43%, rgba(180, 170, 255, .15), transparent 70%),
    radial-gradient(480px 170px at 90% 33%, rgba(150, 160, 255, .12), transparent 70%),
    linear-gradient(152deg, transparent 33%, rgba(140, 130, 240, .08) 42%, rgba(190, 180, 255, .13) 50%, rgba(140, 130, 240, .08) 58%, transparent 67%),
    linear-gradient(152deg, transparent 48.6%, rgba(4, 6, 16, .35) 50%, transparent 51.4%),
    radial-gradient(800px 500px at 0% 0%, rgba(70, 90, 210, .22), transparent 60%),
    radial-gradient(700px 450px at 100% 100%, rgba(255, 150, 80, .09), transparent 60%) !important;
  background-size: cover !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
  background-attachment: fixed !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stHeader"], [data-testid="stBottom"] { background: transparent; }

/* twinkling stars: each star animates on its own, and the whole layer sways a little */
.stApp::before {
  content: ""; position: fixed; inset: -3%; z-index: 0; pointer-events: none;
  background: url("__TWINKLE__") center / cover no-repeat;
  animation: ss-sway 80s ease-in-out infinite alternate;
}
@keyframes ss-sway {
  from { transform: translate(-1.2%, -.8%); }
  to   { transform: translate(1.2%, .8%); }
}

/* slowly drifting, breathing nebula glow */
.stApp::after {
  content: ""; position: fixed; inset: -10%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(500px 320px at 20% 30%, rgba(120, 90, 255, .10), transparent 70%),
    radial-gradient(600px 360px at 75% 70%, rgba(255, 120, 160, .07), transparent 70%),
    radial-gradient(520px 300px at 55% 15%, rgba(70, 160, 255, .08), transparent 70%);
  animation: ss-nebula 40s ease-in-out infinite alternate;
}
@keyframes ss-nebula {
  from { transform: translate(-3%, -2%) scale(1);    opacity: .7; }
  to   { transform: translate(3%, 2%)   scale(1.08); opacity: 1; }
}

/* shooting stars */
.stApp .ss-shoot {
  position: fixed; z-index: 0; pointer-events: none;
  width: 140px; height: 2px; border-radius: 2px; opacity: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0), #fff);
  transform: rotate(28deg);
}
.stApp .ss-shoot.s1 { top: 8%;  left: 12%; animation: ss-shoot 19s linear 4s infinite; }
.stApp .ss-shoot.s2 { top: 22%; left: 52%; animation: ss-shoot 27s linear 11s infinite; }
.stApp .ss-shoot.s3 { top: 5%;  left: 66%; animation: ss-shoot 33s linear 20s infinite; }
@keyframes ss-shoot {
  0%   { opacity: 0; transform: rotate(28deg) translateX(0); }
  1%   { opacity: 1; }
  5%   { opacity: 0; transform: rotate(28deg) translateX(650px); }
  100% { opacity: 0; transform: rotate(28deg) translateX(650px); }
}

/* tilted spiral galaxy, rotating slowly */
.stApp .ss-galaxy {
  position: fixed; top: -330px; right: -390px; width: 1080px; height: 1080px;
  pointer-events: none; z-index: -1; opacity: .9;
  transform: rotate(-22deg) scale(1, .52);
}
.stApp .ss-galaxy div {
  width: 100%; height: 100%;
  background: url("__GALAXY__") center / contain no-repeat;
  animation: ss-spin 200s linear infinite;
}
@keyframes ss-spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .stApp::before, .stApp::after { animation: none; }
  .stApp .ss-shoot { display: none; }
  .stApp .ss-galaxy div { animation: none; }
}

/* ---------- page ---------- */
html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp button {
  font-family: var(--sans) !important;
  color: var(--text);
}
header[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { max-width: 760px; padding-top: 3.5rem; position: relative; z-index: 2; }

/* hero */
.stApp .ss-title {
  font-family: var(--serif); font-weight: 700; font-size: 3.2rem;
  letter-spacing: -0.02em; line-height: 1.05; color: var(--text);
}
.stApp .ss-title span { color: var(--accent); }
.stApp .ss-tag { font-family: var(--sans); color: var(--muted); font-size: 1.05rem; margin-top: .5rem; }
.stApp .ss-stats {
  font-family: var(--sans); color: var(--muted); font-size: .78rem;
  letter-spacing: .12em; text-transform: uppercase; margin: 1rem 0 1.4rem;
}

/* search box */
div[data-baseweb="input"] {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  backdrop-filter: blur(6px);
}
div[data-baseweb="input"]:focus-within {
  border-color: var(--accent); box-shadow: 0 0 0 3px rgba(255, 180, 84, .18);
}
div[data-baseweb="input"] input {
  background: transparent; color: var(--text); font-size: 1.08rem; padding: .85rem 1rem;
}
.stApp label p { color: var(--muted); font-size: .88rem; }

/* overview card */
.stApp .ss-overview {
  font-family: var(--sans);
  background: linear-gradient(180deg, rgba(255, 180, 84, .09), rgba(255, 180, 84, .02)), var(--card);
  border: 1px solid #3b3552; border-radius: 18px; backdrop-filter: blur(8px);
  padding: 1.4rem 1.7rem 1.2rem; margin: 1.4rem 0 2.2rem;
  box-shadow: 0 12px 40px rgba(0, 0, 0, .4);
}
.stApp .ss-label {
  color: var(--accent); font-size: .74rem; font-weight: 600;
  letter-spacing: .16em; text-transform: uppercase; margin-bottom: .9rem;
}
.stApp .ss-para { color: var(--text); font-size: 1.04rem; line-height: 1.75; margin-bottom: .9rem; }
.stApp .ss-cite { color: var(--accent); font-size: .72rem; font-weight: 600; vertical-align: super; margin-left: 3px; }
.stApp .ss-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .3rem; }
.stApp .ss-chip {
  color: var(--muted); font-size: .8rem; border: 1px solid var(--line);
  border-radius: 999px; padding: .25rem .8rem; background: rgba(255, 255, 255, .03);
}
.stApp .ss-chip b { color: var(--accent); margin-right: .3rem; }
.stApp .ss-note { color: var(--muted); font-size: .74rem; margin-top: 1rem; }

/* result cards */
.stApp .ss-heading {
  font-family: var(--serif); font-size: 1.5rem; font-weight: 500;
  color: var(--text); margin: 0 0 .9rem;
}
.stApp .ss-result {
  font-family: var(--sans); background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 1rem 1.25rem 1.1rem; margin-bottom: .8rem;
  backdrop-filter: blur(6px); transition: border-color .15s, transform .15s;
}
.stApp .ss-result:hover { border-color: var(--accent); transform: translateY(-1px); }
.stApp a.ss-rtitle {
  display: block; font-family: var(--serif) !important; font-size: 1.22rem;
  font-weight: 700; color: var(--text) !important; text-decoration: none !important;
}
.stApp a.ss-rtitle:hover { color: var(--accent) !important; }
.stApp .ss-snippet { color: #c3cadf; font-size: .95rem; line-height: 1.6; margin: .4rem 0 .8rem; }
.stApp .ss-bar { height: 4px; background: var(--line); border-radius: 4px; overflow: hidden; }
.stApp .ss-bar div { height: 100%; background: linear-gradient(90deg, #ff8a4c, #ffcf70); }
.stApp .ss-hint { color: var(--muted); font-size: .9rem; margin-top: 1.2rem; }
</style>
"""


@st.cache_data
def build_css():
    css = CSS_TEMPLATE
    css = css.replace("__STARS__", make_starfield())
    css = css.replace("__TWINKLE__", make_twinkle())
    css = css.replace("__GALAXY__", make_galaxy())
    return css


st.markdown(build_css(), unsafe_allow_html=True)


# ---------- page helpers ----------

def esc(text):
    """Make text safe to place inside HTML."""
    return html.escape(text).replace("$", "&#36;")


def overview_card(groups):
    paras = "".join(
        f'<div class="ss-para">{esc(" ".join(sentences))}<span class="ss-cite">[{n}]</span></div>'
        for n, (doc, sentences) in enumerate(groups, 1)
    )
    chips = "".join(
        f'<span class="ss-chip"><b>{n}</b>{esc(doc)}</span>'
        for n, (doc, _) in enumerate(groups, 1)
    )
    return (
        '<div class="ss-overview">'
        '<div class="ss-label">✨ Overview</div>'
        f'{paras}'
        f'<div class="ss-chips">{chips}</div>'
        '<div class="ss-note">Built from the most relevant sentences of the top matching '
        'articles. No AI model is used.</div>'
        '</div>'
    )


def result_card(doc, snippet, pct):
    url = "https://en.wikipedia.org/wiki/" + quote(doc.replace(" ", "_"))
    return (
        '<div class="ss-result">'
        f'<a class="ss-rtitle" href="{url}" target="_blank">{esc(doc)}</a>'
        f'<div class="ss-snippet">{esc(snippet)}</div>'
        f'<div class="ss-bar"><div style="width:{pct:.0f}%"></div></div>'
        '</div>'
    )


@st.cache_resource
def load_index():
    index, doc_lengths = build_index()
    return index, doc_lengths, {}  # third item remembers queries already fetched


index, doc_lengths, fetched = load_index()

st.markdown(
    '<div class="ss-galaxy"><div></div></div>'
    '<div class="ss-shoot s1"></div><div class="ss-shoot s2"></div><div class="ss-shoot s3"></div>'
    '<div class="ss-title">Space Search<span>.</span></div>'
    '<div class="ss-tag">Ask anything about space. Answers drawn from Wikipedia.</div>'
    f'<div class="ss-stats">{len(doc_lengths)} articles &nbsp;·&nbsp; '
    f'{len(index):,} words indexed</div>',
    unsafe_allow_html=True,
)

query = st.text_input(
    "Search",
    placeholder="Try: who was the first person on the moon",
    label_visibility="collapsed",
)
live = st.toggle("Fetch new articles from Wikipedia when needed", value=True)

if not query:
    st.markdown(
        '<div class="ss-hint">Try: &nbsp;how do rockets work &nbsp;·&nbsp; '
        'what is a black hole &nbsp;·&nbsp; Voyager 1</div>',
        unsafe_allow_html=True,
    )
else:
    boost = set()
    if live:
        key = query.strip().lower()
        if key not in fetched:
            try:
                with st.spinner("Checking Wikipedia for more articles..."):
                    hits, _added = grow_index(query, index, doc_lengths)
                fetched[key] = hits
            except Exception as e:
                st.warning(f"Could not reach Wikipedia: {e}")
                fetched[key] = []
        boost = set(fetched[key])

    results = search(query, index, doc_lengths, boost_docs=boost)

    if not results:
        st.warning("No results found.")
    else:
        st.markdown(overview_card(make_overview(query, results)), unsafe_allow_html=True)

        st.markdown('<div class="ss-heading">Top results</div>', unsafe_allow_html=True)
        best = results[0][1] or 1
        query_words = tokenize(query)
        for doc, score in results:
            st.markdown(
                result_card(doc, get_snippet(doc, query_words), 100 * score / best),
                unsafe_allow_html=True,
            )

#to run code use command in terminal: venv\Scripts\python.exe -m streamlit run app.py