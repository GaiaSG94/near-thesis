"""Lot 12 — Phrases factuelles §4 du dashboard (maquette option A).

Extrait de ``build_dashboard.py`` : gabarits remplis depuis les donnees
reelles (daily.csv + logs), jamais a la main. Une fonction par phrase,
formulations strictement identiques a l'original.
"""

from __future__ import annotations

try:
    from scripts.dashboard_content import (
        MANY_FEW_THRESHOLD_PCT,
        PRICE_NOTE,
        TOP_K_CONTRACTS,
        TOP_K_WALLETS,
    )
except ImportError:  # execution directe : python scripts/xxx.py
    from dashboard_content import (
        MANY_FEW_THRESHOLD_PCT,
        PRICE_NOTE,
        TOP_K_CONTRACTS,
        TOP_K_WALLETS,
    )


def fmt_int(v: float) -> str:
    """Entier affiché avec espace en séparateur de milliers."""
    return f"{v:,.0f}".replace(",", " ")


def fmt_pct(v: float) -> str:
    return f"{v:.1f} %"


def fmt_r(v: float) -> str:
    return f"{v:.3f}"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Correlation de Pearson, ou None si < 3 paires ou serie constante."""
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    mx, my = _mean(xs), _mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def _corr_label(pairs: list[tuple[float, float]], what: str) -> str:
    """Libellé honnête d'une corrélation : valeur ou raison explicite."""
    if len(pairs) < 3:
        return f"non calculable ({what} : paires insuffisantes)"
    r = _pearson([p[0] for p in pairs], [p[1] for p in pairs])
    if r is None:
        return f"non calculable ({what} : série constante)"
    return fmt_r(r)


def _trend_words(a: list[float], v: list[float]) -> str:
    """Décrit (sans expliquer) via moyennes 2e moitié vs 1re moitié.

    Les deux montent -> « montent ensemble sur la période », les deux
    baissent -> « baissent ensemble sur la période », sinon « divergent
    sur la période ». Un seul jour -> mention explicite.
    """
    n = len(a)
    if n < 2:
        return "comptent un seul jour (tendance non descriptible)"
    h = n // 2
    up_a = _mean(a[h:]) > _mean(a[:h])
    dn_a = _mean(a[h:]) < _mean(a[:h])
    up_v = _mean(v[h:]) > _mean(v[:h])
    dn_v = _mean(v[h:]) < _mean(v[:h])
    if up_a and up_v:
        return "montent ensemble sur la période"
    if dn_a and dn_v:
        return "baissent ensemble sur la période"
    return "divergent sur la période"


def _phrase_preuve(daily: dict[str, list]) -> str:
    """Phrase 1 : moyennes actifs + volume, tendance commune."""
    n = len(daily["date"])
    dmin, dmax = daily["date"][0], daily["date"][-1]
    actifs = [float(x) for x in daily["active_accounts"]]
    vols = [float(x) for x in daily["intents_volume_usd"]]
    return (
        f"Du {dmin} au {dmax} ({n} jours), la moyenne quotidienne des "
        f"comptes actifs est de {fmt_int(_mean(actifs))} et le volume "
        f"Intents SUCCESS moyen de {fmt_int(_mean(vols))} USD/jour ; "
        f"les deux séries {_trend_words(actifs, vols)}."
    )


def _phrase_leadlag(daily: dict[str, list]) -> str:
    """Phrase 2 : correlations 0 / J-7 / J-14 sur paires appariees."""
    n = len(daily["date"])
    actifs = [float(x) for x in daily["active_accounts"]]
    vols = [float(x) for x in daily["intents_volume_usd"]]
    pairs0 = list(zip(actifs, vols))
    pairs7 = [(actifs[i], vols[i - 7]) for i in range(7, n)]
    pairs14 = [(actifs[i], vols[i - 14]) for i in range(14, n)]
    r0 = _corr_label(pairs0, "sans décalage")
    r7 = _corr_label(pairs7, "décalage 7 jours")
    r14 = _corr_label(pairs14, "décalage 14 jours")
    if len(pairs14) >= 3:
        span2 = f"sur {len(pairs14)} jours appariés"
    else:
        span2 = (f"sur {n} jours de fenêtre (décalage de 14 jours non "
                 "calculable : paires insuffisantes)")
    return (
        f"Le volume Intents décalé de 7 jours obtient une corrélation de {r7} "
        f"avec les actifs du jour J (décalage de 14 jours : {r14}), contre "
        f"{r0} sans décalage, {span2}."
    )


def _phrase_contexte(
    daily: dict[str, list],
    top_contracts: list[tuple[str, float]] | None,
) -> str:
    """Phrase 3 : activite on-chain + concentration par contrat."""
    mean_tx = fmt_int(_mean([float(x) for x in daily["tx_count"]]))
    mean_unq = fmt_int(_mean([float(x) for x in daily["unique_contracts"]]))
    if top_contracts is None:
        clause_c = ("la concentration par contrat est non calculable "
                    "(ni data/merged/top_contracts.csv ni "
                    "data/raw/bq_04_top_contracts.csv)")
    else:
        kc = min(TOP_K_CONTRACTS, len(top_contracts))
        top_sum = sum(c for _, c in top_contracts[:kc])
        total = sum(float(x) for x in daily["contract_calls"])
        if total <= 0:
            clause_c = ("la concentration par contrat est non calculable "
                        "(contract_calls total nul)")
        elif top_sum > total:
            clause_c = (f"la concentration par contrat est incohérente (top {kc} = "
                        f"{fmt_int(top_sum)} appels > total daily.csv = {fmt_int(total)}"
                        " — lots désynchronisés)")
        else:
            clause_c = (f"le top {kc} contrats concentre {fmt_pct(100 * top_sum / total)} "
                        "des appels")
    return (
        f"Sur la fenêtre, {mean_tx} transactions/jour en moyenne et {mean_unq} "
        f"contrats uniques/jour ; {clause_c}."
    )


def _phrase_limites(wallets: dict[str, float]) -> str:
    """Phrase 4 : contre-preuve, concentration par portefeuille."""
    if not wallets:
        return (
            "La concentration par portefeuille est non calculable (brut "
            "data/raw/intents_*.json absent ou sans montants USD exploitables)."
        )
    ranked = sorted(wallets.values(), reverse=True)
    kw = min(TOP_K_WALLETS, len(ranked))
    total_w = sum(ranked)
    pw = 100 * sum(ranked[:kw]) / total_w if total_w > 0 else 0.0
    few = "peu" if pw >= MANY_FEW_THRESHOLD_PCT else "beaucoup"
    return (
        f"Le top {kw} wallets représente {fmt_pct(pw)} du volume Intents "
        f"SUCCESS sur la fenêtre : le signal repose donc sur {few} d'acteurs."
    )


def _phrase_methode(daily: dict[str, list], bq: dict[str, str | None]) -> str:
    """Phrase 5 : fraicheur BigQuery (jamais un resultat)."""
    dmin, dmax = daily["date"][0], daily["date"][-1]
    maxbd = bq["max_block_date"] or "non relevé (aucun log BigQuery — lot 05)"
    pullbq = bq["pull_date"] or "non relevé (aucun log BigQuery — lot 05)"
    raw_bytes = bq["bytes"]
    kind = bq.get("bytes_kind") or "scannés"
    try:
        bytes_txt = f"{fmt_int(float(raw_bytes))} bytes {kind}" if raw_bytes else None
    except (TypeError, ValueError):
        bytes_txt = f"{raw_bytes} bytes {kind}"
    bytes_txt = bytes_txt or "bytes non relevés (aucun log BigQuery — lot 05)"
    return (
        f"Données BigQuery au MAX(block_date)={maxbd} (pull du {pullbq}, "
        f"{bytes_txt}) ; fenêtre {dmin} → {dmax} ; prix : {PRICE_NOTE}."
    )


def _build_phrases(
    daily: dict[str, list],
    bq: dict[str, str | None],
    intent_pull: str | None,
    wallets: dict[str, float],
    top_contracts: list[tuple[str, float]] | None,
) -> dict[str, str]:
    """Assemble les 5 phrases factuelles §4 depuis les donnees reelles.

    NOTE : intent_pull (pull Intents) est affiche dans le header et le
    tableau methode, pas dans ces phrases (signature historique inchangee).
    """
    _ = intent_pull
    return {
        "preuve": _phrase_preuve(daily),
        "leadlag": _phrase_leadlag(daily),
        "contexte": _phrase_contexte(daily, top_contracts),
        "limites": _phrase_limites(wallets),
        "methode": _phrase_methode(daily, bq),
    }
