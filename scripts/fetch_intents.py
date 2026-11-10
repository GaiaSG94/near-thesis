#!/usr/bin/env python3
"""Pull brut paginé des swaps NEAR Intents (lot 06).

Source : GET https://explorer.near-intents.org/api/v0/transactions
Auth   : JWT Bearer lu dans `.env` (jamais loggé, jamais commité).

Usage:
    python scripts/fetch_intents.py --start 2026-10-01 --end 2026-11-09
    python scripts/fetch_intents.py --start 2026-10-01 --max-pages 5

Sans JWT valide, le script échoue proprement (exit 2) en expliquant le
mode cache : `rebuild.py` réutilise alors `data/raw/intents_*.json`.

Règles API (intent.md) :
  - 1 req / 5 s max (429 si dépassé) -> throttle >= 5 s entre appels.
  - Pagination curseur : `lastDepositAddress` + `lastDepositMemo`,
    `direction=next` (vers le plus vieux), `numberOfTransactions` <= 1000.
  - Filtres : `statuses=SUCCESS` + `startTimestamp` / `endTimestamp` (ms).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from scripts.common import extract_payload_items
except ImportError:  # execution directe : python scripts/xxx.py
    from common import extract_payload_items

BASE_URL = "https://explorer.near-intents.org/api/v0"
TRANSACTIONS_PATH = "/transactions"
PAGE_SIZE = 1000  # max autorisé
THROTTLE_SECONDS = 5.0
# Noms de variable acceptés dans .env (par ordre de priorité).
JWT_ENV_KEYS = ("INTENTS_JWT", "NEAR_INTENTS_JWT", "NEAR_INTENTS_API_JWT")


def _repo_root() -> Path:
    # scripts/fetch_intents.py -> near-thesis/
    return Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse minimaliste d'un fichier .env (KEY=VALUE, sans log des valeurs)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and val and key not in values:
            values[key] = val
    return values


def get_jwt(explicit_env: str | None = None) -> tuple[str | None, str]:
    """Retourne (jwt, source). Le JWT n'est jamais affiché ni loggé."""
    candidates: list[Path] = []
    if explicit_env:
        candidates.append(Path(explicit_env))
    else:
        candidates.append(_repo_root() / ".env")
        candidates.append(Path.cwd() / ".env")
    for key in JWT_ENV_KEYS:
        if os.environ.get(key):
            return os.environ[key], f"env:{key}"
    for env_file in candidates:
        values = load_dotenv(env_file)
        for key in JWT_ENV_KEYS:
            if values.get(key):
                return values[key], f"{env_file}:{key}"
    return None, "introuvable (.env / environnement)"


def to_ms_timestamp(value: str) -> int:
    """Accepte 'YYYY-MM-DD' (UTC) ou un timestamp ms epoch. Retourne des ms."""
    value = value.strip()
    if value.isdigit():
        ts = int(value)
        # Heuristique : secondes -> ms.
        return ts * 1000 if ts < 10**12 else ts
    parsed = dt.datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp() * 1000)


def build_url(params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(params)
    return f"{BASE_URL}{TRANSACTIONS_PATH}?{query}"


def http_get(url: str, jwt: str, timeout: int = 60) -> tuple[int, dict]:
    """GET authentifié. Ne loggue jamais le JWT (ni headers ni URL)."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {jwt}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
        return status, payload
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        # 429 -> remonter le Retry-After éventuel sans exposer de secret.
        retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
        raise IntentsHTTPError(exc.code, body, retry_after) from None


class IntentsHTTPError(Exception):
    def __init__(self, status: int, body: str, retry_after: str = "") -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body
        self.retry_after = retry_after


def extract_items(payload: dict | list) -> list[dict]:
    """Liste des transactions d'un payload API (voir scripts/common.py)."""
    return extract_payload_items(payload)


def extract_cursor(last_item: dict) -> tuple[str | None, str | None]:
    """Curseur = dernière adresse/memo de dépôt de la page.

    L'ancien param `lastDepositAddressAndMemo` est déprécié : on envoie
    toujours les deux champs séparés.
    """
    addr = last_item.get("depositAddress") or last_item.get("lastDepositAddress")
    memo = last_item.get("depositMemo")
    if memo is None:
        memo = last_item.get("lastDepositMemo", "")
    if addr is None:
        # Variantes défensives selon la forme du payload brut.
        deposit = last_item.get("deposit") or {}
        if isinstance(deposit, dict):
            addr = deposit.get("address")
            memo = deposit.get("memo", memo or "")
    if addr is None:
        return None, None
    return str(addr), str(memo or "")


def _build_page_params(start_ms: int, end_ms: int, page_size: int,
                       cursor_addr: str | None, cursor_memo: str | None) -> dict[str, str]:
    """Parametres d'une page (curseur inclus des la 2e page)."""
    params: dict[str, str] = {
        "statuses": "SUCCESS",
        "startTimestamp": str(start_ms),
        "endTimestamp": str(end_ms),
        "direction": "next",
        "numberOfTransactions": str(page_size),
    }
    if cursor_addr is not None:
        params["lastDepositAddress"] = cursor_addr
        params["lastDepositMemo"] = cursor_memo or ""
    return params


def _throttled_get(jwt: str, url: str, page: int) -> tuple[int, dict]:
    """GET avec throttle 5 s (des la 2e page) + retry unique sur 429."""
    if page > 1:
        # Throttle imposé : >= 5 s entre deux appels.
        time.sleep(THROTTLE_SECONDS)
    try:
        return http_get(url, jwt)
    except IntentsHTTPError as exc:
        if exc.status != 429:
            raise
        wait = THROTTLE_SECONDS * 3
        if exc.retry_after.isdigit():
            wait = max(wait, int(exc.retry_after))
        print(
            f"[page {page}] 429 rate-limit, pause {wait:.0f}s puis retry...",
            flush=True,
        )
        time.sleep(wait)
        return http_get(url, jwt)


def _write_page_envelope(out_dir: Path, payload: dict, params: dict[str, str],
                         status: int, page: int, pull_stamp: str,
                         start_label: str, end_label: str) -> tuple[Path, list[dict]]:
    """Ecrit l'enveloppe brute d'une page. Retourne (chemin, transactions)."""
    items = extract_items(payload)
    envelope = {
        "pull_date": pull_stamp,
        "source": "explorer.near-intents.org/api/v0/transactions",
        "page": page,
        "http_status": status,
        "params": {**params},  # pas de secret ici (JWT en header uniquement)
        "item_count": len(items),
        "payload": payload,  # brut intégral, non transformé
    }
    fname = (
        f"intents_{start_label}_{end_label}_pull{pull_stamp}_p{page:03d}.json"
    )
    dest = out_dir / fname
    dest.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return dest, items


def fetch_all(
    jwt: str,
    start_ms: int,
    end_ms: int,
    out_dir: Path,
    pull_stamp: str,
    max_pages: int,
    page_size: int,
    start_label: str,
    end_label: str,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    cursor_addr: str | None = None
    cursor_memo: str | None = None
    total_items = 0

    for page in range(1, max_pages + 1):
        params = _build_page_params(start_ms, end_ms, page_size,
                                    cursor_addr, cursor_memo)
        url = build_url(params)
        status, payload = _throttled_get(jwt, url, page)
        dest, items = _write_page_envelope(out_dir, payload, params, status,
                                           page, pull_stamp, start_label, end_label)
        written.append(dest)
        total_items += len(items)
        print(
            f"[page {page}] {len(items)} tx -> {dest.name} (total {total_items})",
            flush=True,
        )

        if not items or len(items) < page_size:
            break  # dernière page
        new_addr, new_memo = extract_cursor(items[-1])
        if new_addr is None or (new_addr, new_memo) == (cursor_addr, cursor_memo):
            print(
                "[info] curseur introuvable ou inchangé : arrêt propre.",
                flush=True,
            )
            break
        cursor_addr, cursor_memo = new_addr, new_memo

    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pull brut paginé NEAR Intents.")
    p.add_argument("--start", default="2026-10-01",
                   help="Début de fenêtre (YYYY-MM-DD UTC ou ms).")
    p.add_argument("--end", default=None,
                   help="Fin de fenêtre (défaut : maintenant).")
    p.add_argument("--out-dir", default=None,
                   help="Dossier brut (défaut : data/raw sous near-thesis/).")
    p.add_argument("--max-pages", type=int, default=1000,
                   help="Garde-fou pagination (défaut 1000).")
    p.add_argument("--page-size", type=int, default=PAGE_SIZE,
                   help="numberOfTransactions par appel (max 1000).")
    p.add_argument("--env", default=None, help="Chemin .env explicite.")
    return p.parse_args(argv)


def _missing_jwt_message() -> str:
    """Message d'erreur sans JWT (mode cache explique, valeur masquee)."""
    return (
        "ERREUR : aucun JWT Intents trouvé.\n"
        "  Cherché : variables INTENTS_JWT / NEAR_INTENTS_JWT (environnement),\n"
        "  puis fichier `.env` à la racine near-thesis/ (ex : INTENTS_JWT=<token>).\n"
        "  MODE CACHE : relancez `python rebuild.py` sans pull Intents —\n"
        "  il réutilise le brut existant `data/raw/intents_*.json` et produit\n"
        "  les mêmes chiffres. Pour rafraîchir le brut, ajoutez le JWT dans\n"
        "  `.env` (jamais commité, voir `.env.example`) puis relancez ce script."
    )


def _resolve_pull_window(args: argparse.Namespace) -> tuple:
    """Fenetre ms + dossier brut + etiquettes (sans validation croisee)."""
    page_size = min(max(1, args.page_size), PAGE_SIZE)
    start_ms = to_ms_timestamp(args.start)
    end_ms = to_ms_timestamp(args.end) if args.end else int(time.time() * 1000)
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else _repo_root() / "data" / "raw"
    )
    pull_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start_label = args.start.replace("-", "")
    end_label = (args.end or pull_stamp[:8]).replace("-", "")
    return page_size, start_ms, end_ms, out_dir, pull_stamp, start_label, end_label


def _report_done(written: list[Path], out_dir: Path, pull_stamp: str) -> None:
    """Resume de fin de pull (fichiers ecrits)."""
    print(f"[done] pull {pull_stamp} : {len(written)} fichier(s) écrit(s) dans {out_dir}")
    for f in written:
        print(f"  - {f.name}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    jwt, jwt_source = get_jwt(args.env)
    if not jwt:
        print(_missing_jwt_message(), file=sys.stderr)
        return 2

    (page_size, start_ms, end_ms, out_dir, pull_stamp,
     start_label, end_label) = _resolve_pull_window(args)
    if start_ms > end_ms:
        print("ERREUR : --start postérieur à --end.", file=sys.stderr)
        return 2

    print(
        f"[init] JWT: présent ({jwt_source}, valeur masquée) | "
        f"fenêtre ms {start_ms} -> {end_ms} | page_size {page_size} | "
        f"out {out_dir}",
        flush=True,
    )
    try:
        written = fetch_all(
            jwt, start_ms, end_ms, out_dir, pull_stamp,
            max(1, args.max_pages), page_size, start_label, end_label,
        )
    except IntentsHTTPError as exc:
        print(
            f"ERREUR HTTP {exc.status} sur /transactions. Extrait : {exc.body}",
            file=sys.stderr,
        )
        return 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"ERREUR réseau/parse : {exc}", file=sys.stderr)
        return 1

    _report_done(written, out_dir, pull_stamp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
