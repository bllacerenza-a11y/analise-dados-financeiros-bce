"""Exploratory analysis of the ECB USD per EUR reference rate in 2025."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent


def load_rates(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"TIME_PERIOD", "OBS_VALUE"}
    if required.difference(raw.columns):
        raise ValueError(f"Colunas ausentes: {', '.join(sorted(required.difference(raw.columns)))}")
    if "KEY" in raw.columns and not raw["KEY"].eq("EXR.D.USD.EUR.SP00.A").all():
        raise ValueError("A fonte contém uma série diferente da taxa USD por EUR do BCE")
    rates = raw[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "usd_per_eur"})
    rates["date"] = pd.to_datetime(rates["date"], errors="coerce")
    rates["usd_per_eur"] = pd.to_numeric(rates["usd_per_eur"], errors="coerce")
    if rates["date"].isna().any() or rates["usd_per_eur"].isna().any() or rates["usd_per_eur"].le(0).any():
        raise ValueError("Datas ou cotações inválidas na fonte")
    if rates["date"].duplicated().any():
        raise ValueError("Datas duplicadas na fonte")
    rates = rates.sort_values("date").reset_index(drop=True)
    if rates.empty:
        raise ValueError("A fonte está vazia")
    return rates


def analyze(rates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rates = rates.copy()
    rates["daily_change_pct"] = rates["usd_per_eur"].pct_change() * 100
    rates["monthly"] = rates["date"].dt.to_period("M").astype(str)
    # Descriptive variation of the quotation, not portfolio return or trading risk.
    rates["volatility_20_obs_pct"] = rates["daily_change_pct"].rolling(20).std() * (252 ** 0.5)
    rates["quote_drawdown_pct"] = (rates["usd_per_eur"] / rates["usd_per_eur"].cummax() - 1) * 100
    monthly = rates.groupby("monthly", as_index=False).agg(
        average_usd_per_eur=("usd_per_eur", "mean"),
        observations=("usd_per_eur", "size"),
    )
    monthly["average_usd_per_eur"] = monthly["average_usd_per_eur"].round(4)
    daily_std = rates["daily_change_pct"].std()
    metrics = {
        "series": "EXR.D.USD.EUR.SP00.A",
        "quotation": "USD por 1 EUR",
        "first_date": rates["date"].min().date().isoformat(),
        "last_date": rates["date"].max().date().isoformat(),
        "observations": len(rates),
        "first_quote": round(float(rates["usd_per_eur"].iloc[0]), 4),
        "last_quote": round(float(rates["usd_per_eur"].iloc[-1]), 4),
        "quote_change_pct": round(float((rates["usd_per_eur"].iloc[-1] / rates["usd_per_eur"].iloc[0] - 1) * 100), 2),
        "lowest_quote": round(float(rates["usd_per_eur"].min()), 4),
        "highest_quote": round(float(rates["usd_per_eur"].max()), 4),
        "largest_daily_increase_pct": round(float(rates["daily_change_pct"].max()), 2),
        "largest_daily_decrease_pct": round(float(rates["daily_change_pct"].min()), 2),
        "daily_changes_over_2_std": int(rates["daily_change_pct"].abs().gt(2 * daily_std).sum()),
        "lowest_quote_drawdown_pct": round(float(rates["quote_drawdown_pct"].min()), 2),
    }
    return rates, monthly, metrics


def render(rates: pd.DataFrame, monthly: pd.DataFrame, metrics: dict, target: Path) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig = plt.figure(figsize=(15, 9), facecolor="#f3f7fb")
    grid = fig.add_gridspec(3, 2, height_ratios=[0.9, 2.2, 2.2], hspace=0.62, wspace=0.27)
    fig.text(0.055, 0.955, "DADOS FINANCEIROS", fontsize=22, weight="bold", color="#102a43")
    fig.text(0.055, 0.925, "Câmbio de referência do BCE · 2025 · dólares dos EUA por 1 euro",
             fontsize=10, color="#526b80")
    kpis = [("Observações", str(metrics["observations"])),
            ("Primeira cotação", f"{metrics['first_quote']:.4f}".replace(".", ",")),
            ("Última cotação", f"{metrics['last_quote']:.4f}".replace(".", ",")),
            ("Variação da cotação", f"{metrics['quote_change_pct']:+.2f}%".replace(".", ","))]
    axk = fig.add_subplot(grid[0, :]); axk.axis("off")
    for i, (name, value) in enumerate(kpis):
        x = 0.02 + i * 0.25
        axk.text(x, 0.76, name, transform=axk.transAxes, color="#526b80", fontsize=10)
        axk.text(x, 0.23, value, transform=axk.transAxes, color="#102a43", fontsize=20, weight="bold")
    axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1]),
            fig.add_subplot(grid[2, 0]), fig.add_subplot(grid[2, 1])]
    for ax in axes:
        ax.set_facecolor("white")
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.grid(axis="y", color="#e5edf4", zorder=0)
    axes[0].plot(rates["date"], rates["usd_per_eur"], color="#087e8b", lw=2.2)
    axes[0].set_title("Cotação diária", loc="left", weight="bold", color="#102a43")
    axes[0].set_ylabel("USD por EUR")
    axes[1].bar(monthly["monthly"], monthly["average_usd_per_eur"], color="#3d85c6", zorder=2)
    axes[1].set_title("Média mensal da cotação", loc="left", weight="bold", color="#102a43")
    axes[1].set_ylabel("USD por EUR")
    axes[1].set_ylim(0.95, max(monthly["average_usd_per_eur"]) + 0.03)
    axes[1].tick_params(axis="x", rotation=45, labelsize=8)
    axes[2].plot(rates["date"], rates["daily_change_pct"], color="#48a9a6", lw=1.1)
    axes[2].axhline(0, color="#596579", lw=0.8)
    axes[2].set_title("Variação entre observações", loc="left", weight="bold", color="#102a43")
    axes[2].set_ylabel("%")
    axes[3].plot(rates["date"], rates["volatility_20_obs_pct"], color="#d08c4b", lw=1.7)
    axes[3].set_title("Desvio padrão móvel anualizado", loc="left", weight="bold", color="#102a43")
    axes[3].set_ylabel("% · 20 observações")
    for ax in (axes[0], axes[2], axes[3]):
        ax.tick_params(axis="x", rotation=25, labelsize=8)
    fig.text(0.055, 0.025,
             "Fonte: Banco Central Europeu, EXR.D.USD.EUR.SP00.A. Cotação descritiva; não representa rendimento de investimento.",
             fontsize=9, color="#526b80")
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "ecb_usd_eur_2025.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "report")
    args = parser.parse_args()
    rates, monthly, metrics = analyze(load_rates(args.input))
    args.out.mkdir(exist_ok=True, parents=True)
    rates.to_csv(args.out / "processed_rates.csv", index=False)
    monthly.to_csv(args.out / "monthly_average.csv", index=False)
    (args.out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    render(rates, monthly, metrics, args.out / "dashboard.png")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
