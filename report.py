"""주간 리포트: 주차장별 잔여석 추이 그래프 생성

사용법:
  python report.py                 # 최근 7일
  python report.py --all           # 수집 전체 기간
  python report.py --start 2026-10-14 --end 2026-10-21
결과: reports/<시작>_<끝>.png  (+ 주차장별 요약표 .csv)
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "gimhae_parking.csv"
OUT_DIR = ROOT / "reports"

LINE = "#2a78d6"      # 잔여석 선
FILL = "#2a78d6"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


def set_korean_font():
    for name in ("Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic"):
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def lot_order(name):
    # P1, P2, P3 ... 순서로 정렬, 나머지는 뒤로
    for i in range(1, 10):
        if f"P{i}" in name.upper() or f"제{i}" in name:
            return (i, name)
    return (99, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["t"] = pd.to_datetime(df["collected_at_kst"])
    df["available"] = pd.to_numeric(df["available"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")

    if not a.all:
        end = pd.to_datetime(a.end) + timedelta(days=1) if a.end else df["t"].max() + timedelta(minutes=1)
        start = pd.to_datetime(a.start) if a.start else end - timedelta(days=7)
        df = df[(df["t"] >= start) & (df["t"] < end)]
    if df.empty:
        raise SystemExit("해당 기간 데이터가 없습니다.")

    lots = sorted(df["lot"].unique(), key=lot_order)
    set_korean_font()

    fig, axes = plt.subplots(len(lots), 1, figsize=(12, 3.0 * len(lots)),
                             sharex=True, facecolor=SURFACE)
    if len(lots) == 1:
        axes = [axes]

    summary = []
    for ax, lot in zip(axes, lots):
        d = df[df["lot"] == lot].sort_values("t")
        total = d["total"].dropna().max()
        ax.set_facecolor(SURFACE)
        ax.fill_between(d["t"], d["available"], color=FILL, alpha=0.12, linewidth=0)
        ax.plot(d["t"], d["available"], color=LINE, linewidth=2)

        # 최저점(가장 붐빈 시각) 표시
        lo = d.loc[d["available"].idxmin()]
        ax.plot(lo["t"], lo["available"], "o", color=LINE, markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"최저 {int(lo['available']):,}면\n{lo['t']:%m/%d %H시}",
                    (lo["t"], lo["available"]), xytext=(10, 18), textcoords="offset points",
                    fontsize=9, color=INK2,
                    bbox=dict(boxstyle="round,pad=0.3", fc=SURFACE, ec=GRID, lw=0.8))

        title = f"{lot}  잔여석"
        if pd.notna(total):
            title += f"  (전체 {int(total):,}면)"
            ax.set_ylim(0, total * 1.05)
        else:
            ax.set_ylim(bottom=0)
        ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.grid(axis="x", color=GRID, linewidth=0.5, alpha=0.6)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=9, length=0)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

        d2 = d.assign(hour=d["t"].dt.hour)
        by_hour = d2.groupby("hour")["available"].mean()
        summary.append({
            "주차장": lot,
            "전체면수": int(total) if pd.notna(total) else None,
            "평균 잔여": round(d["available"].mean()),
            "최저 잔여": int(lo["available"]),
            "최저 시각": f"{lo['t']:%m/%d %H:%M}",
            "평균적으로 가장 붐비는 시간대": f"{int(by_hour.idxmin())}시",
            "평균적으로 가장 여유 있는 시간대": f"{int(by_hour.idxmax())}시",
            "기록 수": len(d),
        })

    axes[-1].xaxis.set_major_locator(mdates.DayLocator())
    axes[-1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: (lambda d: f"{d:%m/%d}({'월화수목금토일'[d.weekday()]})")(mdates.num2date(v))))
    axes[-1].xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))

    s, e = df["t"].min(), df["t"].max()
    fig.suptitle(f"김해공항 주차장 잔여석 추이  {s:%Y-%m-%d} ~ {e:%Y-%m-%d}  (1시간 간격)",
                 x=0.01, ha="left", fontsize=14, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    OUT_DIR.mkdir(exist_ok=True)
    stem = f"{s:%Y%m%d}_{e:%Y%m%d}"
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=150, facecolor=SURFACE)
    pd.DataFrame(summary).to_csv(OUT_DIR / f"{stem}_summary.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(summary).to_string(index=False))
    print(f"저장: reports/{stem}.png")


if __name__ == "__main__":
    main()
