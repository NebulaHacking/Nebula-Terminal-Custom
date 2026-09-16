"""Calculatrice — portage des lignes 669-681 de l'ancien main.py, SÉCURISÉ.

L'ancien code faisait `eval(expr, {"__builtins__": None, "math": math})` — fragile
(`__builtins__` n'est pas réellement neutralisé par la dict vide). On le remplace
par un validateur AST avec liste blanche : aucune exécution arbitraire possible.

Autorisé : nombres, parenthèses, + - * / % ** // , préfixe -/+,
    et les fonctions `math.*` + sqrt/abs/round/min/max (avec `sqrt`/`math.sqrt`).
"""
import ast
import math

_FUNCS = {"sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max}
_FUNCS.update({n: getattr(math, n) for n in dir(math) if not n.startswith("_")})

_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)


def _verifier(node) -> None:
    """Lève ValueError si le nœud (ou un descendant) n'est pas dans la liste blanche."""
    if isinstance(node, ast.Expression):
        _verifier(node.body)
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return
        raise ValueError(f"constante non numérique : {node.value!r}")
    if isinstance(node, ast.BinOp) and isinstance(node.op, _BINOPS):
        _verifier(node.left)
        _verifier(node.right)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        _verifier(node.operand)
        return
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in _FUNCS:
                raise ValueError(f"fonction interdite : {func.id}")
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == "math" and func.attr in _FUNCS):
            pass  # math.<fonction de la liste blanche> autorisée
        else:
            raise ValueError(f"appel non autorisé : {ast.dump(func)}")
        for arg in node.args:
            _verifier(arg)
        return
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "math" and node.attr in _FUNCS):
        return  # constante/fonction math.* référence seule (ex: math.pi)
    raise ValueError(f"expression non autorisée : {type(node).__name__}")


def calculer(expr: str):
    """Évalue une expression mathématique sûre. Lève ValueError/ZeroDivisionError etc."""
    tree = ast.parse(expr, mode="eval")
    _verifier(tree)
    env = {"math": math, **_FUNCS}
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, env)


def calculatrice() -> None:
    """Boucle interactive REPL de la calculatrice (parité avec l'original)."""
    print("Mode Calculatrice : tapez une expression mathématique ou 'exit' pour revenir.")
    while True:
        expr = input("calc> ").strip()
        if expr.lower() == "exit":
            print("Sortie du mode calculatrice.")
            break
        try:
            print("Résultat :", calculer(expr))
        except Exception as e:
            print("Erreur :", e)