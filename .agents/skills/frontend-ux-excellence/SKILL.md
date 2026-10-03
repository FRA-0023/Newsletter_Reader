---
name: frontend-ux-excellence
description: >
  MUST USE THIS SKILL whenever progettando, sviluppando, revisionando o eseguendo il refactoring di interfacce utente (UI), componenti frontend interattivi, flussi UX, layout web o applicazioni client-side.
  Attiva per keyword o intenti concreti: "frontend", "interfaccia utente", "ui design", "ux", "design system", "componenti web", "accessibilità ui", "stati componenti", "microinterazioni", "mobile-first", "core web vitals".
  Attiva anche quando l'utente richiede di creare schermate, form, dashboard, modali o pagine web con standard professionali e non banali.
  NON attivare per la generazione di singoli widget HTML/Tailwind usa-e-getta inline nella chat senza logica applicativa (usa generative_ui), né per logica backend/API priva di frontend, né per la sola stesura di copy testuale senza interfaccia (usa copywriting-master-strategy).
tags: [frontend, ux, ui, dev-backend]
---

> ℹ️ **Skill in esecuzione**: `frontend-ux-excellence`
> *Questa skill si è attivata per guidare la progettazione e implementazione di interfacce utente ad alta densità di usabilità, accessibilità e robustezza interattiva.*

**REGOLA DI OUTPUT OBBLIGATORIA**: quando questa skill è attiva, includi sempre all'inizio della tua risposta il blocco di callout soprastante.

# Frontend UX Excellence

## Il problema che questa skill risolve
Elimina il pattern tipico delle interfacce generate da AI: layout statici e banali, stati interattivi assenti o impliciti (click a vuoto, doppie submit), spaziatura incoerente con pixel arbitrari, contrasto inaccessibile, spinner generici bloccanti e form fragili. Trasforma ogni implementazione frontend in un sistema robusto, reattivo, accessibile (WCAG 2.2 AA) e cognitivamente fluido.

---

## 1. Matrice delle Leggi Cognitive
Ogni decisione di layout e interazione discende da vincoli cognitivi oggettivi, mai da preferenze estetiche arbitrarie.

| Legge | Vincolo Operativo | Regola Implementativa |
|---|---|---|
| **Jakob's Law** | Standard de facto degli utenti | Navbar in alto/sidebar a sinistra, carrello/profilo in alto a destra. Zero pattern "originali" senza guadagno provato. |
| **Fitts's Law** | Tempo target = $f(\text{distanza}, \text{dimensione})$ | CTA primaria ampia e posizionata lungo il percorso naturale dello sguardo/dita. Bottoni critici non periferici. |
| **Hick's Law** | Tempo di scelta cresce con $N$ opzioni | Menu con $>7\text{--}9$ voci $\rightarrow$ raggruppamento semantico o progressive disclosure. Massimo 1-2 azioni primarie. |
| **Miller's Law** | Memoria di lavoro limitata a $7 \pm 2$ chunk | Form o wizard complessi divisi in step sequenziali numerati; mai schermate uniche a scroll infinito. |
| **Von Restorff** | Unicità visiva focalizza l'attenzione | Esattamente **una** CTA primaria ad alto contrasto visivo per viewport. Nessuna competizione tra pulsanti. |
| **Peak-End Rule** | Ricordo ancorato a picco ed epilogo | Design ossessivo per onboarding-completato, checkout-success ed error-recovery (celebrazione o via d'uscita). |
| **Doherty Threshold** | Flusso cognitivo interrotto sopra i 400ms | Risposta visiva percepita entro 400ms (feedback immediato, optimistic UI, micro-loader). |

---

## 2. Spaziatura, Griglia & Gerarchia Tipografica

| Proprietà | Vincolo Assoluto | Implementazione |
|---|---|---|
| **Griglia Spaziale** | Multipli rigorosi di **8pt** (o **4pt** per micro-spazi) | Padding, margin, gap e altezze solo: 4, 8, 12, 16, 24, 32, 48, 64px. |
| **Scala Tipografica** | Ratio modulare 1.200 (Minor Third) o 1.250 (Major Third) | Max 5-6 taglie totali (es. 12, 14, 16, 20, 24, 32px). |
| **Line-Height** | Proporzione ergonomica di lettura | `1.4`–`1.6` per body text; `1.1`–`1.3` per headline e titoli grandi. |
| **Famiglie Font** | Massimo 2 famiglie per progetto | 1 Sans/Serif primario per UI + eventuale 1 Monospace per dati/tabelle/codice. |

```
❌ margin: 13px; padding: 22px; font-size: 17px; line-height: 1.15; (valori casuali)
✅ gap: 16px; padding: 24px; font-size: 16px; line-height: 1.5; font-family: var(--font-sans);
```

---

## 3. Color System & Contrasto Semantico

| Token Semantico | Utilizzo Vincolante | Requisito Contrasto (WCAG 2.2 AA) |
|---|---|---|
| `var(--bg-surface)` / `var(--text-primary)` | Superficie base e testo di lettura | Minimo **4.5:1** rispetto allo sfondo. |
| `var(--text-muted)` / `var(--border-subtle)` | Dettagli secondari e bordi di confine | Minimo **3.0:1** per componenti UI e icone informative. |
| `var(--interactive-primary)` | CTA principale e stati attivi | Minimo **3.0:1** per elementi grafici interattivi; 4.5:1 sul testo interno. |
| `var(--feedback-error/success/warning)` | Messaggi di stato e convalida | Contrasto 4.5:1 con fondo; non usare SOLO il colore (affiancare icona/testo). |

- **Palette Luminosa**: definire scale a 9-10 step (`50`–`900`) per ogni tinta semantica per abilitare il tema dark con scambio token 1:1, senza ricalcolare i contrasti.
```
❌ color: #737373; background: #e5e5e5; (contrasto 2.1:1 - fallimento WCAG AA)
✅ color: var(--color-text-secondary); (garantito ≥ 4.5:1 con token verificati light/dark)
```

---

## 4. Matrice dei 9 Stati Obbligatori dei Componenti
Ogni componente interattivo (button, input, select, card cliccabile) DEVE prevedere l'implementazione esplicita dei seguenti stati:

| Stato | Trigger | Comportamento Visivo & Accessibilità |
|---|---|---|
| **1. Default** | A riposo | Aspetto base stabile, target minimo touch garantito. |
| **2. Hover** | Cursore sopra | Transizione colore/superficie (150-200ms); non mostrare su dispositivi touch. |
| **3. Focus** | Tab/navigazione tastiera | Ring o outline ad alto contrasto (`outline-offset: 2px`). Mai `outline: none` isolato. |
| **4. Active** | Pressione/clic in corso | Leggera contrazione di scala (`scale(0.98)`) o abbassamento tonale. |
| **5. Disabled** | Azione non disponibile | `opacity: 0.5`, `cursor: not-allowed`, `aria-disabled="true"`. Rimuovere listener click. |
| **6. Loading** | Richiesta server asincrona | Disabilitazione interazione, inline spinner o skeleton, preserving layout (no layout shift). |
| **7. Error** | Convalida fallita/eccezione | Bordo d'errore semantico, messaggio esplicito associato via `aria-describedby`. |
| **8. Empty** | Nessun dato presente | Visuale dedicata, testo contestualizzato e CTA primaria per sbloccare lo stato. |
| **9. Success** | Azione completata | Conferma visiva (icona/check), testo di successo prima del ripristino o redirect. |

```
❌ <button onClick={submit}>Invia</button> (nessun feedback al click: l'utente ripete il click -> submit duplicata)
✅ <button disabled={isLoading} aria-busy={isLoading} className="...">
     {isLoading ? <Spinner size="sm" aria-hidden="true" /> : <SendIcon />}
     <span>{isLoading ? "Invio in corso..." : "Invia richiesta"}</span>
   </button>
```

---

## 5. Microinterazioni, Motion & Transizioni

- **Budget Temporale**: transizioni UI tra **150ms** e **300ms** (sotto 100ms è invisibile; sopra 400ms induce sensazione di lag).
- **Curva di Easing Funzionale**:
  - Elementi in ingresso nel viewport: `ease-out` (decelerazione naturale all'arrivo).
  - Elementi in uscita dal viewport: `ease-in` (accelerazione in allontanamento).
  - Micro-cambiamenti di stato (hover, toggle): `ease` o `cubic-bezier(0.4, 0, 0.2, 1)`. **Mai `linear`** su animazioni UI.
- **Supporto Accessibilità Ridotta**:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```
```
❌ Animazioni continue a rotazione puramente decorative; transizioni di 600ms con curve lineari.
✅ Transizione mirata (200ms ease-out) su accordion che spiega causa-effetto; motion disattivabile.
```

---

## 6. Performance Percepita & Core Web Vitals

| Strategia | Scopo | Implementazione Tecnica |
|---|---|---|
| **Skeleton Screen** | Azzeramento attesa percepita su layout noti | Skeleton pulsante con dimensioni esatte dei dati in arrivo; vietati spinner centrali isolati su feed/tabelle. |
| **Optimistic UI** | Azioni ad alta confidenza (like, switch) | Aggiornamento UI immediato al click; invio asincrono in background; rollback con notifica toast solo in errore. |
| **LCP (< 2.5s)** | Rendering rapido contenuto primario | Prioritizzare hero images (`fetchpriority="high"`), prefetch font critici, evitare blocco CSS. |
| **INP (< 200ms)** | Interattività istantanea | Decomprimere task lunghi sul main thread (`requestIdleCallback`, web worker), debouncing su input. |
| **CLS (< 0.1)** | Stabilità visiva totale | Dimensioni esplicite (`width`/`height` o `aspect-ratio`) su tutte le immagini, iframe e container dinamici. |

```
❌ Mostrare schermo bianco con spinner per 2 secondi durante il caricamento di una card prodotto.
✅ Mostrare skeleton strutturato 1:1; render istantaneo dei dati appena ricevuti senza layout shift (CLS = 0).
```

---

## 7. Accessibilità Strutturale (WCAG 2.2 Standard)

| Area | Requisito Minimo | Validazione Operativa |
|---|---|---|
| **Touch Target** | Minimo **44x44px** (iOS) / **48x48dp** (Android) | Minimo assoluto WCAG 2.2: 24x24px. Padding trasparente su icone per espandere il target. |
| **Tastiera & Focus** | Parità 100% tastiera vs mouse | Tab order sequenziale logico, Focus Trap vincolante su modali/drawer, esc per chiusura. |
| **HTML Semantico** | Zero div/span con listener click | `<button>` per azioni, `<a href>` per navigazione, `<form>`, `<fieldset>`, `<legend>`, `<dialog>`. |
| **ARIA Necessario** | ARIA solo se HTML nativo non basta | `aria-expanded`, `aria-controls`, `aria-live="polite"` per annunci dinamici, `aria-label` su bottoni icona. |

```
❌ <div onClick={openModal} className="btn">Opzioni</div> (inaccessibile da tastiera, zero semantics)
✅ <button type="button" aria-haspopup="dialog" aria-expanded={isOpen} onClick={openModal}>Opzioni</button>
```

---

## 8. Error Handling, Empty States & Ciclo Fetch

Ogni operazione asincrona o form deve gestire la triade di stati in modo trasparente e azionabile:

```
                  ┌───────────────┐
                  │ 1. Loading    │ (Skeleton / aria-busy)
                  └───────┬───────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
  ┌───────────────┐               ┌───────────────┐
  │ 2. Success    │               │ 3. Error      │ (Messaggio azionabile + Retry)
  │ (Data / View) │               └───────────────┘
  └───────────────┘
```

- **Messaggi d'Errore Specifici & Umani**: spiegare il motivo e indicare la soluzione immediata. Mai status code o log interni esposti ("Email già registrata: accedi qui", non "Error 409 Conflict").
- **Empty State Produttivi**: mai un riquadro vuoto o tabella bianca. Sempre: 1) Icona/illustrazione chiara, 2) Titolo esplicativo, 3) Descrizione del perché è vuoto, 4) CTA primaria che invita a creare il primo record.

---

## 9. Layout Mobile-First & Breakpoint Guidati dal Contenuto

- **Mobile-First Realistico**: scrivi prima il CSS/Tailwind per il viewport più compatto (360-390px, una colonna, touch ergonomico con pollice); espandi con media query `min-width` solo quando lo spazio extra valorizza il contenuto.
- **Breakpoint Intrinseci**: posiziona i breakpoint dove il layout collassa o la riga di testo supera i 75-80 caratteri, non su dimensioni rigide di telefoni specifici memorizzate a priori.
- **Fluid Typography & Spacing**: privilegia `clamp()` o unità relative percentuali/vw per scalare coerentemente tra mobile e desktop.

```
❌ Desktop-first con override @media (max-width: 768px); tabelle che escono dal bordo mobile con scroll orizzontale rotto.
✅ Grid fluida a 1 colonna (mobile) -> 2 colonne (tablet) -> 3 colonne (desktop); tabelle con card-view fallback su touch.
```

---

## Checklist di Validazione Pre-Consegna UI

- [ ] **Leggi Cognitive**: Esiste una sola CTA primaria dominante? I form complessi sono suddivisi a step?
- [ ] **Spaziatura & Griglia**: Tutti i margini, padding e gap sono multipli di 8px (o 4px)? Nessun valore arbitrario?
- [ ] **Tipografia**: Scala modulare rispettata (max 5-6 taglie)? Line-height 1.4-1.6 su body e 1.1-1.3 su titoli?
- [ ] **Colori & Contrasto**: Rapporto WCAG AA verificato (≥4.5:1 testo, ≥3:1 componenti)? Token semantici utilizzati?
- [ ] **I 9 Stati Interattivi**: Il componente ha design esplicito per default, hover, focus-visible, active, disabled, loading, error, empty, success?
- [ ] **Motion & Performance**: Transizioni entro 150-300ms con curve ease-out/in? `prefers-reduced-motion` gestito? Skeleton screen presente per fetch asincrone?
- [ ] **Accessibilità & Touch**: Touch target minimo ≥ 44x44px? Navigazione completa da tastiera con focus ring visibile? Modali con focus trap?
- [ ] **Errori & Mutation**: Fetch gestita con Loading, Error con Retry, e Success? Messaggi d'errore azionabili e non tecnici?
- [ ] **Mobile-First**: Layout testato sui 360px senza overflow orizzontale indesiderato? Breakpoint guidati dal contenuto?
