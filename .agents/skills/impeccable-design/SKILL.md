---
name: impeccable-design
description: >
  MUST USE THIS SKILL whenever designing, building, refining, or auditing complete frontend web applications,
  dashboards, data-dense interfaces, SaaS tools, or editorial experiences. Enforces Paul Bakaus's Impeccable framework:
  4 visitor modes (Operate, Persuade, Read, Experience), 24 modular design commands (shape, audit, critique, polish, harden, onboard, distill),
  durable truth artifacts (PRODUCT.md, DESIGN.md), and deterministic anti-slop rules.
  Attiva per keyword o intenti: "impeccable", "impeccable-design", "shape UI", "audit frontend", "critique design", "polish UI", "harden frontend", "design system", "dashboard UX", "onboarding UX".
  NON attivare per pura logica backend priva di interfaccia o per landing page di solo marketing di conversione (usa invece design-taste-frontend).
tags: [dev-backend, frontend, ui-ux, design-systems, architecture]
---

> ℹ️ **Skill in esecuzione**: `impeccable-design`
> *Questa skill si e attivata per guidare l'architettura UX/UI full-lifecycle, la consistenza dei registri applicativi e la robustezza pre-shipping.*

**REGOLA DI OUTPUT OBBLIGATORIA**: quando questa skill e attiva, includi sempre all'inizio della tua risposta il blocco di callout soprastante.

# Impeccable Design (Full-Lifecycle UX & Design Engineering)

Framework ingegneristico di design per agenti AI basato sulla metodologia **Impeccable** di Paul Bakaus (ex-Google, autore di jQuery UI).
Tratta il design non come decorazione arbitraria, ma come **sistema decisionale a 4 modalita operative**, governato da artefatti persistenti (`PRODUCT.md` e `DESIGN.md`), 24 comandi atomici on-demand e 61 regole deterministiche anti-slop.

---

## 1. I 4 Registri Visivi (Visitor Modes)

Il design fallisce quando applica pattern di marketing a software applicativo, o pattern di dashboard a landing page. Identifica la modalita della superficie prima di scrivere codice:

| Modalita | Superficie Target | Obiettivo Utente | Priorita Architetturale |
|---|---|---|---|
| **Operate** | Web App, Dashboard, Console SaaS, Editor, Settings, Data Tables | Completare un task con precisione ed efficienza | Scansionabilita, alta densita, prevedibilita spaziale, hotkey, focus keyboard, assenza di animazioni decorative. |
| **Persuade** | Landing page, campagne marketing, pricing, pagine prodotto | Comprendere il valore e prendere una decisione | Gerarchia drammatica, tensione spaziale, contrasto, social proof autentica, asset visivi di impatto. |
| **Read** | Documentazione, knowledge base, changelog, articoli tecnici | Comprendere e assimilare informazioni complesse | Misura ergonomica (45-75ch), line-height 1.5-1.7, contrasto AAA, navigazione non invasiva, leggibilita tipografica. |
| **Experience** | Portfolio creativo, showcase interattivi, brand immersion | Vivere l'opera o il prodotto in prima persona | L'interfaccia arretra per valorizzare l'artefatto visivo; interazioni fisiche fluide e transizioni sceniche. |

---

## 2. Artefatti di Persistenza della Verita

Per evitare che il modello reinterpreti l'identita del software a ogni prompt (Context Drift), Impeccable si ancora a due documenti nella radice di progetto:

### `PRODUCT.md` (Durable Product Truth)
Registra i fatti invarianti del prodotto. Non viene modificato durante le iterazioni visive:
- **Audience & Context:** Chi usa il prodotto e in quale ambiente fisico/cognitivo (es. operatori in fabbrica con guanti, manager B2B con fretta).
- **Core Value Proposition:** Il problema primario risolto e la metrica di successo.
- **Invariant Constraints:** Vincoli normativi, conformita a11y (es. WCAG 2.2 AAA obbligatorio), requisiti browser/device.
- **Tone & Register:** Voce del prodotto (asciutta, autorevole, pragmatica).

### `DESIGN.md` (Living Design System)
Mappa il sistema estetico e i token del codice:
- **Color Tokens:** Superfici, confini, testi e semantica di stato (Success, Warning, Critical) con ratio di contrasto testati.
- **Typography Stack:** Famiglie sans/mono/serif, ratio modulare (Minor Third 1.200 o Major Third 1.250), altezze di linea.
- **Elevation & Radii:** Scala coerente dei raggi di curvatura (Sharp 0px, Soft 6-8px, Pill 9999px) e ombre color-tinted.
- **Component Contracts:** Comportamento di bottoni, input, modali, badge e tabelle.

---

## 3. Matrice dei Comandi Operativi On-Demand

Non caricare prompt enormi. Invoca il comando chirurgico corrispondente al task:

### Fase 1: Pianificazione & Definizione
- **`shape [feature]`**: Pianifica architettura dell'informazione, flussi utente, stati limite ed affordances prima di generare componenti o scrivere CSS.
- **`init`**: Intervista o scansiona il repository per creare il file `PRODUCT.md` con i vincoli fondamentali.
- **`document`**: Esegue l'ingegneria inversa della codebase esistente ed estrae lo stato attuale in `DESIGN.md`.
- **`extract [target]`**: Trasforma stili hardcoded o frammenti sparsi in token semantici e componenti atomici riusabili.

### Fase 2: Valutazione & Verifica Critica
- **`critique [target]`**: Audit euristico avanzato su gerarchia visiva, carico cognitivo, chiarezza informativa e risonanza d'uso.
- **`audit [target]`**: Verifica tecnica automatizzata: conformita WCAG AA/AAA, navigazione da tastiera, zero layout shift (CLS < 0.1), responsivita mobile.
- **`harden [target]`**: Rendere il componente a prova di produzione: gestione integrata di stati di errore (Error Boundaries), overflow di testo (troncamento/wrap pulito), espansione stringhe per internazionalizzazione (i18n), fallimento di rete e dati estremi.
- **`onboard [target]`**: Progettazione meticolosa dell'esperienza di primo utilizzo: empty states con call-to-action istruttive, scheletri di caricamento realistici e percorsi di attivazione.

### Fase 3: Calibrazione & Rifinitura
- **`polish [target]`**: Passaggio finale pre-shipping: allineamento micrometrico a `DESIGN.md`, perfezionamento dei dettagli di frontiera, pulizia DOM.
- **`bolder [target]`**: Aumenta contrasto, peso tipografico e presenza scenica di interfacce troppo timide o slavate.
- **`quieter [target]`**: Riduce stimoli visivi, abbassa saturazione e calma layout sovra-stimolanti o iper-animati.
- **`distill [target]`**: Elimina la complessita accidentale: rimuove card annidate inutili, riduce linee di separazione, fa respirare il layout attraverso il solo spazio negativo.
- **`animate [target]`**: Introduce microinterazioni cinetiche con molle fisiche (Spring Physics: damping/stiffness bilanciati) e supporto obbligatorio a `prefers-reduced-motion`.
- **`typeset [target]`** / **`layout [target]`** / **`colorize [target]`**: Micro-interventi isolati su ritmo verticale, palette o gerarchia dei caratteri.

---

## 4. Regole Deterministiche Anti-Slop (The 61 Rules Core)

La skill applica tassativamente questi vincoli tecnici ed estetici:

1. **Anti-Cardception:** MAI annidare card dentro card (`card in card`). Raggruppa i dati tramite spaziatura ergonomica (griglia 8pt integrata da `frontend-ux-excellence`), linee sottili di confine o sfondi tenui a contrasto 1.05:1.
2. **Zero Testo Grigio su Fondi Colorati:** Il testo secondario su superfici tinte deve derivare dalla stessa tinta a opacita controllata (es. `rgba(white, 0.7)` su blu scuro), mai grigio neutro slavato.
3. **No Pure Black / Pure White:** Banditi `#000000` assoluto e `#ffffff` assoluto su superfici piene. Usa off-black con componente cromatica (Zinc-950, Slate-950) e off-white per preservare profondita ottica.
4. **No Easing a Rimbalzo Giocattolo:** Banditi curve `bounce` o easing elastici circensi per software professionale. Usa curve smorzate (`cubic-bezier(0.16, 1, 0.3, 1)` o spring fisiche).
5. **Keyboard Accessibility First:** Ogni controllo interattivo possiede uno stato `:focus-visible` nitido con anello di contrasto minimo 3:1. Nessun elemento cliccabile e privo di semantica HTML nativa (`<button>`, `<a>`).
6. **Form Ergonomics:** Etichette sempre esterne e stabili al di sopra del campo; mai affidare la comprensione del campo al solo `placeholder`.

---

## 5. Protocollo di Esecuzione in Antigravity

Quando l'utente richiede di creare o migliorare un'interfaccia:
1. **Dichiara la Modalita:** Specifica se stai operando in `Operate`, `Persuade`, `Read` o `Experience`.
2. **Ancora la Verita:** Verifica la presenza di `PRODUCT.md` e `DESIGN.md`; se assenti in un progetto articolato, proponi una rapida esecuzione di `/impeccable init` o `/impeccable document`.
3. **Esegui con Granularita:** Applica il comando richiesto (`shape`, `harden`, `audit`, `polish`) focalizzandoti sul suo specifico perimetro.
