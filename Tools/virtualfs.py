"""Système de fichiers virtuel de Nebula — ton espace de travail.

Arborescence en mémoire (dossier = dict, fichier = texte), sauvegardée avec ton profil.
Les chemins marchent comme sous Linux : absolus (/Nebula/notes.txt), relatifs (notes.txt,
../x), `~` = /Nebula (ton dossier personnel), `.` et `..`.
Les résultats d'une commande y atterrissent avec la redirection (`scan ... > scan.txt`) ;
`import` / `export` font le pont avec les vrais fichiers du disque.

Format stocké (compatible avec les anciens profils et sauvegardes) : {"/": {"Nebula": {...}}}
"""
import fnmatch
import json
import os
from pathlib import Path

# Absolu : les sauvegardes restent dans le projet quel que soit le dossier de lancement.
SAVES_DIR = str(Path(__file__).resolve().parent.parent / "saves")
HOME = ["Nebula"]
MAX_FILE = 5 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024


def _size(node) -> int:
    if isinstance(node, str):
        return len(node.encode("utf-8"))
    return sum(_size(child) for child in node.values())


class VirtualFS:
    def __init__(self) -> None:
        self.root: dict = {"/": {"Nebula": {}}}
        self.current_path: list[str] = ["/", *HOME]

    # ------------------------------------------------------------------
    # Chemins
    # ------------------------------------------------------------------
    @property
    def cwd(self) -> list[str]:
        return self.current_path[1:]

    def parts(self, path: str = "") -> list[str]:
        """Chemin tapé → liste absolue de noms (sans la racine)."""
        path = (path or "").strip().replace("\\", "/")
        if path == "~" or path.startswith("~/"):
            base, path = list(HOME), path[1:]
        elif path.startswith("/"):
            base = []
        else:
            base = list(self.cwd)
        for name in path.split("/"):
            if name in ("", "."):
                continue
            if name == "..":
                if base:
                    base.pop()
            else:
                base.append(name)
        return base

    def show(self, parts: list[str]) -> str:
        return "/" + "/".join(parts)

    def node(self, parts: list[str]):
        cur = self.root["/"]
        for name in parts:
            if not isinstance(cur, dict) or name not in cur:
                return None
            cur = cur[name]
        return cur

    def _dir(self, path: str):
        parts = self.parts(path)
        node = self.node(parts)
        if node is None:
            raise ValueError(f"Introuvable : {self.show(parts)}")
        if not isinstance(node, dict):
            raise ValueError(f"Ce n'est pas un dossier : {self.show(parts)}")
        return parts, node

    def _parent(self, path: str):
        """(dossier parent, nom) pour créer ou remplacer `path`."""
        parts = self.parts(path)
        if not parts:
            raise ValueError("Opération impossible sur la racine /")
        name = parts[-1]
        if len(name) > 255 or any(c in name for c in '<>:"|?*\0'):
            raise ValueError(f"Nom invalide : {name!r}")
        parent = self.node(parts[:-1])
        if not isinstance(parent, dict):
            raise ValueError(f"Dossier inexistant : {self.show(parts[:-1])}")
        return parent, name, parts

    def _check_space(self, extra: int) -> None:
        if extra > MAX_FILE:
            raise ValueError(f"Fichier trop gros (max {MAX_FILE // 1024 // 1024} Mo)")
        if _size(self.root["/"]) + extra > MAX_TOTAL:
            raise ValueError(f"Espace de travail plein (max {MAX_TOTAL // 1024 // 1024} Mo) : supprime ou exporte des fichiers")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def get_current_dir(self) -> dict:
        return self.node(self.cwd)

    def get_path(self) -> str:
        return self.show(self.cwd)

    def cd(self, path: str = "~") -> None:
        parts, _ = self._dir(path or "~")
        self.current_path = ["/", *parts]

    def ls(self, path: str = "") -> list[tuple[str, bool, int]]:
        """[(nom, est_un_dossier, taille)] — dossiers d'abord. Un fichier se liste lui-même."""
        parts = self.parts(path)
        node = self.node(parts)
        if node is None:
            raise ValueError(f"Introuvable : {self.show(parts)}")
        if isinstance(node, str):
            return [(parts[-1], False, _size(node))]
        items = [(n, isinstance(c, dict), _size(c)) for n, c in node.items()]
        return sorted(items, key=lambda i: (not i[1], i[0].lower()))

    def entries(self, path_prefix: str) -> list[str]:
        """Complétions de chemin pour Tab (dossiers terminés par /)."""
        head, sep, start = path_prefix.replace("\\", "/").rpartition("/")
        node = self.node(self.parts(head or "/")) if sep else self.get_current_dir()
        if not isinstance(node, dict):
            return []
        base = head + "/" if sep else ""
        return [base + n + ("/" if isinstance(c, dict) else "") for n, c in sorted(node.items()) if n.startswith(start)]

    # ------------------------------------------------------------------
    # Création / lecture / écriture
    # ------------------------------------------------------------------
    def mkdir(self, path: str, parents: bool = False) -> None:
        if parents:
            cur = self.root["/"]
            for name in self.parts(path):
                nxt = cur.setdefault(name, {})
                if not isinstance(nxt, dict):
                    raise ValueError(f"Un fichier porte déjà ce nom : {name}")
                cur = nxt
            return
        parent, name, parts = self._parent(path)
        if name in parent:
            raise ValueError(f"Existe déjà : {self.show(parts)}")
        parent[name] = {}

    def touch(self, path: str) -> None:
        parent, name, parts = self._parent(path)
        if isinstance(parent.get(name), dict):
            raise ValueError(f"C'est un dossier : {self.show(parts)}")
        parent.setdefault(name, "")

    def read_file(self, path: str) -> str | None:
        node = self.node(self.parts(path))
        return node if isinstance(node, str) else None

    def read(self, path: str) -> str:
        parts = self.parts(path)
        node = self.node(parts)
        if node is None:
            raise ValueError(f"Introuvable : {self.show(parts)}")
        if isinstance(node, dict):
            raise ValueError(f"C'est un dossier : {self.show(parts)}")
        return node

    def write_file(self, path: str, content: str, append: bool = False) -> str:
        parent, name, parts = self._parent(path)
        old = parent.get(name)
        if isinstance(old, dict):
            raise ValueError(f"C'est un dossier : {self.show(parts)}")
        new = (old or "") + content if append else content
        self._check_space(len(new.encode("utf-8")) - _size(old or ""))
        parent[name] = new
        return self.show(parts)

    # ------------------------------------------------------------------
    # Suppression / déplacement / copie
    # ------------------------------------------------------------------
    def rm(self, path: str, recursive: bool = False) -> None:
        parent, name, parts = self._parent(path)
        if name not in parent:
            raise ValueError(f"Introuvable : {self.show(parts)}")
        if isinstance(parent[name], dict) and parent[name] and not recursive:
            raise ValueError(f"Dossier non vide : {self.show(parts)} (rm -r pour tout supprimer)")
        if parts == self.cwd[:len(parts)]:
            raise ValueError("Impossible de supprimer le dossier où tu te trouves (ou un de ses parents)")
        del parent[name]

    def delete_file(self, path: str) -> bool:  # compatibilité
        try:
            self.rm(path)
            return True
        except ValueError:
            return False

    def _target(self, src_parts, dst: str):
        """Destination de mv/cp : dans le dossier `dst` s'il existe, sinon renommage en `dst`."""
        dst_node = self.node(self.parts(dst))
        if isinstance(dst_node, dict):
            dst = dst.rstrip("/") + "/" + src_parts[-1]
        parent, name, parts = self._parent(dst)
        if parts[:len(src_parts)] == src_parts:
            raise ValueError("Impossible de mettre un dossier à l'intérieur de lui-même")
        if isinstance(parent.get(name), dict):
            raise ValueError(f"Un dossier porte déjà ce nom : {self.show(parts)}")
        return parent, name

    def mv(self, src: str, dst: str) -> None:
        src_parent, src_name, src_parts = self._parent(src)
        if src_name not in src_parent:
            raise ValueError(f"Introuvable : {self.show(src_parts)}")
        if src_parts == self.cwd[:len(src_parts)]:
            raise ValueError("Impossible de déplacer le dossier où tu te trouves")
        parent, name = self._target(src_parts, dst)
        parent[name] = src_parent.pop(src_name)

    def cp(self, src: str, dst: str, recursive: bool = False) -> None:
        src_parts = self.parts(src)
        node = self.node(src_parts)
        if node is None or not src_parts:
            raise ValueError(f"Introuvable : {self.show(src_parts)}")
        if isinstance(node, dict) and not recursive:
            raise ValueError(f"{self.show(src_parts)} est un dossier (cp -r pour le copier)")
        parent, name = self._target(src_parts, dst)
        copy = json.loads(json.dumps(node))
        self._check_space(_size(copy))
        parent[name] = copy

    # ------------------------------------------------------------------
    # Recherche / affichage
    # ------------------------------------------------------------------
    def tree(self, path: str = "") -> list[str]:
        parts, node = self._dir(path)
        lines = [self.show(parts)]

        def walk(d, prefix):
            items = sorted(d.items(), key=lambda i: (not isinstance(i[1], dict), i[0].lower()))
            for i, (n, c) in enumerate(items):
                last = i == len(items) - 1
                lines.append(f"{prefix}{'└── ' if last else '├── '}{n}{'/' if isinstance(c, dict) else ''}")
                if isinstance(c, dict):
                    walk(c, prefix + ("    " if last else "│   "))

        walk(node, "")
        return lines

    def find(self, pattern: str, path: str = "") -> list[str]:
        parts, node = self._dir(path)
        found = []

        def walk(d, base):
            for n, c in sorted(d.items()):
                if fnmatch.fnmatch(n.lower(), pattern.lower()) or pattern.lower() in n.lower():
                    found.append(self.show(base + [n]) + ("/" if isinstance(c, dict) else ""))
                if isinstance(c, dict):
                    walk(c, base + [n])

        walk(node, parts)
        return found

    def usage(self) -> int:
        return _size(self.root["/"])

    # ------------------------------------------------------------------
    # Disque réel
    # ------------------------------------------------------------------
    def import_file(self, disk_path: str, path: str = "") -> str:
        disk = Path(os.path.expanduser(disk_path.strip().strip('"')))
        if not disk.is_file():
            raise ValueError(f"Fichier introuvable sur le disque : {disk}")
        if disk.stat().st_size > MAX_FILE:
            raise ValueError(f"Fichier trop gros (max {MAX_FILE // 1024 // 1024} Mo)")
        data = disk.read_bytes()
        if b"\0" in data[:4096]:
            raise ValueError("Fichier binaire : seul le texte peut aller dans l'espace de travail")
        target = path or disk.name
        if isinstance(self.node(self.parts(target)), dict):
            target = target.rstrip("/") + "/" + disk.name
        # Fins de ligne Windows normalisées : sinon elles doublent à l'export.
        return self.write_file(target, data.decode("utf-8", "replace").replace("\r\n", "\n"))

    def export_file(self, path: str, disk_path: str, overwrite: bool = False) -> str:
        content = self.read(path)
        disk = Path(os.path.expanduser(disk_path.strip().strip('"')))
        if disk.is_dir():
            disk = disk / self.parts(path)[-1]
        if disk.exists() and not overwrite:
            raise ValueError(f"{disk} existe déjà (ajoute -f pour l'écraser)")
        disk.write_text(content, encoding="utf-8")
        return str(disk.resolve())

    # ------------------------------------------------------------------
    # Chargement / sauvegarde
    # ------------------------------------------------------------------
    def load_tree(self, root) -> None:
        """Remplace l'arborescence par une sauvegarde (profil ou fichier), après vérification."""
        def valid(d):
            return isinstance(d, dict) and all(isinstance(k, str) and (isinstance(v, str) or valid(v)) for k, v in d.items())

        if not (isinstance(root, dict) and set(root) == {"/"} and valid(root["/"])):
            raise ValueError("Sauvegarde du système de fichiers invalide")
        self.root = root
        self.current_path = ["/", *HOME] if isinstance(self.node(HOME), dict) else ["/"]

    @staticmethod
    def list_saves(saves_dir: str = SAVES_DIR) -> list[str]:
        if not os.path.isdir(saves_dir):
            return []
        return sorted(f for f in os.listdir(saves_dir) if f.endswith(".txt"))

    def save_to(self, filename: str, saves_dir: str = SAVES_DIR) -> str:
        if not filename or any(c in filename for c in '\\/<>:"|?*'):
            raise ValueError(f"Nom de sauvegarde invalide : {filename!r}")
        os.makedirs(saves_dir, exist_ok=True)
        filepath = os.path.join(saves_dir, filename + ".txt")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.root, f, indent=2, ensure_ascii=False)
        return filepath

    def load_from(self, index: int, saves_dir: str = SAVES_DIR) -> str | None:
        files = self.list_saves(saves_dir)
        if not 0 <= index < len(files):
            return None
        filepath = os.path.join(saves_dir, files[index])
        with open(filepath, "r", encoding="utf-8") as f:
            self.load_tree(json.load(f))
        return filepath
