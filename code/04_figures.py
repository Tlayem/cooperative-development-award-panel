#!/usr/bin/env python3
"""Figures. Draft-stamped unless run with --final (only after the author's verification).

fig1_obligations_by_fy.png   net obligations by fiscal year and programme
fig2_counties_reached.png    counties with an active award (recipient county), by FY and programme
fig3_top_states.png          cumulative net obligations, top 15 states (recipient state)
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from common import FIG, FY_END, FY_START, OUT

FINAL = "--final" in sys.argv
COL = {"RCDG": "#2a78d6", "SDGG": "#eb6834"}     # dataviz reference palette, slots 1-2
NAME = {"RCDG": "Rural Cooperative Development Grant (10.771)",
        "SDGG": "Socially Disadvantaged Groups Grant (10.871)"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5e0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})


def finish(fig, ax, name, caption, grid="y"):
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, -0.04, caption, fontsize=7.5, color=MUTED, ha="left", va="top")
    if not FINAL:
        fig.text(0.99, 0.98, "draft".upper(), fontsize=14, color="#c0392b", ha="right", va="top", weight="bold", alpha=0.8)
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def lines(df, value, ylabel, title, name, fmt):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for prog, g in df.groupby("programme"):
        g = g.sort_values("fy")
        ax.plot(g.fy, g[value], color=COL[prog], lw=2, marker="o", ms=4, label=NAME[prog])
        last = g.iloc[-1]
        ax.annotate(fmt(last[value]), (last.fy, last[value]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    ax.set_xlim(FY_START - 0.5, FY_END + 1.5)
    ax.set_xticks(range(FY_START, FY_END + 1, 2))
    ax.set_xlabel("Federal fiscal year"); ax.set_ylabel(ylabel); ax.set_title(title, loc="left", color=INK)
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    finish(fig, ax, name, "Source: USAspending.gov prime transactions, Assistance Listings 10.771 and 10.871. "
                          "Cooperative Development Award Panel (Adesiyan, T. F.).")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    p = pd.read_csv(OUT / "cdap_county_fy.csv", dtype={"county_fips": str, "state_fips": str})
    s = pd.read_csv(OUT / "cdap_state_fy.csv", dtype={"state_fips": str})
    by = p.groupby(["fy", "programme"]).agg(obl=("rec_obligations", "sum"), counties=("rec_any_award", "sum")).reset_index()
    st = s.groupby(["fy", "programme"]).rec_obligations_total.sum().reset_index(name="obl_all")
    by = by.merge(st, on=["fy", "programme"], how="left").fillna(0)
    by["obl_m"] = by.obl_all / 1e6
    lines(by, "obl_m", "Net obligations ($ million, nominal)", "Net obligations by fiscal year",
          "fig1_obligations_by_fy.png", lambda v: f"${v:.1f}m")
    lines(by, "counties", "Counties with an active award", "Counties reached (recipient county)",
          "fig2_counties_reached.png", lambda v: f"{v:.0f}")

    top = s.groupby("state").rec_obligations_total.sum().sort_values().tail(15) / 1e6
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(top.index, top.values, color=COL["RCDG"], height=0.7)
    for y, v in enumerate(top.values):
        ax.text(v, y, f" ${v:.1f}m", va="center", fontsize=8, color=INK)
    ax.set_xlabel("Cumulative net obligations ($ million, nominal)")
    ax.set_title(f"Top 15 recipient states, FY{FY_START}–FY{FY_END}, both programmes", loc="left", color=INK)
    finish(fig, ax, "fig3_top_states.png", "Source: USAspending.gov. Recipient state of each award.", grid="x")
    print("figures written", "final" if FINAL else "draft")


if __name__ == "__main__":
    main()
