"""Lot 12 — Assemblage HTML du dashboard (maquette §3 + §5).

Extrait de ``build_dashboard.py`` : page autonome (CSS inline, PNG en
base64, liens relatifs), <details> fermes sauf le verdict. HTML produit
strictement identique a l'original.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

try:
    from scripts.dashboard_content import BLOCKS, CSS_INLINE, READINGS, SOURCES_URLS
except ImportError:  # execution directe : python scripts/xxx.py
    from dashboard_content import BLOCKS, CSS_INLINE, READINGS, SOURCES_URLS


def _rel(href_target: Path, out_parent: Path) -> str:
    try:
        return os.path.relpath(href_target, out_parent).replace(os.sep, "/")
    except ValueError:
        return href_target.name


def _render_head(ctx: dict) -> list[str]:
    """En-tete : titre, claim, verdict, fenetre, pulls, sommaire."""
    esc = html.escape
    return [
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>NEAR Intents, indicateur avancé de l'usage réel ?</title>",
        "<style>",
        CSS_INLINE,
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>NEAR Intents, indicateur avancé de l'usage réel ?</h1>",
        f"<p>{esc(ctx['claim'])}</p>",
        f"<p><span class=\"badge {ctx['verdict']['badge_class']}\">"
        f"{esc(ctx['verdict']['badge_label'])}</span> "
        f"Fenêtre : {esc(ctx['dmin'])} → {esc(ctx['dmax'])} ({ctx['n']} jours)</p>",
        f"<p class=\"meta\">Pulls : BigQuery {esc(ctx['pull_bq'])} · Intents "
        f"{esc(ctx['pull_intents'])} · MAX(block_date) = {esc(ctx['maxbd'])} · "
        f"Prix : {esc(ctx['price'])} · Généré le {esc(ctx['generated_at'])} (UTC)</p>",
        "<nav class=\"toc\">" + " ".join(
            f"<a href=\"#{b['id']}\">{esc(b['toc'])}</a>" for b in BLOCKS
        ) + "</nav>",
        "</header>",
    ]


def _render_verdict(ctx: dict) -> list[str]:
    """Bloc 0 : verdict (seul <details> ouvert)."""
    esc = html.escape
    return [
        '<section class="card verdict" id="verdict">',
        "<h2>Verdict</h2>",
        "<details open>",
        f"<summary>Verdict et seuil d'infirmation ({esc(ctx['verdict']['source'])})</summary>",
        f"<p><strong>Sur {esc(ctx['dmin'])} → {esc(ctx['dmax'])}, "
        f"{esc(ctx['verdict']['phrase'])}</strong></p>",
        f"<p>Seuil qui ferait changer d'avis : {esc(ctx['verdict']['seuil'])}</p>",
        "<p class=\"qlinks\">" + " · ".join(
            f"<a href=\"{esc(h)}\">{esc(label)}</a>" for label, h in ctx["verdict_links"]
        ) + "</p>",
        "</details>",
        "</section>",
    ]


def _render_block(ctx: dict, b: dict, i: int) -> list[str]:
    """Une section : figures, tableau methode, phrase, requete, lecture."""
    esc = html.escape
    parts: list[str] = []
    cls = "card warn" if b.get("warn") else "card"
    parts.append(f"<section class=\"{cls}\" id=\"{esc(b['id'])}\">")
    parts.append(f"<h2>{i}. {esc(b['title'])}</h2>")
    for png, alt, caption in b["figures"]:
        parts.append("<figure>")
        parts.append(
            f"<img class=\"chart\" src=\"data:image/png;base64,{ctx['images'][png]}\" "
            f"alt=\"{esc(alt)}\">"
        )
        parts.append(f"<figcaption>{esc(caption)}</figcaption>")
        parts.append("</figure>")
    if b["id"] == "methode":
        parts.append("<table class=\"fresh\">")
        for head, cell in ctx["fresh_rows"]:
            parts.append(f"<tr><th>{esc(head)}</th><td>{esc(cell)}</td></tr>")
        parts.append("</table>")
        parts.append("<pre>pip install -r requirements.txt &amp;&amp; python rebuild.py\n"
                     "(sans .env : rebuild via data/raw/ — mêmes chiffres)</pre>")
    parts.append(f"<p class=\"fact\"><strong>{esc(ctx['phrases'][b['id']])}</strong></p>")
    parts.append("<details>")
    parts.append("<summary>Voir la requête exacte</summary>")
    for label, texte in ctx["details"][b["id"]]:
        parts.append(f"<h3>{esc(label)}</h3>")
        parts.append(f"<pre>{esc(texte.rstrip())}</pre>")
    if ctx["qlinks"][b["id"]]:
        parts.append("<p class=\"qlinks\">" + " ".join(
            f"<a href=\"{esc(h)}\">{esc(label)}</a>"
            for label, h in ctx["qlinks"][b["id"]]
        ) + "</p>")
    parts.append("</details>")
    parts.append(f"<p class=\"reading\">{esc(READINGS[b['id']])}</p>")
    parts.append("</section>")
    return parts


def _render_footer(ctx: dict) -> list[str]:
    """Pied de page : rappel claim, verdict, sources, regle de preuve."""
    esc = html.escape
    return [
        "<footer>",
        f"<p>{esc(ctx['claim'])}</p>",
        f"<p>Verdict : <span class=\"badge {ctx['verdict']['badge_class']}\">"
        f"{esc(ctx['verdict']['badge_label'])}</span> — Seuil : {esc(ctx['verdict']['seuil'])}</p>",
        "<nav class=\"src\">Sources : " + " ".join(
            f"<a href=\"{esc(url)}\">{esc(label)}</a>" for label, url in SOURCES_URLS
        ) + "</nav>",
        "<p class=\"meta\">Chaque chiffre pointe vers une requête ou un log. "
        "JWT jamais commité (.env.example seul).</p>",
        "</footer>",
        "</body>",
        "</html>",
        "",
    ]


def build_html(ctx: dict) -> str:
    """Assemble la page autonome : CSS inline, PNG en base64, liens relatifs.

    Tous les <details> sont fermés sauf celui du verdict (<details open>).
    """
    parts: list[str] = []
    parts += _render_head(ctx)
    parts += _render_verdict(ctx)
    for i, b in enumerate(BLOCKS, start=1):
        parts += _render_block(ctx, b, i)
    parts += _render_footer(ctx)
    page = "\n".join(parts)
    # Garde-fou : aucune dépendance réseau (les <a href> de navigation sont
    # autorisés : ils ne chargent rien tant qu'on ne clique pas).
    for bad in ('src="http', "src='http", "<link", "<script", "@import", "url("):
        if bad in page:
            raise ValueError(f"Garde-fou réseau : motif interdit {bad!r} dans le HTML.")
    return page
