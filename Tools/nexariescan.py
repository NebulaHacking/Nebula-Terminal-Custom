#!/usr/bin/env python3
"""
NexarieScan — simple educational XSS scanner (module importable + CLI)

Fichier: nexariescan.py

Usage CLI:
    python3 nexariescan.py -t https://example.com --delay 0.6 --max-pages 200 --verbose

Usage import from other code:
    from nexariescan import run_scan
    results = run_scan("https://example.com", verbose=True)
"""

from urllib.parse import urljoin, urlparse, parse_qsl, urlunparse
from bs4 import BeautifulSoup
import requests
import time
import logging
import argparse
import sys


class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'

__tool_name__ = "NexarieScan"

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


class Scanner:
    def __init__(self, target_url, ignore_links=None, delay=0.5, user_agent=None, timeout=10):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent or f'{__tool_name__}/1.0 (+educational)'})
        self.links_to_ignore = set(ignore_links or [])
        self.target_url = self._normalize_url(target_url)
        self.target_links = []
        self.delay = float(delay)
        self.timeout = timeout

    def _normalize_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme == '':
            url = 'http://' + url
        return url

    def _is_same_domain(self, link):
        try:
            target_host = urlparse(self.target_url).netloc
            link_host = urlparse(link).netloc
            return target_host == link_host or link_host == ''
        except Exception:
            return False

    def extract_links_from(self, url):
        """Return list of absolute links found on the page."""
        try:
            r = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            logging.debug(f"Failed to GET {url}: {e}")
            return []

        soup = BeautifulSoup(r.content, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href:
                full = urljoin(url, href)
                links.append(full)
        return links

    def crawl(self, url=None, max_pages=1000):
        """Crawl links recursively (same domain only)."""
        if url is None:
            url = self.target_url

        to_visit = [url]
        visited = set()

        while to_visit and len(visited) < max_pages:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Normalize remove fragment
            current = current.split('#')[0]

            logging.info("Crawling: " + current)
            try:
                href_links = self.extract_links_from(current)
            except Exception as e:
                logging.debug(f"Error extracting links from {current}: {e}")
                continue

            for link in href_links:
                link = link.split('#')[0]
                if link in visited:
                    continue
                if any(ignored and link.startswith(ignored) for ignored in self.links_to_ignore):
                    continue
                # Only same domain
                if self._is_same_domain(link):
                    if link not in self.target_links:
                        self.target_links.append(link)
                        logging.debug("Discovered: " + link)
                    to_visit.append(link)
            time.sleep(self.delay)

    def extract_forms(self, url):
        """Return list of form elements (BeautifulSoup objects)."""
        try:
            r = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            logging.debug(f"Failed to GET {url} for forms: {e}")
            return []

        soup = BeautifulSoup(r.content, 'html.parser')
        return soup.find_all('form')

    def submit_form(self, form, value, url, safe_only=False):
        """Fill form inputs; return requests.Response or None.

        If safe_only == True, performs a GET request with params (avoids POST).
        """
        action = form.get('action') or ''
        post_url = urljoin(url, action)
        method = (form.get('method') or 'get').lower()

        inputs_list = form.find_all('input')
        data = {}

        for inp in inputs_list:
            name = inp.get('name')
            if not name:
                continue
            inp_type = (inp.get('type') or 'text').lower()
            inp_value = inp.get('value') or ''
            if inp_type in ['text', 'search', 'email', 'url']:
                inp_value = value
            data[name] = inp_value

        # textarea
        for textarea in form.find_all('textarea'):
            name = textarea.get('name')
            if not name:
                continue
            data[name] = value

        # select: choose first option or selected
        for sel in form.find_all('select'):
            name = sel.get('name')
            if not name:
                continue
            option = sel.find('option', selected=True) or sel.find('option')
            data[name] = option.get('value') if option and option.get('value') is not None else ''

        try:
            if method == 'post' and not safe_only:
                return self.session.post(post_url, data=data, timeout=self.timeout)
            else:
                # GET with params (safer)
                return self.session.get(post_url, params=data, timeout=self.timeout)
        except requests.RequestException as e:
            logging.debug(f"Form submit failed to {post_url}: {e}")
            return None

    def run_scanner(self, xss_payload=None, safe_only=False):
        """Iterate discovered links and test for XSS in links and forms.
        safe_only=True => avoids POST on forms (GET only).
        """
        xss_payload = xss_payload or "<script>alert('xss')</script>"
        results = {
            'xss_in_links': [],
            'xss_in_forms': [],
            'tested_links_count': 0,
            'tested_forms_count': 0
        }

        # ensure we at least test the base url
        if self.target_url not in self.target_links:
            self.target_links.insert(0, self.target_url)

        for link in self.target_links:
            logging.info("Testing: " + link)

            # Test forms on page
            forms = self.extract_forms(link)
            for form in forms:
                results['tested_forms_count'] += 1
                logging.info(f"[+] Testing form in {link}")
                r = self.submit_form(form, xss_payload, link, safe_only=safe_only)
                if r and xss_payload.encode() in r.content:
                    logging.warning(f"[***] XSS discovered in form on {link} (action: {form.get('action')})")
                    results['xss_in_forms'].append({'page': link, 'form_action': form.get('action')})
            time.sleep(self.delay)

            # Test reflected XSS via URL parameter injection
            parsed = urlparse(link)
            qs = parsed.query
            if qs:
                # inject payload for each parameter separately and test
                params = dict(parse_qsl(qs, keep_blank_values=True))
                for key in list(params.keys()):
                    original = params[key]
                    params[key] = original + xss_payload
                    # build new query string safely (simple quoting)
                    new_query = '&'.join(f"{k}={requests.utils.quote(v, safe='')}" for k, v in params.items())
                    injected = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    try:
                        resp = self.session.get(injected, timeout=self.timeout)
                        results['tested_links_count'] += 1
                        if resp and xss_payload.encode() in resp.content:
                            logging.warning(f"[***] XSS discovered in {injected}")
                            results['xss_in_links'].append(injected)
                    except requests.RequestException as e:
                        logging.debug(f"GET failed for {injected}: {e}")
                    # restore param
                    params[key] = original
                    time.sleep(self.delay)

        return results


def parse_kv_pairs(kv_string):
    """Parse 'a=b,c=d' into dict."""
    if not kv_string:
        return {}
    out = {}
    for pair in kv_string.split(','):
        if '=' in pair:
            k, v = pair.split('=', 1)
            out[k] = v
    return out


def run_scan(target,
             delay=0.5,
             login_url=None,
             login_data=None,
             ignore=None,
             user_agent=None,
             max_pages=500,
             xss_payload=None,
             verbose=False,
             safe_only=False):
    """
    Fonction principale exportée pour lancer un scan depuis un autre script.

    Retourne un dictionnaire avec les résultats (ne fait PAS sys.exit si importé).
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if isinstance(ignore, str):
        ignore_list = [s.strip() for s in ignore.split(',') if s.strip()]
    else:
        ignore_list = list(ignore or [])

    # always ignore mailto:
    if 'mailto:' not in ignore_list:
        ignore_list.append('mailto:')

    sc = Scanner(target, ignore_links=ignore_list, delay=delay, user_agent=user_agent)
    # Optional login
    if login_url and login_data:
        data = login_data if isinstance(login_data, dict) else parse_kv_pairs(login_data)
        try:
            logging.info(f"Posting login to {login_url} with keys {list(data.keys())}")
            sc.session.post(login_url, data=data, timeout=sc.timeout)
            time.sleep(sc.delay)
        except Exception as e:
            logging.warning(f"Login attempt failed: {e}")

    # Crawl
    logging.info("Starting crawl...")
    sc.crawl(max_pages=max_pages)

    # Run scanner
    logging.info("Starting vulnerability checks...")
    results = sc.run_scanner(xss_payload=xss_payload, safe_only=safe_only)

    # attach some metadata
    results['scanned_target'] = target
    results['links_found'] = len(sc.target_links)
    results['target_links'] = sc.target_links  # utile pour debug (peut être grand)

    return results


def _cli_main():
    parser = argparse.ArgumentParser(description=f"{__tool_name__} — simple educational XSS scanner.")
    parser.add_argument('-t', '--target', required=True, help='Target URL (e.g. https://example.com)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    parser.add_argument('--login-url', help='Optional: URL to POST login data to before scanning')
    parser.add_argument('--login-data', help='Login data as comma separated k=v pairs, e.g. username=admin,password=pass')
    parser.add_argument('--ignore', help='Comma separated start-of-url strings to ignore', default='')
    parser.add_argument('--user-agent', help='Custom User-Agent header')
    parser.add_argument('--max-pages', type=int, default=500, help='Max pages to crawl')
    parser.add_argument('--xss-payload', help='Custom XSS payload string')
    parser.add_argument('--safe-only', action='store_true', help='Do not POST forms (safer mode)')
    parser.add_argument('--verbose', action='store_true', help='Verbose debug logging')
    args = parser.parse_args()

    results = run_scan(
        target=args.target,
        delay=args.delay,
        login_url=args.login_url,
        login_data=args.login_data,
        ignore=args.ignore,
        user_agent=args.user_agent,
        max_pages=args.max_pages,
        xss_payload=args.xss_payload,
        verbose=args.verbose,
        safe_only=args.safe_only
    )

    # résumé sur la console
    print(f"\n{__tool_name__} — Résumé du scan pour : {results.get('scanned_target')}")
    print("Liens trouvés :", results.get('links_found'))
    print("Tests de liens effectués :", results.get('tested_links_count'))
    print("Tests de formulaires effectués :", results.get('tested_forms_count'))
    print("XSS détectés dans les liens :", len(results.get('xss_in_links', [])))
    for l in results.get('xss_in_links', []):
        print(" ->", l)
    print("XSS détectés dans les formulaires :", len(results.get('xss_in_forms', [])))
    for f in results.get('xss_in_forms', []):
        print(" -> page:", f['page'], " action:", f['form_action'])

    # si on a trouvé des vulnérabilités, retourner code 2 (utile en CI)
    if results.get('xss_in_links') or results.get('xss_in_forms'):
        return 2
    return 0


if __name__ == "__main__":
    # CLI mode -> on peut utiliser sys.exit pour renvoyer un code
    exit_code = _cli_main()
    sys.exit(exit_code)
