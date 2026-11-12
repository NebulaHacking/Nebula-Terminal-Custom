# Changelog

## 2.0.0 — 2026-11

### Nebula IA (nouveau)
- Copilote de pentest qui lance lui-même les commandes Nebula, lit les résultats (`--json`) et enchaîne.
- 8 fournisseurs : Claude, ChatGPT, Gemini, Mistral, Groq, DeepSeek, OpenRouter, Ollama (local). Changement à chaud, même conversation.
- Garde-fous appliqués par le terminal : accord pour toute commande réseau, périmètre de mission imposé, commandes système interdites.
- Chaque action de l'IA est inscrite au registre de la mission ; ses constats vont au rapport.
- Réponses en flux, bouton Stop (Ctrl+C dans le terminal), `ia test` pour vérifier les clés.
- Playbooks : `ia audit web|tls|reseau|complet <cible>`.
- Dans le terminal (`ia`) et dans le dashboard (page Nebula IA).

### Missions
- Mode mission : périmètre autorisé, registre de preuves chaîné par hash, `mission diff`.
- `mission constat` / `constats` : constats manuels avec gravité, famille, commande de preuve.
- `mission retest` : rejoue la preuve de chaque constat → corrigé ou toujours présent.
- Rapport Markdown + HTML imprimable en PDF : synthèse, constats, tableau de conformité (nLPD, ISO/IEC 27001:2022, NIS2), chronologie.

### Outils
- Nouveaux : `tracewave` (captures réseau), `reqforge` (atelier HTTP), boîte à outils crypto, recon (`dns`, `whois`, `headers`, `banner`, `sslscan`, `subdomain`, `hostscan`).
- `shadowviper` réécrit : résultats structurés, RIPEstat (BGPView a fermé), fonctionne sans scikit-learn.
- `nexariescan` : non interactif (`nexariescan <url>`), résultats structurés, GET seulement sauf `--post`.
- Tous les outils réseau : formulaire dans le dashboard, `--json`, utilisables par l'IA.
- Sorties des commandes Windows (ping, tracert, nslookup, exec) décodées avec la bonne page de code.

### Terminal et interface
- Saisie type Kali (Tab, suggestions grisées), espace de travail façon Linux, redirection `>`, alias, scripts, `tuto`.
- 8 thèmes avec dégradé ; bannières et dashboard aux couleurs du thème ; prompt qui signale erreur et lenteur.
- Dashboard web local (`nebulaGui`) : journal en direct, console, formulaires d'outils.
- Bannières pour les outils qui n'en avaient pas : `dirb`, `nexariescan`, `tracewave`, `reqforge` (écran d'accueil) et la conversation `ia`, aux couleurs du thème (masquées avec `--json`, dans le dashboard et pour l'IA).

### Installation
- Dépendances de base allégées ; outils optionnels via `python launch.py --full` ou `pip install -e ".[all]"`.
- `pyproject.toml` (commande `nebula`), `nebula --version`.
- `update` compare ta version à celle publiée sur GitHub, affiche les nouveautés et l'installe (git pull, ou téléchargement ZIP si le projet n'a pas été cloné). `update --check` pour seulement vérifier. Vérification automatique au démarrage, une fois par jour.
- Tests automatiques (GitHub Actions, Windows + Linux).

### Retiré
- `netstorm` (outil d'attaque réseau) : incompatible avec le positionnement « audit encadré » de la 2.0.
- Ancien chat Nebula IA (Ollama/OpenAI sans outils, voix TTS).
