"""Affichage texte des « blocs » de résultat — le même format que le dashboard (NebulaGui/tools.py).

Un outil qui renvoie des blocs s'affiche donc à l'identique dans le terminal et dans le navigateur.
"""
import json
import threading

local = threading.local()  # .json = afficher en JSON (option --json) ; .json_used = l'outil l'a honorée

_MARK = {"ok": "[+]", "warn": "[!]", "bad": "[!!]", "info": "[*]"}
_LEVEL_COLOR = {"ok": "\033[92m", "warn": "\033[93m", "bad": "\033[91m"}  # statuts : mêmes couleurs dans tous les thèmes
_CELL = 60


def _cut(text, width=_CELL):
    text = str(text).replace("\n", " ")
    return text if len(text) <= width else text[:width - 1] + "…"


def print_blocks(blocks, max_text_lines=None):
    if getattr(local, "json", False):
        local.json_used = True
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
        return
    from terminal.theme import get_prompt_colors
    c = get_prompt_colors()
    for b in blocks:
        if "notes" in b:
            for level, text in b["notes"]:
                print(f"  {_LEVEL_COLOR.get(level, '')}{_MARK.get(level, '[*]')}{c['reset']} {text}")
            print()
            continue
        print(f"{c['primary']}--- {c['accent']}{b.get('title', 'Résultat')}{c['primary']} ---{c['reset']}")
        if "text" in b:
            lines = (b["text"] or "(vide)").splitlines()
            if max_text_lines and len(lines) > max_text_lines:
                lines = lines[:max_text_lines] + [f"… ({len(lines) - max_text_lines} lignes de plus, option -b pour tout voir)"]
            print("\n".join(lines))
        else:
            rows = b.get("kv") or b.get("rows") or []
            if not rows:
                print("  (aucun)")
            elif "kv" in b:
                width = min(max(len(str(k)) for k, _ in rows), 28)
                for k, v in rows:
                    print(f"  {_cut(k, 28):<{width}}  {v}")
            else:
                table = [b["cols"]] + rows
                widths = [min(max(len(_cut(r[i])) for r in table), _CELL) for i in range(len(b["cols"]))]
                for i, row in enumerate(table):
                    print("  " + "  ".join(f"{_cut(c):<{w}}" for c, w in zip(row, widths)).rstrip())
                    if i == 0:
                        print("  " + "  ".join("-" * w for w in widths))
        print()
