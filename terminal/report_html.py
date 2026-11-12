"""Rapport de mission en HTML : un seul fichier, sans dépendance, prêt à imprimer en PDF depuis le navigateur.

Tout le texte est échappé : les sorties de commande viennent de la cible et peuvent contenir du HTML.
"""
import base64
import html
from pathlib import Path

from terminal import __version__

_LOGO = Path(__file__).resolve().parent.parent / "Images" / "Nebula_Logo.png"
_SEV = {"critique": "#b42318", "haute": "#d9480f", "moyenne": "#b7791f", "basse": "#2f6f4f", "info": "#4a5568"}

_CSS = """
*{box-sizing:border-box} body{margin:0;font:14px/1.55 "Segoe UI",Inter,system-ui,sans-serif;color:#1a1d21;background:#f4f5f7}
main{max-width:960px;margin:0 auto;background:#fff;padding:48px 56px}
header{display:flex;align-items:center;gap:20px;border-bottom:2px solid #1a1d21;padding-bottom:20px;margin-bottom:28px}
header img{height:64px} header h1{margin:0;font-size:26px} header p{margin:2px 0 0;color:#5b616b}
h2{font-size:18px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid #d8dbe0;break-after:avoid}
h3{font-size:15px;margin:22px 0 6px;break-after:avoid}
table{width:100%;border-collapse:collapse;margin:8px 0 16px;font-size:13px} th,td{text-align:left;padding:7px 9px;border-bottom:1px solid #e4e6ea;vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#5b616b;background:#f7f8fa}
.kv td:first-child{width:220px;color:#5b616b}
.sev{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:12px;font-weight:600;white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:12px 0 8px} .card{border:1px solid #e4e6ea;border-radius:8px;padding:10px;text-align:center}
.card b{display:block;font-size:24px} .card span{font-size:12px;color:#5b616b}
.finding{border:1px solid #e4e6ea;border-left:4px solid;border-radius:6px;padding:12px 16px;margin:12px 0;break-inside:avoid}
.finding p{margin:6px 0} code,pre{font:12px "Cascadia Code",Consolas,monospace} code{background:#f1f3f5;padding:1px 5px;border-radius:4px}
pre{background:#f7f8fa;border:1px solid #e4e6ea;border-radius:6px;padding:10px;white-space:pre-wrap;word-break:break-word;max-height:none}
.ok{color:#2f6f4f;font-weight:600} .bad{color:#b42318;font-weight:600} .muted{color:#5b616b;font-size:12px}
footer{margin-top:40px;padding-top:12px;border-top:1px solid #d8dbe0;color:#5b616b;font-size:12px}
@media print{body{background:#fff} main{padding:0;max-width:none} @page{margin:16mm} a{color:inherit}}
"""


def _e(text) -> str:
    return html.escape(str(text))


def _logo() -> str:
    if not _LOGO.is_file():
        return ""
    return f'<img alt="" src="data:image/png;base64,{base64.b64encode(_LOGO.read_bytes()).decode()}">'


def _sev(level: str) -> str:
    return f'<span class="sev" style="background:{_SEV.get(level, "#4a5568")}">{_e(level)}</span>'


def render(m, items, runs, refused, found, compliance, ok, detail, max_lines=60) -> str:
    from terminal.mission import CATEGORIES, SEVERITY_ORDER

    period = f"{items[0]['time']} → {items[-1]['time']}" if items else "aucune activité"
    counts = {s: sum(1 for f in found if f["severity"] == s) for s in SEVERITY_ORDER}
    out = [f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Rapport — {_e(m['name'])}</title>",
           f"<style>{_CSS}</style></head><body><main>",
           f"<header>{_logo()}<div><h1>Rapport de mission — {_e(m['name'])}</h1>",
           f"<p>Nebula Terminal Custom {__version__} · généré à partir du registre de preuves</p></div></header>",
           "<table class='kv'>",
           f"<tr><td>Créée le</td><td>{_e(m['created'])}{' par ' + _e(m['owner']) if m.get('owner') else ''}</td></tr>",
           f"<tr><td>Périmètre autorisé</td><td>{_e(', '.join(m['scope']))}</td></tr>",
           f"<tr><td>Période</td><td>{_e(period)}</td></tr>",
           f"<tr><td>Commandes</td><td>{len(runs)} dont {len(refused)} refusées (hors périmètre)</td></tr>",
           f"<tr><td>Intégrité du registre</td><td class='{'ok' if ok else 'bad'}'>{'intacte' if ok else 'ANOMALIE'} — {_e(detail)}</td></tr>",
           "</table>"]

    out.append("<h2>Synthèse</h2><div class='cards'>")
    out += [f"<div class='card' style='border-top:3px solid {_SEV[s]}'><b>{counts[s]}</b><span>{s}</span></div>" for s in SEVERITY_ORDER]
    out.append("</div>")
    if found:
        out.append("<table><tr><th>Gravité</th><th>Constat</th><th>Catégorie</th><th>État</th><th>Registre</th></tr>")
        out += [f"<tr><td>{_sev(f['severity'])}</td><td>{_e(f['title'])}</td><td>{_e(CATEGORIES[f['category']][0])}</td>"
                f"<td>{_e(f['state'])}</td><td>n°{f['n']}</td></tr>" for f in found]
        out.append("</table><h2>Constats détaillés</h2>")
        for f in found:
            out.append(f"<div class='finding' style='border-left-color:{_SEV.get(f['severity'], '#4a5568')}'>"
                       f"<h3>{_sev(f['severity'])} {_e(f['title'])}</h3>"
                       f"<p><b>Preuve :</b> {_e(f['evidence'])}</p><p><b>Correction :</b> {_e(f['recommendation'])}</p>")
            if f["command"]:
                out.append(f"<p class='muted'>Vérifier la correction : <code>{_e(f['command'])}</code> — corrigé quand "
                           f"« {_e(f['expect'])} » n'apparaît plus. État : <b>{_e(f['state'])}</b>"
                           f"{' (' + _e(f['checked']) + ')' if f['checked'] else ''}</p>")
            out.append("</div>")
    else:
        out.append("<p>Aucun constat enregistré.</p>")

    if compliance:
        out.append("<h2>Conformité</h2><p class='muted'>Repères : ce que chaque famille de constats touche dans les "
                   "référentiels. Ce n'est pas un audit de conformité.</p>")
        out.append("<table><tr><th>Famille</th><th>Constats</th><th>nLPD</th><th>ISO/IEC 27001:2022</th><th>NIS2</th><th>En clair</th></tr>")
        out += [f"<tr><td>{_e(c['label'])}</td><td>{c['count']}</td><td>art. 8</td><td>{_e(c['iso'])}</td>"
                f"<td>{_e(c['nis2'])}</td><td>{_e(c['plain'])}</td></tr>" for c in compliance]
        out.append("</table>")

    out.append("<h2>Chronologie</h2><table><tr><th>N°</th><th>Heure</th><th>Source</th><th>Commande</th><th>Statut</th><th>Durée</th></tr>")
    out += [f"<tr><td>{e['n']}</td><td>{_e(e['time'])}</td><td>{_e(e['source'])}</td><td><code>{_e(e['command'])}</code></td>"
            f"<td>{_e(e['status'])}</td><td>{e['duration']} s</td></tr>" for e in items]
    out.append("</table>")
    if refused:
        out.append("<h2>Tentatives hors périmètre</h2><p class='muted'>Refusées par le terminal : rien n'a été envoyé.</p><ul>")
        out += [f"<li>n°{e['n']} — {_e(e['time'])} — <code>{_e(e['command'])}</code></li>" for e in refused]
        out.append("</ul>")

    out.append("<h2>Résultats</h2>")
    for e in runs:
        if e["status"] == "refusé" or not e["output"].strip():
            continue
        lines = e["output"].splitlines()
        more = f"\n… ({len(lines) - max_lines} lignes de plus dans le registre)" if len(lines) > max_lines else ""
        out.append(f"<h3>n°{e['n']} — <code>{_e(e['command'])}</code></h3><p class='muted'>{_e(e['time'])} · "
                   f"{_e(e['status'])} · {e['duration']} s</p><pre>{_e(chr(10).join(lines[:max_lines]) + more)}</pre>")
    out.append(f"<footer>Empreinte du registre : {_e(detail)}. Pour une preuve opposable, communiquez cette empreinte "
               "au client séparément (mail, rapport signé).</footer></main></body></html>")
    return "\n".join(out)
