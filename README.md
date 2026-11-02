# Mutuo + PIC vs No mutuo + PAC — Simulazione Monte Carlo

> ## ⚠️ DISCLAIMER — LEGGERE PRIMA DI USARE QUESTO REPOSITORY ⚠️
>
> **Questo progetto NON fornisce alcuna consulenza finanziaria, né alcun consiglio di investimento, fiscale o creditizio.**
> È un **modello statistico semplificato**, realizzato **esclusivamente a scopo didattico e divulgativo**, per esplorare — da un punto di vista quantitativo — gli effetti dell'inflazione, della volatilità dei rendimenti, della leva finanziaria e della tassazione sul confronto tra due strategie ipotetiche.
>
> **Il modello ha limiti importanti** (elencati nel manuale) e le sue ipotesi (rendimento atteso, volatilità, inflazione, aliquote fiscali, ecc.) sono impostate arbitrariamente dall'utente: **non rappresentano previsioni, stime affidabili o raccomandazioni**.
>
> I risultati **non devono in alcun modo essere usati per ispirare, motivare o giustificare decisioni finanziarie reali** (accendere un mutuo, investire, disinvestire, ecc.). Prima di qualunque decisione finanziaria, rivolgersi a un consulente finanziario, fiscale o creditizio abilitato e indipendente.
>
> **Prima di usare questo strumento è fortemente consigliato leggere per intero il [manuale](manuale_mutuo_vs_investimento.pdf) ed essere pienamente consapevoli dei limiti del modello.**
>
> L'autore non si assume alcuna responsabilità per decisioni prese, in tutto o in parte, sulla base dell'utilizzo di questo codice o dei suoi output.

---

## Cosa fa questo progetto

Il progetto confronta due strategie ipotetiche per l'acquisto di un immobile:

- **No mutuo + PAC**: si acquista senza indebitarsi e si investe mensilmente, tramite un piano di accumulo (PAC), l'importo che sarebbe stato destinato alla rata del mutuo.
- **Mutuo + PIC**: si accende un mutuo e si investe subito l'intero capitale disponibile in un'unica soluzione (PIC — Piano di Investimento Capitale), continuando a pagare la rata del mutuo.

Il modello tiene conto di variabili come tasso del mutuo, rendimento atteso e volatilità degli investimenti (rischio di sequenza), inflazione, detrazioni fiscali, tassazione delle plusvalenze e imposta di bollo. Per i dettagli completi su ipotesi e limiti, vedi il **manuale**.

## Struttura del repository

Il progetto è composto da due parti che lavorano insieme:

| Componente | Cosa fa |
|---|---|
| **`mutuo_vs_investimento.xlsx`** | Contiene tutti i parametri di input (foglio *Input*) ed esegue **una singola simulazione deterministica/casuale per volta**, utile per capire la meccanica del modello ed esplorare rapidamente uno scenario alla volta. |
| **`run_analysis.py`** (+ script correlati) | Esegue **N simulazioni Monte Carlo** (migliaia di scenari casuali) leggendo i parametri **direttamente dal file Excel**, e produce grafici e statistiche aggregate sulla distribuzione dei risultati. |

### 🔑 Punto fondamentale

- **L'Excel calcola una sola simulazione alla volta.** È utile per capire il modello, ma un singolo scenario non dice molto sulla dispersione statistica dei possibili esiti.
- **Gli script Python eseguono migliaia di simulazioni** (Monte Carlo), variando casualmente i rendimenti anno per anno secondo una distribuzione t-student, per costruire una visione statistica (percentili, win rate, distribuzione della differenza finale, ecc.).
- **Anche per lanciare le simulazioni Python è necessario impostare i parametri nel file Excel.** Lo script non ha una propria interfaccia di parametri: legge il foglio *Input* dell'xlsx. Quindi, prima di lanciare `run_analysis.py`, apri `mutuo_vs_investimento.xlsx`, imposta i parametri desiderati (importo, TAN, durata, rendimento atteso, deviazione standard, inflazione, tassazione, ecc.) e salva il file.

## Come avviare una simulazione Monte Carlo da terminale

1. Apri `mutuo_vs_investimento.xlsx` e imposta i parametri nel foglio *Input* (importo casa/mutuo, TAN, durata, rendimento atteso, deviazione standard, gradi di libertà, inflazione, detrazioni, tassazione plusvalenze, imposta di bollo, ecc.). Salva il file.
2. Da terminale, posizionati nella cartella del progetto e lancia:

```bash
python3 run_analysis.py --xlsx /percorso/al/file.xlsx --n 5000 --seed 42 --outdir /percorso/output
```

Parametri principali:

| Parametro | Significato |
|---|---|
| `--xlsx` | Percorso del file Excel da cui leggere i parametri di input |
| `--n` | Numero di simulazioni Monte Carlo da eseguire (es. 5000) |
| `--seed` | Seed per la riproducibilità dei risultati casuali |
| `--outdir` | Cartella in cui salvare i grafici e le tabelle generate |

Lo script produce 5 output grafici nella cartella indicata da `--outdir`:

1. **Fan chart** — evoluzione del portafoglio nel tempo, con percentili (5°–95°, 25°–75°, mediana)
2. **Istogramma della differenza finale** — distribuzione di (Mutuo+PIC − No mutuo+PAC) e win rate
3. **Patrimonio totale nel tempo** — netto vs lordo, incluse detrazioni/liquidità non reinvestita
4. **Riepilogo statistico** — numero simulazioni, mediane, differenza mediana, win rate, percentili
5. **Tabella dei rendimenti condizionati** — per anno e fascia di rendimento di mercato, con win rate e frequenza

Per la spiegazione dettagliata di come leggere ogni grafico, consulta la **Guida all'interpretazione dei risultati** inclusa nel repository.

## Documentazione

- 📘 **[Manuale d'uso del modello](manuale_mutuo_vs_investimento.pdf)** — spiega ipotesi, parametri e, soprattutto, i **limiti del modello**. Lettura fortemente consigliata prima di ogni utilizzo.
- 📊 **[Guida all'interpretazione dei risultati](Guida_all_interpretazione_dei_risultati.pdf)** — spiega come leggere i 5 grafici/tabelle prodotti da `run_analysis.py`.

## Limiti principali del modello (sintesi — vedi il manuale per l'elenco completo)

- Il rendimento atteso è un'**ipotesi** dell'utente, non una previsione: il rendimento reale con ogni probabilità sarà diverso.
- Non sono modellati eventi estremi "una tantum" (cigni neri) come categoria separata; gli esiti estremi emergono solo dalla casualità della distribuzione t-student.
- Non è modellata la correlazione tra anni di mercato negativo e rischio di perdita del reddito, né il costo psicologico del debito.
- Non si tiene conto di costi di transazione, commissioni specifiche degli strumenti, cambi di reddito imprevisti, surroga del mutuo, variazioni del tasso su mutui variabili.
- Il modello assume rendimento e tassazione identici nei due scenari (stesso portafoglio titoli sottostante).
- I rendimenti e l'inflazione sono calcolati su base annuale e poi distribuiti sui mesi.

## Licenza

Questo progetto è distribuito con licenza **MIT** — vedi il file [`LICENSE`](LICENSE) per il testo completo. In sintesi: puoi usare, copiare, modificare e ridistribuire il codice liberamente, anche a scopo commerciale, mantenendo la nota di copyright originale. Il software è fornito "così com'è", senza alcuna garanzia (vedi anche il disclaimer in cima a questo README).

---

> ## ⚠️ RICORDA ⚠️
>
> **Questo repository non costituisce consulenza finanziaria, fiscale o di alcun altro tipo.** È un esercizio statistico/didattico con un modello **semplificato e limitato**, pensato per osservare l'effetto di inflazione, volatilità e altre variabili sui risultati simulati — non per guidare scelte reali di indebitamento o investimento. Usalo solo dopo aver letto il manuale e aver compreso i suoi limiti, e non prendere decisioni finanziarie basandoti sui suoi output. Per decisioni reali, consulta un professionista abilitato e indipendente.
