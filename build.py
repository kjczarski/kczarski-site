#!/usr/bin/env python3
"""Build the blog from posts/*.md into blog.html + posts/<slug>.html.

Usage:
    python3 build.py

Each post is a Markdown file in posts/ with a small front matter header:

    ---
    title: My title
    date: 2026-09-21
    ---

    Body in Markdown.
"""

import datetime
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
POSTS = ROOT / "posts"

HEADER = """      <a class="brand" href="{home}">Krzysztof Czarski</a>
      <nav class="topnav">
{links}      </nav>"""


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
    return title, date, body.strip()


def pretty_date(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        return d.strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return iso


def page(title, header, main, prefix=""):
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n"
        '<link rel="stylesheet" href="%sassets/style.css">\n'
        "</head>\n"
        "<body>\n"
        '  <div class="wrap">\n'
        '    <header class="top">\n'
        "%s\n"
        "    </header>\n"
        "    <main>\n"
        "%s\n"
        "      <footer>\n"
        '        <a href="mailto:kjczarski@gmail.com">kjczarski@gmail.com</a>\n'
        "        <span>Blog</span>\n"
        "      </footer>\n"
        "    </main>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    ) % (title, prefix, header, main)


def build():
    POSTS.mkdir(exist_ok=True)
    entries = []
    for path in sorted(POSTS.glob("*.md")):
        if path.name.startswith("_"):
            continue
        title, date, body = parse(path)
        slug = re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-")
        entries.append({"slug": slug, "title": title, "date": date, "body": body})

    entries.sort(key=lambda e: e["date"], reverse=True)

    for e in entries:
        header = HEADER.format(
            home="../index.html",
            links="".join(
                '        <a class="xlink" href="../%s">%s</a>\n' % (href, label)
                for href, label in [
                    ("blog.html", "Blog"),
                    ("lessons.html", "Lessons"),
                    ("workshops.html", "Workshops"),
                ]
            ),
        )
        main = (
            '      <div class="hero">\n'
            "        <h1>%s</h1>\n"
            "      </div>\n"
            '      <p class="meta">%s</p>\n'
            '      <section class="post">\n'
            "        %s\n"
            "      </section>"
        ) % (html.escape(e["title"]), pretty_date(e["date"]), md_to_html(e["body"]))
        (POSTS / (e["slug"] + ".html")).write_text(
            page(e["title"] + ", Krzysztof Czarski", header, main, prefix="../"), encoding="utf-8"
        )

    header = HEADER.format(
        home="index.html",
        links="".join(
            '        <a class="xlink" href="%s">%s</a>\n' % (href, label)
            for href, label in [("lessons.html", "Lessons"), ("workshops.html", "Workshops")]
        ),
    )
    if entries:
        items = "".join(
            '          <li><a href="posts/%s.html"><span class="ptitle">%s</span>'
            '<span class="date">%s</span></a></li>\n'
            % (e["slug"], html.escape(e["title"]), pretty_date(e["date"]))
            for e in entries
        )
        listing = '        <ul class="posts">\n%s        </ul>' % items
    else:
        listing = '        <p class="empty">No posts yet.</p>'
    main = '      <div class="hero">\n        <h1>Blog</h1>\n      </div>\n\n      <section>\n%s\n      </section>' % listing
    (ROOT / "blog.html").write_text(page("Blog, Krzysztof Czarski", header, main), encoding="utf-8")

    print("Built %d post(s)." % len(entries))


if __name__ == "__main__":
    build()
