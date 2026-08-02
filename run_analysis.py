"""
Esegue N simulazioni Monte Carlo del modello 'mutuo_vs_investimento.xlsx' e produce:
 1. Fan chart: andamento medio del portafoglio (entrambi gli scenari) con percentili nel tempo
 2. Istogramma della differenza finale (Mutuo+PIC - NoMutuo+PAC)
 3. Grafico del patrimonio TOTALE nel tempo (investito + liquidità non reinvestita) – netto vs lordo
 4. Pannello riassuntivo con statistiche chiave
 5. Tabella dei rendimenti condizionati per anno e fascia

Uso:
    python3 run_analysis.py --xlsx /path/al/file.xlsx --n 5000 --seed 42 --outdir /path/output
"""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
import pandas as pd
import os

from simulate import run_monte_carlo


def eur(x, _pos=None):
    return f'{x/1000:,.0f}k'.replace(',', '.')


def make_plots(res, outdir, n):
    p = res['p']
    months = p['months']
    years = p['years']
    x_years = np.arange(1, months + 1) / 12

    traj_pac, traj_pic = res['traj_pac'], res['traj_pic']
    final_pac, final_pic = res['final_pac'], res['final_pic']
    diff = final_pic - final_pac
    
    print("\n--- Verifica coerenza fan chart / riepilogo ---")
    print(f"Mediana ultimo punto PAC (traj):  {np.median(traj_pac[:, -1]):,.0f} €")
    print(f"Mediana finale PAC (final):       {np.median(final_pac):,.0f} €")

    print(f"Mediana ultimo punto PIC (traj):  {np.median(traj_pic[:, -1]):,.0f} €")
    print(f"Mediana finale PIC (final):       {np.median(final_pic):,.0f} €")
    print("---------------------------------------------\n")

    percentiles = [5, 25, 50, 75, 95]
    pac_pct = np.percentile(traj_pac, percentiles, axis=0)
    pic_pct = np.percentile(traj_pic, percentiles, axis=0)

    # ---------- 1. Fan chart ----------
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = {'pac': '#2563eb', 'pic': '#dc2626'}

    ax.fill_between(x_years, pac_pct[0], pac_pct[4], color=colors['pac'], alpha=0.12, label='NO mutuo+PAC 5°-95°pct')
    ax.fill_between(x_years, pac_pct[1], pac_pct[3], color=colors['pac'], alpha=0.25, label='NO mutuo+PAC 25°-75°pct')
    ax.plot(x_years, pac_pct[2], color=colors['pac'], lw=2, label='NO mutuo+PAC mediana')

    ax.fill_between(x_years, pic_pct[0], pic_pct[4], color=colors['pic'], alpha=0.12, label='Mutuo+PIC 5°-95°pct')
    ax.fill_between(x_years, pic_pct[1], pic_pct[3], color=colors['pic'], alpha=0.25, label='Mutuo+PIC 25°-75°pct')
    ax.plot(x_years, pic_pct[2], color=colors['pic'], lw=2, label='Mutuo+PIC mediana')

    ax.set_title(f'Andamento del portafoglio nel tempo — {n:,} simulazioni'.replace(',', '.'))
    ax.set_xlabel('Anni')
    ax.set_ylabel('Valore portafoglio (€, dopo bollo, ante vendita/tasse finali)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(eur))
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(f'{outdir}/1_fan_chart_percentili.png', dpi=150)
    plt.close(fig)

    # ---------- 2. Istogramma differenza finale ----------
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(diff, bins=60, color='#7c3aed', alpha=0.85, edgecolor='white', linewidth=0.3)
    ax.axvline(0, color='black', lw=1.2, ls='--')
    ax.axvline(np.median(diff), color='#f59e0b', lw=2, label=f'Mediana: €{np.median(diff):,.0f}'.replace(',', '.'))
    win_rate = (diff > 0).mean() * 100
    ax.set_title(f'Differenza finale: Mutuo+PIC − NO mutuo+PAC  (Mutuo+PIC vince nel {win_rate:.1f}% dei casi)')
    ax.set_xlabel('Differenza (€)')
    ax.set_ylabel('Frequenza')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(eur))
    ax.legend()
    ax.grid(alpha=0.25, axis='y')
    fig.tight_layout()
    fig.savefig(f'{outdir}/2_istogramma_differenza.png', dpi=150)
    plt.close(fig)

    # ---------- 3. Patrimonio TOTALE (investito + liquidità non reinvestita), netto vs lordo ----------
    total_net_pac, total_net_pic = res['total_net_pac'], res['total_net_pic']
    total_gross_pac, total_gross_pic = res['total_gross_pac'], res['total_gross_pic']

    net_pct_pac = np.percentile(total_net_pac, percentiles, axis=0)
    net_pct_pic = np.percentile(total_net_pic, percentiles, axis=0)
    gross_med_pac = np.median(total_gross_pac, axis=0)
    gross_med_pic = np.median(total_gross_pic, axis=0)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    ax.fill_between(x_years, net_pct_pac[0], net_pct_pac[4], color=colors['pac'], alpha=0.12, label='NO mutuo+PAC 5°-95°pct (netto)')
    ax.fill_between(x_years, net_pct_pac[1], net_pct_pac[3], color=colors['pac'], alpha=0.25, label='NO mutuo+PAC 25°-75°pct (netto)')
    ax.plot(x_years, net_pct_pac[2], color=colors['pac'], lw=2, label='NO mutuo+PAC mediana (netto)')
    ax.plot(x_years, gross_med_pac, color=colors['pac'], lw=1.3, ls='--', alpha=0.8, label='NO mutuo+PAC mediana (lordo)')

    ax.fill_between(x_years, net_pct_pic[0], net_pct_pic[4], color=colors['pic'], alpha=0.12, label='Mutuo+PIC 5°-95°pct (netto)')
    ax.fill_between(x_years, net_pct_pic[1], net_pct_pic[3], color=colors['pic'], alpha=0.25, label='Mutuo+PIC 25°-75°pct (netto)')
    ax.plot(x_years, net_pct_pic[2], color=colors['pic'], lw=2, label='Mutuo+PIC mediana (netto)')
    ax.plot(x_years, gross_med_pic, color=colors['pic'], lw=1.3, ls='--', alpha=0.8, label='Mutuo+PIC mediana (lordo)')

    ax.set_title(f'Patrimonio TOTALE nel tempo (investito + liquidità non reinvestita, aggiunta quando matura) — {n:,} simulazioni'.replace(',', '.'))
    ax.set_xlabel('Anni')
    ax.set_ylabel('Valore (€)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(eur))
    ax.legend(loc='upper left', fontsize=8, ncol=2)
    ax.grid(alpha=0.25)
    fig.text(0.5, 0.01,
              'Netto = plusvalenza tassata "come se si vendesse oggi" (mark-to-market) + liquidità già maturata (detrazioni/risparmio non reinvestiti).\n'
              'Lordo (tratteggiato) = stesso patrimonio ma senza sottrarre la tassa sulla plusvalenza maturata.',
              ha='center', fontsize=8, style='italic', color='#555')
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(f'{outdir}/3_patrimonio_totale.png', dpi=150)
    plt.close(fig)

    # ---------- 4. Pannello riassuntivo ----------
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis('off')
    rows = [
        ('Simulazioni', f'{n:,}'.replace(',', '.')),
        ('NO mutuo+PAC — mediana finale', f'€{np.median(final_pac):,.0f}'.replace(',', '.')),
        ('Mutuo+PIC — mediana finale', f'€{np.median(final_pic):,.0f}'.replace(',', '.')),
        ('Differenza — mediana', f'€{np.median(diff):,.0f}'.replace(',', '.')),
        ('P(Mutuo+PIC migliore)', f'{win_rate:.1f}%'),
        ('NO mutuo+PAC — 5°/95° pct finale', f'€{np.percentile(final_pac,5):,.0f} / €{np.percentile(final_pac,95):,.0f}'.replace(',', '.')),
        ('Mutuo+PIC — 5°/95° pct finale', f'€{np.percentile(final_pic,5):,.0f} / €{np.percentile(final_pic,95):,.0f}'.replace(',', '.')),
    ]
    table = ax.table(cellText=[[k, v] for k, v in rows], colWidths=[0.6, 0.4], loc='center', cellLoc='left')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.9)
    ax.set_title('Riepilogo Monte Carlo', fontsize=13, pad=20)
    fig.tight_layout()
    fig.savefig(f'{outdir}/4_riepilogo.png', dpi=150)
    plt.close(fig)

    return dict(win_rate=win_rate, median_diff=np.median(diff),
                median_pac=np.median(final_pac), median_pic=np.median(final_pic))


def make_return_condition_table(res, outdir, n):
    annual_returns = res['annual_returns']
    final_pac = res['final_pac']
    final_pic = res['final_pic']
    n_sim = len(final_pac)
    n_years = annual_returns.shape[1]

    STEP = 5
    LIMIT = 40
    bins = [-np.inf]
    labels = [f'< -{LIMIT}%']
    for v in range(-LIMIT, LIMIT, STEP):
        bins.append(v)
        labels.append(f'{v} / {v+STEP}')
    bins.append(LIMIT)
    bins.append(np.inf)
    labels.append(f'≥ {LIMIT}%')

    cell_data = {}

    for year in range(n_years):
        ret_perc = annual_returns[:, year] * 100
        cats = pd.cut(ret_perc, bins=bins, labels=labels, right=False, include_lowest=True)
        for idx, label in enumerate(labels):
            mask = (cats == label)
            count = np.sum(mask)
            if count == 0:
                cell = {'N': 0, 'freq': 0.0, 'delta_med': np.nan, 'win_rate': np.nan}
            else:
                diff = final_pic[mask] - final_pac[mask]
                cell = {
                    'N': count,
                    'freq': count / n_sim * 100,
                    'delta_med': np.median(diff),
                    'win_rate': np.mean(diff > 0) * 100
                }
            cell_data[(year, idx)] = cell

    n_rows = len(labels)
    n_cols = n_years

    cell_width = 0.8
    cell_height = 0.6
    fig_width = cell_width * (n_cols + 1) + 1
    fig_height = cell_height * (n_rows + 1) + 1

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, fig_width)
    ax.set_ylim(0, fig_height)
    ax.axis('off')

    def draw_cell(x, y, width, height, text_lines, bg_color='white', text_color='black', fontsize=8):
        rect = Rectangle((x, y), width, height, facecolor=bg_color, edgecolor='black', linewidth=0.5)
        ax.add_patch(rect)
        for i, line in enumerate(text_lines):
            ax.text(x + width/2, y + height - 0.1 - i*0.12, line,
                    ha='center', va='top', fontsize=fontsize, color=text_color, wrap=True)

    # Intestazioni
    for col, year in enumerate(range(n_years)):
        x = cell_width * (col + 1) + 0.5
        y = fig_height - cell_height - 0.2
        draw_cell(x, y, cell_width, cell_height, [f'Anno {year+1}'], bg_color='lightgray', fontsize=10)

    for row, label in enumerate(labels):
        x = 0.5
        y = fig_height - cell_height - 0.2 - (row+1)*cell_height
        draw_cell(x, y, cell_width, cell_height, [label], bg_color='lightgray', fontsize=9)

    # Popolamento celle
    for row, label in enumerate(labels):
        for col, year in enumerate(range(n_years)):
            cell = cell_data[(year, row)]
            x = cell_width * (col + 1) + 0.5
            y = fig_height - cell_height - 0.2 - (row+1)*cell_height

            win = cell['win_rate']
            if np.isnan(win):
                bg = 'white'
            elif win < 40:
                bg = 'lightcoral'
            elif win < 60:
                bg = 'white'
            else:
                bg = 'lightgreen'

            if cell['N'] == 0:
                lines = ["N = 0", "f = 0%", "Δ = —", "Win = —"]
                bg = 'white'
            else:
                def fmt_eur(v):
                    if np.isnan(v):
                        return "—"
                    if abs(v) < 1e6:
                        return f"{v/1000:.1f} k€"
                    else:
                        return f"{v/1000:.0f} k€"
                lines = [
                    f"N = {cell['N']}",
                    f"f = {cell['freq']:.1f}%",
                    f"Δ = {fmt_eur(cell['delta_med'])}",
                    f"Win = {cell['win_rate']:.0f}%"
                ]

            draw_cell(x, y, cell_width, cell_height, lines, bg_color=bg, fontsize=7)

    ax.text(fig_width/2, fig_height - 0.1, "Tabella rendimenti condizionati per anno e fascia",
            ha='center', va='top', fontsize=14, fontweight='bold')

    plt.tight_layout()
    outfile = os.path.join(outdir, "5_tabella_rendimenti_condizionati.png")
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Tabella condizionata salvata in {outfile}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx', default='/mnt/user-data/uploads/mutuo_vs_investimento.xlsx')
    ap.add_argument('--n', type=int, default=5000)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--outdir', default='.')
    args = ap.parse_args()

    res = run_monte_carlo(args.xlsx, N=args.n, seed=args.seed)
    stats = make_plots(res, args.outdir, args.n)
    make_return_condition_table(res, args.outdir, args.n)
    print(stats)