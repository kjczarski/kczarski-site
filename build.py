#!/usr/bin/env python3
"""Build the site for two languages: English at the root, Polish in /pl/.

Usage:
    python3 build.py

Static pages (index, lessons, workshops) read their body from
parts/_<page>-<lang>.html. The blog is generated from posts/*.md, and each
post may declare:

    ---
    title: My title
    date: 2026-09-21
    lang: en
    pair: counterpart-slug-in-other-language
    ---

    Body in Markdown.

Files starting with an underscore inside posts/ are ignored.
"""

import datetime
import html
import pathlib
import posixpath
import re

ROOT = pathlib.Path(__file__).resolve().parent
POSTS = ROOT / "posts"
PARTS = ROOT / "parts"

LANGS = ["en", "pl"]
LANG_DIR = {"en": "", "pl": "pl/"}
SWITCH_LABEL = {"en": "PL", "pl": "EN"}

# Nav link sets per kind of page, keys refer to page names.
NAV = {
    "index": ["blog"],
    "lessons": ["workshops", "blog"],
    "workshops": ["lessons", "blog"],
    "blog": ["lessons", "workshops"],
    "post": ["blog", "lessons", "workshops"],
}

LABELS = {
    "en": {"lessons": "Lessons", "workshops": "Workshops", "blog": "Blog"},
    "pl": {"lessons": "Lekcje", "workshops": "Warsztaty", "blog": "Blog"},
}

PAGE_TITLES = {
    "en": {
        "index": "Krzysztof Czarski",
        "lessons": "Lessons, Krzysztof Czarski",
        "workshops": "Workshops, Krzysztof Czarski",
        "blog": "Blog, Krzysztof Czarski",
    },
    "pl": {
        "index": "Krzysztof Czarski",
        "lessons": "Lekcje, Krzysztof Czarski",
        "workshops": "Warsztaty, Krzysztof Czarski",
        "blog": "Blog, Krzysztof Czarski",
    },
}

DESC = {
    "en": {
        "index": "Krzysztof (Chris) Czarski: private English lessons and Erasmus+ workshops.",
        "lessons": "Private English lessons and conversation online. Method: talk, correct, talk. CPE and CELTA with grade A.",
        "workshops": "Workshops for Erasmus+ and similar programmes: AI, startups, creative practice, communication, confidence.",
        "blog": "Essays and notes by Krzysztof (Chris) Czarski.",
    },
    "pl": {
        "index": "Krzysztof (Chris) Czarski: prywatne lekcje angielskiego i warsztaty Erasmus+.",
        "lessons": "Prywatne lekcje angielskiego i rozmowy online. Metoda: rozmowa, poprawki, rozmowa. CPE i CELTA z oceną A.",
        "workshops": "Warsztaty dla Erasmus+ i podobnych programów: AI, startupy, praktyka twórcza, komunikacja, pewność siebie.",
        "blog": "Eseje i notatki Krzysztofa (Chrisa) Czarskiego.",
    },
}

FOOTER_TAG = {
    "en": {"index": None, "lessons": "Private English lessons, online",
           "workshops": "Workshops, Erasmus+", "blog": "Blog", "post": "Blog"},
    "pl": {"index": None, "lessons": "Lekcje angielskiego online",
           "workshops": "Warsztaty, Erasmus+", "blog": "Blog", "post": "Blog"},
}

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "pl": ["sty", "lut", "mar", "kwi", "maj", "cze",
           "lip", "sie", "wrz", "paź", "lis", "gru"],
}

SUN_SVG = (
    '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4.5"/>'
    '<path d="M12 2.5v2.5M12 19v2.5M2.5 12h2.5M19 12h2.5M5 5l1.8 1.8M17.2 17.2L19 19M19 5l-1.8 1.8M6.8 17.2L5 19"/></svg>'
)

THEME_INIT = (
    '<script>\n'
    "(function(){var t;try{t=localStorage.getItem('theme')}catch(e){}"
    "if(!t){try{t=matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':''}catch(e){}}"
    "if(t==='dark')document.documentElement.setAttribute('data-theme','dark')})();\n"
    "</script>\n"
)

THEME_HANDLER = (
    '<script>\n'
    "document.getElementById('theme').addEventListener('click',function(){"
    "var h=document.documentElement;"
    "h.hasAttribute('data-theme')?h.removeAttribute('data-theme'):h.setAttribute('data-theme','dark');"
    "try{localStorage.setItem('theme',h.hasAttribute('data-theme')?'dark':'')}catch(e){}})"
    ";\n"
    "</script>\n"
)


def rel(out, target):
    """Relative href from output file to a root-relative target."""
    d = posixpath.dirname(out)
    return posixpath.relpath(target, d) if d else target


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(md):
    out, in_ul = [], False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw in md.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            close_ul()
            continue
        if line.startswith("### "):
            close_ul()
            out.append("<h3>%s</h3>" % inline(line[4:]))
        elif line.startswith("## "):
            close_ul()
            out.append("<h2>%s</h2>" % inline(line[3:]))
        elif line.startswith("# "):
            close_ul()
            out.append("<h2>%s</h2>" % inline(line[2:]))
        elif re.match(r"^!\[", line):
            m = re.match(r"^!\[(.*?)\]\((.*?)\)$", line)
            out.append('<img src="%s" alt="%s" loading="lazy">' % (m.group(2), m.group(1)))
        elif re.match(r"^[-*] ", line):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>%s</li>" % inline(line[2:]))
        else:
            close_ul()
            out.append("<p>%s</p>" % inline(line))
    close_ul()
    return "\n        ".join(out)


def parse(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = m.group(2)
    title = meta.get("title") or path.stem
    date = meta.get("date", "")
    lang = meta.get("lang", "en")
    pair = meta.get("pair", "")
    return title, date, body.strip(), lang, pair


def pretty_date(lang, iso):
    try:
        d = datetime.date.fromisoformat(iso)
        day = str(d.day)
        if lang == "pl":
            return "%s %s %d" % (day, MONTHS["pl"][d.month - 1], d.year)
        return "%s %s %d" % (day, MONTHS["en"][d.month - 1], d.year)
    except ValueError:
        return iso


def header(lang, out, kind, keys, post_key=None):
    other = "pl" if lang == "en" else "en"
    if kind == "index":
        switch_target = LANG_DIR[other] + "index.html"
    elif kind == "post" and post_key:
        switch_target = LANG_DIR[other] + "posts/" + post_key + ".html"
    else:
        switch_target = LANG_DIR[other] + kind + ".html"
    links = ['        <a class="xlink" href="%s">%s</a>\n'
             % (rel(out, LANG_DIR[lang] + key + ".html"), LABELS[lang][key])
             for key in keys]
    links.append('        <a class="xlink lang" href="%s">%s</a>\n'
                 % (rel(out, switch_target), SWITCH_LABEL[lang]))
    links.append(
        '        <button type="button" class="theme" id="theme" '
        'aria-label="Toggle dark mode">%s</button>\n' % SUN_SVG
    )
    home = rel(out, LANG_DIR[lang] + "index.html")
    return ('      <a class="brand" href="%s">Krzysztof Czarski</a>\n'
            '      <nav class="topnav">\n%s      </nav>') % (
        home, "".join(links))


def page(lang, title, desc, out, head, main, tagline):
    css = rel(out, "assets/style.css")
    footer = ""
    if tagline:
        footer = (
            "      <footer>\n"
            '        <a href="mailto:kjczarski@gmail.com">kjczarski@gmail.com</a>\n'
            "        <span>%s</span>\n"
            "      </footer>\n"
        ) % tagline
    return (
        "<!doctype html>\n"
        '<html lang="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n"
        '<meta name="description" content="%s">\n'
        '<link rel="stylesheet" href="%s">\n'
        "%s"
        "</head>\n"
        "<body>\n"
        '  <div class="wrap">\n'
        "    <header class=\"top\">\n"
        "%s\n"
        "    </header>\n"
        "    <main>\n"
        "%s\n"
        "%s"
        "    </main>\n"
        "%s"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    ) % (lang, title, desc, css, THEME_INIT, head, main, footer, THEME_HANDLER)


def build():
    POSTS.mkdir(exist_ok=True)
    (ROOT / "pl" / "posts").mkdir(parents=True, exist_ok=True)
    for old in list(POSTS.glob("*.html")) + list((ROOT / "pl" / "posts").glob("*.html")):
        old.unlink()

    entries = []
    for path in sorted(POSTS.glob("*.md")):
        if path.name.startswith("_"):
            continue
        title, date, body, lang, pair = parse(path)
        slug = re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-")
        entries.append({"slug": slug, "title": title, "date": date,
                        "body": body, "lang": lang, "pair": pair})

    for lang in LANGS:
        d = LANG_DIR[lang]
        posts = [e for e in entries if e["lang"] == lang]
        posts.sort(key=lambda e: (e["date"], e["title"].lower()), reverse=True)

        # Static pages from parts/ fragments (index, lessons, workshops).
        for page_name in ("index", "lessons", "workshops"):
            if page_name == "blog":
                continue
            frag = PARTS / ("_%s-%s.html" % (page_name, lang))
            main = frag.read_text(encoding="utf-8").strip()
            out = d + page_name + ".html"
            (ROOT / out).write_text(
                page(lang, PAGE_TITLES[lang][page_name], DESC[lang][page_name],
                     out,
                     header(lang, out, page_name, NAV[page_name]),
                     main, FOOTER_TAG[lang][page_name]),
                encoding="utf-8",
            )

        # Post pages.
        for e in posts:
            out = d + "posts/" + e["slug"] + ".html"
            post_key = e["pair"] or None
            main = (
                '      <div class="hero">\n'
                "        <h1>%s</h1>\n"
                "      </div>\n"
                '      <p class="meta">%s</p>\n'
                '      <section class="post">\n'
                "        %s\n"
                "      </section>"
            ) % (html.escape(e["title"]), pretty_date(lang, e["date"]), md_to_html(e["body"]))
            (ROOT / out).write_text(
                page(lang, e["title"] + ", Krzysztof Czarski", DESC[lang]["blog"], out,
                     header(lang, out, "post", NAV["post"], post_key),
                     main, FOOTER_TAG[lang]["post"]),
                encoding="utf-8",
            )

        # Blog listing.
        if posts:
            items = "".join(
                '          <li><a href="posts/%s.html"><span class="ptitle">%s</span>'
                '<span class="date">%s</span></a></li>\n'
                % (e["slug"], html.escape(e["title"]), pretty_date(lang, e["date"]))
                for e in posts
            )
            listing = '        <ul class="posts">\n%s        </ul>' % items
        else:
            listing = '        <p class="empty">No posts yet.</p>'
        main = ('      <div class="hero">\n        <h1>Blog</h1>\n      </div>\n\n'
                '      <section>\n%s\n      </section>' % listing)
        out = d + "blog.html"
        (ROOT / out).write_text(
            page(lang, PAGE_TITLES[lang]["blog"], DESC[lang]["blog"], out,
                 header(lang, out, "blog", NAV["blog"]),
                 main, FOOTER_TAG[lang]["blog"]),
            encoding="utf-8",
        )

    print("Built %d post(s) in %d language(s)." % (len(entries), len(LANGS)))


if __name__ == "__main__":
    build()