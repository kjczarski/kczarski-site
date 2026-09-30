#!/usr/bin/env python3
"""Build the site for two languages: English at the root, Polish in /pl/.

Usage:
    python3 build.py

Static pages (index, lessons, workshops, cv) read their body from
parts/_<page>-<lang>.html. A page with no <lang> fragment yet falls back to
the English one, so pl/cv.html is an untranslated copy until parts/_cv-pl.html
exists. The blog is generated from posts/*.md, and each post may declare:

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

SITE_URL = "https://krzysztofczarski.com"
OG_SITE_NAME = "Krzysztof Czarski"
OG_IMAGE = "assets/img/02-teaching-jordan.jpg"
LOCALE = {"en": "en_GB", "pl": "pl_PL"}

LANGS = ["en", "pl"]
LANG_DIR = {"en": "", "pl": "pl/"}
SWITCH_LABEL = {"en": "PL", "pl": "EN"}

# Nav link sets per kind of page, keys refer to page names.
NAV = {
    "index": [],
    "lessons": ["workshops", "blog", "cv"],
    "workshops": ["lessons", "blog", "cv"],
    "blog": ["lessons", "workshops", "cv"],
    "cv": ["lessons", "workshops", "blog"],
    "post": ["blog", "lessons", "workshops", "cv"],
}

LABELS = {
    "en": {"lessons": "Lessons", "workshops": "Workshops", "blog": "Blog", "cv": "CV"},
    "pl": {"lessons": "Lekcje", "workshops": "Warsztaty", "blog": "Blog", "cv": "CV"},
}

PAGE_TITLES = {
    "en": {
        "index": "Krzysztof Czarski",
        "lessons": "Lessons, Krzysztof Czarski",
        "workshops": "Workshops, Krzysztof Czarski",
        "blog": "Blog, Krzysztof Czarski",
        "cv": "CV, Krzysztof Czarski",
    },
    "pl": {
        "index": "Krzysztof Czarski",
        "lessons": "Lekcje, Krzysztof Czarski",
        "workshops": "Warsztaty, Krzysztof Czarski",
        "blog": "Blog, Krzysztof Czarski",
        "cv": "CV, Krzysztof Czarski",
    },
}

DESC = {
    "en": {
        "index": "Krzysztof (Chris) Czarski: private English lessons and Erasmus+ workshops.",
        "lessons": "Private English lessons and conversation online. Method: talk, correct, talk. CPE and CELTA with grade A.",
        "workshops": "Workshops for Erasmus+ and similar programmes: AI, startups, creative practice, communication, confidence.",
        "blog": "Essays and notes by Krzysztof (Chris) Czarski.",
        "cv": "CV of Krzysztof (Chris) Czarski: teaching, workshop facilitation, translation, and what he has done.",
    },
    "pl": {
        "index": "Krzysztof (Chris) Czarski: prywatne lekcje angielskiego i warsztaty Erasmus+.",
        "lessons": "Prywatne lekcje angielskiego i rozmowy online. Metoda: rozmowa, poprawki, rozmowa. CPE i CELTA z oceną A.",
        "workshops": "Warsztaty dla Erasmus+ i podobnych programów: AI, startupy, praktyka twórcza, komunikacja, pewność siebie.",
        "blog": "Eseje i notatki Krzysztofa (Chrisa) Czarskiego.",
        "cv": "CV of Krzysztof (Chris) Czarski: teaching, workshop facilitation, translation, and what he has done.",
    },
}

FOOTER_TAG = {
    "en": {"index": None, "lessons": "Private English lessons, online",
           "workshops": "Workshops, Erasmus+", "blog": "Blog", "cv": "CV", "post": "Blog"},
    "pl": {"index": None, "lessons": "Lekcje angielskiego online",
           "workshops": "Warsztaty, Erasmus+", "blog": "Blog", "cv": "CV", "post": "Blog"},
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
    "if(t==='dark')document.documentElement.setAttribute('data-theme','dark');"
    "})();\n"
    "</script>\n"
)

THEME_HANDLER = (
    '<script>\n'
    "document.getElementById('theme').addEventListener('click',function(){"
    "var h=document.documentElement;"
    "h.hasAttribute('data-theme')?h.removeAttribute('data-theme'):h.setAttribute('data-theme','dark');"
    "try{localStorage.setItem('theme',h.hasAttribute('data-theme')?'dark':'light')}catch(e){}})"
    ";\n"
    "</script>\n"
)


def rel(out, target):
    """Relative href from output file to a root-relative target."""
    d = posixpath.dirname(out)
    return posixpath.relpath(target, d) if d else target


def abs_url(out):
    """Absolute URL for an output path. index.html becomes a trailing-slash URL."""
    p = out[:-len("index.html")] if out.endswith("index.html") else out
    return SITE_URL + "/" + p


def alt_map(alts):
    """Sort alternates so en comes first, then pl."""
    return sorted(alts, key=lambda a: 0 if a[0] == "en" else 1)


def seo(lang, out, title, desc, kind, alts):
    """Canonical URL, hreflang alternates, Open Graph and Twitter card tags."""
    url = abs_url(out)
    alts = alt_map(alts)
    t = html.escape(title, quote=True)
    d = html.escape(desc, quote=True)
    img = SITE_URL + "/" + OG_IMAGE
    lines = ['    <link rel="canonical" href="%s">' % url]
    for code, href in alts:
        lines.append('    <link rel="alternate" hreflang="%s" href="%s">' % (code, href))
    for code, href in alts:
        if code == "en":
            lines.append('    <link rel="alternate" hreflang="x-default" href="%s">' % href)
            break
    lines += [
        '    <meta property="og:type" content="%s">' % ("article" if kind == "post" else "website"),
        '    <meta property="og:site_name" content="%s">' % OG_SITE_NAME,
        '    <meta property="og:title" content="%s">' % t,
        '    <meta property="og:description" content="%s">' % d,
        '    <meta property="og:url" content="%s">' % url,
        '    <meta property="og:locale" content="%s">' % LOCALE[lang],
        '    <meta property="og:image" content="%s">' % img,
        '    <meta property="og:image:width" content="1367">',
        '    <meta property="og:image:height" content="898">',
    ]
    for code, _href in alts:
        if code != lang:
            lines.append('    <meta property="og:locale:alternate" content="%s">' % LOCALE[code])
    lines += [
        '    <meta name="twitter:card" content="summary_large_image">',
        '    <meta name="twitter:title" content="%s">' % t,
        '    <meta name="twitter:description" content="%s">' % d,
        '    <meta name="twitter:image" content="%s">' % img,
    ]
    return "\n".join(lines) + "\n"


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"==(.+?)==", r'<mark class="hl">\1</mark>', s)
    return s


def md_to_html(md):
    out, in_ul = [], False
    seen_ids = {}

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def heading_id(text):
        s = re.sub(r"[*_`\[\]()]", "", text).lower()
        s = re.sub(r"['’]", "", s)
        for src, dst in (("ą", "a"), ("ć", "c"), ("ę", "e"), ("ł", "l"),
                         ("ń", "n"), ("ó", "o"), ("ś", "s"), ("ź", "z"),
                         ("ż", "z")):
            s = s.replace(src, dst)
        base = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
        n = seen_ids.get(base, 0)
        seen_ids[base] = n + 1
        return base if not n else "%s-%d" % (base, n + 1)

    for raw in md.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            close_ul()
            continue
        if line.startswith("### "):
            close_ul()
            out.append('<h3 id="%s">%s</h3>' % (heading_id(line[4:]), inline(line[4:])))
        elif line.startswith("## "):
            close_ul()
            out.append('<h2 id="%s">%s</h2>' % (heading_id(line[3:]), inline(line[3:])))
        elif line.startswith("# "):
            close_ul()
            out.append('<h2 id="%s">%s</h2>' % (heading_id(line[2:]), inline(line[2:])))
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
    elif kind == "post":
        # No translation yet: send the reader to the blog listing, not a dead post URL.
        switch_target = LANG_DIR[other] + "blog.html"
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


def page(lang, title, desc, out, seo_block, head, main, tagline):
    css = rel(out, "assets/style.css")
    fonts = rel(out, "assets/fonts/site.css")
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
        "%s"
        '<link rel="stylesheet" href="%s">\n'
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
    ) % (lang, html.escape(title), html.escape(desc, quote=True),
         seo_block, fonts, css, THEME_INIT, head, main, footer, THEME_HANDLER)


def write_sitemap(entries):
    """sitemap.xml with hreflang alternates and lastmod for dated posts."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
           '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for e in entries:
        out.append("  <url>")
        out.append("    <loc>%s</loc>" % e["loc"])
        for code, href in e["alts"]:
            out.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (code, href))
        for code, href in e["alts"]:
            if code == "en":
                out.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % href)
                break
        if e["lastmod"]:
            out.append("    <lastmod>%s</lastmod>" % e["lastmod"])
        out.append("  </url>")
    out.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_robots():
    (ROOT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: %s/sitemap.xml\n" % SITE_URL,
        encoding="utf-8",
    )


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

    slugs = {e["slug"] for e in entries}
    sitemap = []

    def record(out, alts, lastmod=""):
        sitemap.append({"loc": abs_url(out), "alts": alt_map(alts), "lastmod": lastmod})

    for lang in LANGS:
        d = LANG_DIR[lang]
        posts = [e for e in entries if e["lang"] == lang]
        posts.sort(key=lambda e: (e["date"], e["title"].lower()), reverse=True)

        # Static pages from parts/ fragments (index, lessons, workshops, cv).
        for page_name in ("index", "lessons", "workshops", "cv"):
            frag = PARTS / ("_%s-%s.html" % (page_name, lang))
            if not frag.exists():
                # No translation yet: fall back to the English fragment.
                frag = PARTS / ("_%s-en.html" % page_name)
            main = frag.read_text(encoding="utf-8").strip()
            out = d + page_name + ".html"
            main = main.replace("{{a}}", rel(out, "assets") + "/")
            # Only advertise a language that actually has its own fragment,
            # so an untranslated fallback is never claimed to be a translation.
            alts = [(l2, abs_url(LANG_DIR[l2] + page_name + ".html")) for l2 in LANGS
                    if (PARTS / ("_%s-%s.html" % (page_name, l2))).exists()]
            if (lang, abs_url(out)) not in alts:
                alts.append((lang, abs_url(out)))
            record(out, alts)
            (ROOT / out).write_text(
                page(lang, PAGE_TITLES[lang][page_name], DESC[lang][page_name],
                     out,
                     seo(lang, out, PAGE_TITLES[lang][page_name], DESC[lang][page_name],
                         page_name, alts),
                     header(lang, out, page_name, NAV[page_name]),
                     main, FOOTER_TAG[lang][page_name]),
                encoding="utf-8",
            )

        # Post pages.
        for e in posts:
            out = d + "posts/" + e["slug"] + ".html"
            post_key = e["pair"] or None
            alts = [(lang, abs_url(out))]
            if post_key and post_key in slugs:
                other = "pl" if lang == "en" else "en"
                alts.append((other, abs_url(LANG_DIR[other] + "posts/" + post_key + ".html")))
            record(out, alts, e["date"])
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
                     seo(lang, out, e["title"] + ", Krzysztof Czarski", DESC[lang]["blog"],
                         "post", alts),
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
        alts = [(l2, abs_url(LANG_DIR[l2] + "blog.html")) for l2 in LANGS]
        record(out, alts)
        (ROOT / out).write_text(
            page(lang, PAGE_TITLES[lang]["blog"], DESC[lang]["blog"], out,
                 seo(lang, out, PAGE_TITLES[lang]["blog"], DESC[lang]["blog"], "blog", alts),
                 header(lang, out, "blog", NAV["blog"]),
                 main, FOOTER_TAG[lang]["blog"]),
            encoding="utf-8",
        )

    write_sitemap(sitemap)
    write_robots()
    print("Built %d post(s) in %d language(s)." % (len(entries), len(LANGS)))
    print("Sitemap: %d URL(s) at sitemap.xml" % len(sitemap))


if __name__ == "__main__":
    build()