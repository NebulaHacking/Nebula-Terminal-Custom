"""
Filmux Simple — Recherche + lecture directe

1. Recherche sur themoviedb.org
2. Ouvre le film sur vidsrc.me (streaming gratuit, fonctionne en 2026)
"""

import sys
import urllib3
from urllib.parse import quote
import webbrowser
from typing import Optional

from bs4 import BeautifulSoup


def search_tmdb(query: str) -> dict:
    """Recherche sur themoviedb.org"""
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    url = f"https://www.themoviedb.org/search/movie?query={quote(query)}&page=1"

    try:
        http = urllib3.PoolManager()
        req = http.request("GET", url, headers={"User-Agent": USER_AGENT}, timeout=10.0)

        if req.status != 200:
            return {}

        soup = BeautifulSoup(req.data, 'html.parser')
        results = {}

        posters = soup.find_all('img', class_='poster')
        for poster in posters[:20]:
            title = poster.get('alt', '').strip()
            link = poster.find_parent('a', href=lambda x: x and x.startswith('/movie/'))
            if not link or not title:
                continue

            href = link.get('href', '')
            tmdb_id = href.split('/')[-1].split('-')[0]

            if tmdb_id and title:
                results[len(results) + 1] = (title, tmdb_id)

        return results

    except Exception:
        return {}


def main(query: str = None) -> None:
    """Interface Filmux simple"""
    print()
    print("╔════════════════════════════════════════╗")
    print("║           FILMUX 3.0                   ║")
    print("╚════════════════════════════════════════╝")
    print()

    if query is None:
        query = input("Recherche film: ").strip()
        if not query:
            print("Annule.")
            return

    print(f"Recherche: '{query}'...")
    results = search_tmdb(query)

    if not results:
        print("Aucun resultat.")
        return

    print()
    print("Resultats:")
    print()
    for num, (title, tmdb_id) in results.items():
        print(f" {num}. {title}")
    print()
    print(" s. Suivant  q. Quitter")
    print()

    while True:
        choice = input("Choix: ").strip().lower()

        if choice == 'q':
            print("Au revoir!")
            return
        elif choice == 's':
            print("Tapez un autre terme de recherche.")
            return
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(results):
                title, tmdb_id = results[num]
                url = f"https://vidsrc.me/embed/movie/{tmdb_id}"
                print()
                print(f"Ouverture: {title}")
                webbrowser.open(url)
                print("Fait!")
                return
            else:
                print("Invalide.")
        else:
            print("Invalide.")


def entry_point(argv: list[str] = None) -> None:
    if argv is None:
        argv = []
    main(argv[0] if argv else None)


if __name__ == "__main__":
    entry_point(sys.argv[1:])