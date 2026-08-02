"""
Replica fedele (vettorizzata, numpy) del modello Excel 'mutuo_vs_investimento.xlsx'.
Legge i parametri direttamente dal foglio 'Input' cosi' restano sincronizzati col file.

Logica replicata 1:1 dalle formule dei fogli: Input, Mutuo, Detrazione, PAC, PIC, Confronto, Sequenza.
"""
import numpy as np
import openpyxl


def load_params(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    inp = wb['Input']
    p = dict(
        P0=inp['C5'].value,
        tan=inp['C6'].value,
        r_mkt=inp['C7'].value,
        years=inp['C8'].value,
        applica_detrazione=inp['C16'].value,
        aliquota_irpef=inp['C17'].value,
        tetto_interessi=inp['C18'].value,
        reinvesti_detrazioni=inp['C19'].value,
        aliquota_plusvalenza=inp['C25'].value,
        applica_sequenza=inp['C32'].value,
        vol=inp['C33'].value,
        df=inp['C34'].value,
        applica_bollo=inp['C40'].value,
        aliquota_bollo=inp['C41'].value,
        applica_inflazione=inp['C48'].value,
        inflazione=inp['C49'].value,
        indicizza_pac=inp['C50'].value,
        reinvesti_risparmio=inp['C56'].value,
    )
    p['months'] = p['years'] * 12
    p['i_mutuo'] = (1 + p['tan']) ** (1 / 12) - 1
    p['i_mkt'] = (1 + p['r_mkt']) ** (1 / 12) - 1
    # rata = -PMT(i, n, P0)  (standard annuity payment)
    i, n, P0 = p['i_mutuo'], p['months'], p['P0']
    p['rata'] = P0 * i / (1 - (1 + i) ** (-n)) if i != 0 else P0 / n
    return p


def mortgage_schedule(p):
    """Deterministic amortization schedule -> monthly interest array + interest paid per year."""
    months, i, rata, P0 = p['months'], p['i_mutuo'], p['rata'], p['P0']
    interest = np.zeros(months)
    debt = P0
    for m in range(months):
        interest[m] = debt * i
        principal = rata - interest[m]
        debt -= principal
    interest_per_year = interest.reshape(p['years'], 12).sum(axis=1)
    return interest_per_year


def detrazione_per_year(p, interest_per_year):
    if not p['applica_detrazione']:
        return np.zeros(p['years'])
    capped = np.minimum(interest_per_year, p['tetto_interessi'])
    return capped * p['aliquota_irpef']


def detrazione_schedule_months(p, detrazione_year):
    """R[month] (1-indexed as R[m-1]): rimborso incassato al mese m, con ritardo 18 mesi,
    eventuali detrazioni che maturerebbero oltre la durata vengono dumped all'ultimo mese."""
    months, years = p['months'], p['years']
    R = np.zeros(months)
    leftover = 0.0
    for y in range(1, years + 1):
        m = y * 12 + 18
        if m <= months:
            R[m - 1] += detrazione_year[y - 1]
        else:
            leftover += detrazione_year[y - 1]
    R[months - 1] += leftover
    return R


def sample_monthly_rates(p, N, rng):
    """Genera, per N simulazioni, la sequenza mensile di rendimento di mercato.
    Replica il foglio 'Sequenza': se applica_sequenza=0, rendimento costante i_mkt ogni mese."""
    months, years = p['months'], p['years']
    if not p['applica_sequenza']:
        return np.full((N, months), p['i_mkt'])

    df = max(p['df'], 3)
    raw = p['r_mkt'] + rng.standard_t(df, size=(N, years)) * p['vol'] / np.sqrt(df / (df - 2))

    invalid = (1 + raw <= 0).any(axis=1) | (np.prod(1 + raw, axis=1) <= 0)
    tries = 0
    while invalid.any() and tries < 50:
        n_bad = invalid.sum()
        raw[invalid] = p['r_mkt'] + rng.standard_t(df, size=(n_bad, years)) * p['vol'] / np.sqrt(df / (df - 2))
        invalid = (1 + raw <= 0).any(axis=1) | (np.prod(1 + raw, axis=1) <= 0)
        tries += 1

    g_raw = np.prod(1 + raw, axis=1) ** (1 / years) - 1
    factor = (1 + p['r_mkt']) / (1 + g_raw)
    adj = (1 + raw) * factor[:, None] - 1          # rendimento annuo rettificato, per anno
    monthly_year = (1 + adj) ** (1 / 12) - 1        # tasso mensile equivalente, per anno
    monthly = np.repeat(monthly_year, 12, axis=1)   # espande a 360 mesi
    return monthly, adj  # adj = rendimenti annui effettivi (per l'istogramma dei rendimenti)


def run_pac(p, monthly_rate):
    """Scenario NO mutuo + PAC. monthly_rate shape (N, months). Ritorna traiettoria (N, months),
    valore netto finale (N,) e la traiettoria della base di costo (serve per calcolare la
    plusvalenza 'mark-to-market' mese per mese, non solo all'ultimo mese)."""
    N, months = monthly_rate.shape
    rata, bollo_on, bollo_rate = p['rata'], p['applica_bollo'], p['aliquota_bollo']
    cg_rate = p['aliquota_plusvalenza']
    infl_on, infl, index_pac = p['applica_inflazione'], p['inflazione'], p['indicizza_pac']

    bal = np.zeros(N)
    cost_base = np.zeros(N)
    traj = np.zeros((N, months))       # valore "G" (dopo bollo, ante vendita) mese per mese
    costbase_traj = np.zeros((N, months))
    final_net = np.zeros(N)

    for m in range(1, months + 1):
        B = rata * ((1 + infl) ** ((m - 1) // 12) if (infl_on and index_pac) else 1.0)
        rm = monthly_rate[:, m - 1]
        D = (bal + B) * rm
        E = bal + D + B
        F = E * bollo_rate if (bollo_on and m % 12 == 0) else 0.0
        G = E - F
        I = cost_base + B
        if m == months:
            K, L = G, I
            M = np.maximum(K - L, 0.0)
            Ntax = M * cg_rate

            if N > 1:
                print("\nPAC")
                print(f"Patrimonio lordo mediano : {np.median(K):,.0f} €")
                print(f"Base fiscale mediana    : {np.median(L):,.0f} €")
                print(f"Plusvalenza mediana     : {np.median(M):,.0f} €")
                print(f"Tassa mediana           : {np.median(Ntax):,.0f} €")

            Q = K - Ntax
            final_net = Q
        else:
            O, P = G, I
        traj[:, m - 1] = G
        costbase_traj[:, m - 1] = I
        bal, cost_base = O, P
    return traj, final_net, costbase_traj


def run_pic(p, monthly_rate, detrazione_year, R_months):
    N, months = monthly_rate.shape
    P0, rata = p['P0'], p['rata']
    bollo_on, bollo_rate = p['applica_bollo'], p['aliquota_bollo']
    cg_rate = p['aliquota_plusvalenza']
    infl_on, infl = p['applica_inflazione'], p['inflazione']
    reinvest_detr = p['reinvesti_detrazioni']
    reinvest_risp = p['reinvesti_risparmio']

    bal = np.full(N, float(P0))
    cost_base = np.full(N, float(P0))
    S_cum = np.zeros(N)   # detrazioni NON reinvestite: liquidità a parte, svalutata dall'inflazione finché resta ferma
    X_cum = np.zeros(N)   # risparmio da inflazione NON reinvestito: idem
    infl_month_factor = (1 + infl) ** (1 / 12) if infl_on else 1.0
    traj = np.zeros((N, months))
    costbase_traj = np.zeros((N, months))
    S_traj = np.zeros((N, months))   # S_cum mese per mese (per il grafico di patrimonio totale)
    X_traj = np.zeros((N, months))   # X_cum mese per mese
    final_net = np.zeros(N)

    for m in range(1, months + 1):
        rm = monthly_rate[:, m - 1]
        C = bal * rm
        Rm = R_months[m - 1]  # deterministico, uguale per tutte le simulazioni
        D = Rm if reinvest_detr else 0.0
        V = rata * ((1 + infl) ** ((m - 1) / 12) - 1) if infl_on else 0.0
        W = V if reinvest_risp else 0.0
        E = bal + C + D + W
        F = E * bollo_rate if (bollo_on and m % 12 == 0) else 0.0
        G = E - F
        I = cost_base + D + W
        if m == months:
            K, L = G, I
            M = np.maximum(K - L, 0.0)
            Ntax = M * cg_rate

            if N > 1:
                print("\nPIC")
                print(f"Patrimonio lordo mediano : {np.median(K):,.0f} €")
                print(f"Base fiscale mediana    : {np.median(L):,.0f} €")
                print(f"Plusvalenza mediana     : {np.median(M):,.0f} €")
                print(f"Tassa mediana           : {np.median(Ntax):,.0f} €")

            Q = K - Ntax
            final_net = Q
        else:
            O, P = G, I
        # La liquidità già accumulata resta ferma per un altro mese: perde potere d'acquisto
        # (si svaluta di 1 mese di inflazione) prima che si aggiunga l'eventuale nuovo importo
        # appena maturato (che invece arriva a valore pieno, non ancora eroso).
        S_cum = S_cum / infl_month_factor + (Rm if not reinvest_detr else 0.0)
        X_cum = X_cum / infl_month_factor + (V if not reinvest_risp else 0.0)
        traj[:, m - 1] = G
        costbase_traj[:, m - 1] = I
        S_traj[:, m - 1] = S_cum
        X_traj[:, m - 1] = X_cum
        bal, cost_base = O, P

    final_total = final_net + S_cum + X_cum
    return traj, final_total, costbase_traj, S_traj, X_traj


def run_monte_carlo(path, N=2000, seed=42):
    p = load_params(path)
    rng = np.random.default_rng(seed)

    interest_per_year = mortgage_schedule(p)
    detrazione_year = detrazione_per_year(p, interest_per_year)
    R_months = detrazione_schedule_months(p, detrazione_year)

    result = sample_monthly_rates(p, N, rng)
    if p['applica_sequenza']:
        monthly_rate, annual_returns = result
    else:
        monthly_rate = result
        annual_returns = np.full((N, p['years']), p['r_mkt'])

    traj_pac, final_pac, costbase_pac = run_pac(p, monthly_rate)
    traj_pic, final_pic, costbase_pic, S_traj, X_traj = run_pic(p, monthly_rate, detrazione_year, R_months)

    cg_rate = p['aliquota_plusvalenza']

    # Patrimonio "mark-to-market": se liquidassi (pagando la plusvalenza maturata) in quel preciso mese.
    net_mtm_pac = traj_pac - np.maximum(traj_pac - costbase_pac, 0.0) * cg_rate
    net_mtm_pic = traj_pic - np.maximum(traj_pic - costbase_pic, 0.0) * cg_rate

    # Patrimonio totale = investito + liquidità non reinvestita, aggiunta man mano che matura
    # (non solo a fine periodo). Per il PAC non esiste liquidità fuori dal portafoglio investito.
    cash_pic = S_traj + X_traj
    total_gross_pac = traj_pac.copy()
    total_net_pac = net_mtm_pac.copy()
    total_gross_pic = traj_pic + cash_pic
    total_net_pic = net_mtm_pic + cash_pic

    return dict(
        p=p,
        traj_pac=traj_pac, traj_pic=traj_pic,
        final_pac=final_pac, final_pic=final_pic,
        costbase_pac=costbase_pac, costbase_pic=costbase_pic,
        S_traj=S_traj, X_traj=X_traj, cash_pic=cash_pic,
        total_gross_pac=total_gross_pac, total_net_pac=total_net_pac,
        total_gross_pic=total_gross_pic, total_net_pic=total_net_pic,
        annual_returns=annual_returns,
    )


if __name__ == '__main__':
    res = run_monte_carlo('/mnt/user-data/uploads/mutuo_vs_investimento.xlsx', N=5, seed=0)
    print('PAC finale (5 sim):', res['final_pac'])
    print('PIC finale (5 sim):', res['final_pic'])
