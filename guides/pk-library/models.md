# PK-Library model maths

This guide writes out the one- and two-compartment equations that PK-Library evaluates, with the file and line that implements each one. Read it when you change a model type, debug a surprising concentration or dose, or review a new study model. For how the classes fit together, see [primer.md](primer.md).

Paths below are relative to `src/packages/cpp/PK-Library/src/`, with `model/`, `math/` and `study/` short for `pharmacokinetics/model/`, `pharmacokinetics/math/` and `pharmacokinetics/study/`. The units in the "where" lists assume a drug dosed in mg with concentrations in mg/L. Drugs with other units convert to and from them through `UnitSettings` (for example `concentration_to_dose_correction()`), and this guide leaves those factors out.

## How the engine chooses a method

- **Concentrations** come from a numerical simulation by default. A closed-form sum is used only when `Model::can_use_closed_form` allows it (`model/model.cpp:730-745`): the model is linear, no parameter varies over time, there is no dialysis, and every dose is intermittent IV.
- **Steady-state values** that the API reports (peak, trough, AUC) always come from simulation. `Model::from_graph` repeats the regimen until consecutive troughs agree within 0.01 % (`model/model.cpp:51-60`, `805-821`).
- **Doses** come from an analytic formula when the model type has one for the target and route, and from a bracket-and-bisect search otherwise. The dispatch lives in `OneCompartment::from_steady_state_target` (`model/onecompartment.cpp:53-136`) and `TwoCompartment::from_steady_state_target` (`model/twocompartment.cpp:49-160`).

## Parameters

### One-compartment

```math
k_e = \frac{CL}{V}, \qquad t_{1/2} = \frac{\ln 2}{k_e}
```

where:

- $k_e$ is the elimination rate constant (1/h).
- $CL$ is clearance (L/h), always a fitted parameter read from the `BayesContainer`.
- $V$ is the volume of distribution (L).
- $t_{1/2}$ is the half-life (h).

Source: `model/onecompartment.cpp:44-51` and `237-244`. `time_to_ss()` reports $4\,t_{1/2}$ (`onecompartment.cpp:246-254`).

### Two-compartment

Each study defines the micro rate constants. Studies parameterised by clearances and volumes use the definitions below, as in `study/cefepime/cefepime_an_2023.hpp:177-201`. Others fix a constant instead. For example, the vancomycin TDMS family, which includes Rodvold 1988, fixes $k_{21} = 0.46$ per hour (`study/vancomycin/vancomycintdms.hpp:123-124`).

```math
k_{10} = \frac{CL}{V_c}, \qquad k_{12} = \frac{Q}{V_c}, \qquad k_{21} = \frac{Q}{V_p}
```

where:

- $k_{10}$ is the elimination rate constant from the central compartment (1/h).
- $k_{12}$ is the transfer rate constant from the central to the peripheral compartment (1/h).
- $k_{21}$ is the transfer rate constant from the peripheral to the central compartment (1/h).
- $CL$ is clearance (L/h).
- $Q$ is inter-compartmental clearance (L/h).
- $V_c$ and $V_p$ are the central and peripheral volumes (L).

Every two-compartment model shares the hybrid rate constants and derived volumes (`model/twocompartment.cpp:343-373`, `424-451`):

```math
\alpha, \beta = \frac{(k_{10} + k_{12} + k_{21}) \pm \sqrt{(k_{10} + k_{12} + k_{21})^2 - 4\,k_{10}\,k_{21}}}{2}, \qquad V_{d\beta} = \frac{CL}{\beta}, \qquad V_{ss} = V_c + V_p, \qquad t_{1/2,\beta} = \frac{\ln 2}{\beta}
```

where:

- $\alpha$ is the fast (distribution) rate constant, taking the plus sign (1/h).
- $\beta$ is the slow (terminal) rate constant, taking the minus sign (1/h).
- $k_{10}$, $k_{12}$ and $k_{21}$ are the central elimination, central-to-peripheral and peripheral-to-central rate constants (1/h).
- $V_{d\beta}$ is the terminal-phase volume (L), and $CL$ is clearance (L/h).
- $V_{ss}$ is the steady-state volume (L), and $V_c$ and $V_p$ are the central and peripheral volumes (L).
- $t_{1/2,\beta}$ is the terminal half-life (h).

`TwoCompartment::half_life()` returns $t_{1/2,\beta}$ (`twocompartment.cpp:44`), and `decay_time()` decays with $\beta$ alone (`twocompartment.cpp:162-176`).

## Numerical simulation

The default simulator, `basic_euler` (`common/pkconstants.cpp:47-55`), integrates the compartment amounts with a fixed-step forward Euler loop (`model/pksimulator_euler.cpp:99-231`). For a linear two-compartment model it solves:

```math
\begin{aligned}
\frac{dX_a}{dT} &= -k_a X_a \\
\frac{dX_1}{dT} &= k_a X_a + S\,R(T) + k_{21} X_2 - \left(k_{12} + k_{10} + \frac{CL_d(T)}{V_c}\right) X_1 \\
\frac{dX_2}{dT} &= k_{12} X_1 - k_{21} X_2 \\
C(T) &= \frac{X_1}{V_c}
\end{aligned}
```

where:

- $T$ is time since the start of the dose history (h).
- $X_a$ is the amount waiting in the absorption depot (mg). Each oral, IM or subcutaneous dose adds $F\,S\,D$ once its lag time has passed.
- $F$ is bioavailability and $S$ is the salt fraction, both per route.
- $D$ is the amount of that dose (mg).
- $k_a$ is the absorption rate constant (1/h).
- $X_1$ and $X_2$ are the amounts in the central and peripheral compartments (mg).
- $R(T)$ is the combined rate of the IV infusions running at time $T$ (mg/h). Each infusion contributes its dose divided by its infusion time.
- $k_{10}$, $k_{12}$ and $k_{21}$ are the central elimination, central-to-peripheral and peripheral-to-central rate constants (1/h).
- $CL_d(T)$ is the dialysis clearance while a dialysis session is running, and 0 otherwise (L/h).
- $V_c$ is the central volume (L).
- $C(T)$ is the central concentration (mg/L).

A one-compartment model drops $X_2$ and uses $k_{12} = k_{21} = 0$, $k_{10} = k_e$ and $V_c = V$.

Implementation details that change results:

- Each step applies absorption, then distribution, then elimination, and clamps every transfer to the amount available, so amounts never go negative (`pksimulator_euler.cpp:190-227`).
- IV input carries $S$ but not $F$ (`pksimulator_euler.cpp:148-152`).
- Erlang transit absorption and Michaelis-Menten elimination run in the same loop, through `PKContainer::ktr()` and `PKContainer::mm()`.
- The step is 1/120 h for graphs and 1/320 h for steady-state and dose searches (`Drug::graphing_dt()` and `Drug::steadystate_dt()`, `pkconstants.cpp:30-32`). Infliximab and adalimumab graph with 1/9 h.
- Graphs run for up to 60 days, or 365 days for infliximab and adalimumab (`pkconstants.cpp:36-38`).

## Closed-form concentrations

These formulas apply only when `can_use_closed_form` holds, so every dose is an intermittent IV infusion.

### One-compartment

```math
\begin{aligned}
C_{\text{dose}}(t) &= \frac{S R}{CL}\left(1 - e^{-k_e t_{\text{on}}}\right) e^{-k_e (t - t_{\text{on}})}, \qquad t_{\text{on}} = \min(t, t_{\text{inf}}), \qquad R = \frac{D}{t_{\text{inf}}} \\
C(T) &= C_0\, e^{-k_e T} + \sum_j C_{\text{dose},j}(T - T_j)
\end{aligned}
```

where:

- $C_{\text{dose}}(t)$ is the concentration from one infusion (mg/L).
- $t$ is time since the start of that dose (h).
- $t_{\text{on}}$ is how long the infusion has run by time $t$ (h), and $t_{\text{inf}}$ is the infusion duration (h).
- $R$ is the infusion rate (mg/h), and $D$ is the dose (mg).
- $S$ is the salt fraction.
- $CL$ is clearance (L/h), and $k_e$ is the elimination rate constant (1/h).
- $C(T)$ is the concentration at time $T$ since the start of the history (mg/L).
- $C_0$ is the starting level from the clinical context (mg/L).
- $T_j$ is the start time of dose $j$ (h), and $C_{\text{dose},j}$ is that dose's curve.

Source: `model/onecompartment.cpp:138-162` and `865-884`. Bioavailability does not appear.

### Two-compartment

```math
\begin{aligned}
C_{\text{dose}}(t) &= S R \left[\frac{a}{\alpha}\left(1 - e^{-\alpha t_{\text{on}}}\right) e^{-\alpha (t - t_{\text{on}})} + \frac{b}{\beta}\left(1 - e^{-\beta t_{\text{on}}}\right) e^{-\beta (t - t_{\text{on}})}\right] \\
a &= \frac{\alpha - k_{21}}{V_c(\alpha - \beta)}, \qquad b = \frac{k_{21} - \beta}{V_c(\alpha - \beta)} \\
C(T) &= C_0\, e^{-\beta T} + \sum_j C_{\text{dose},j}(T - T_j)
\end{aligned}
```

where:

- $C_{\text{dose}}(t)$ is the concentration from one infusion (mg/L), and $t$ is time since the start of that dose (h).
- $t_{\text{on}} = \min(t, t_{\text{inf}})$ is how long the infusion has run by time $t$ (h).
- $S$ is the salt fraction, and $R = D / t_{\text{inf}}$ is the infusion rate (mg/h).
- $a$ and $b$ are the coefficients of the fast and slow phases (1/L).
- $\alpha$ and $\beta$ are the fast and slow hybrid rate constants (1/h).
- $k_{21}$ is the peripheral-to-central rate constant (1/h), and $V_c$ is the central volume (L).
- $C(T)$ is the concentration at time $T$ since the start of the history (mg/L), and $C_0$ is the starting level (mg/L).
- $T_j$ is the start time of dose $j$ (h), and $C_{\text{dose},j}$ is that dose's curve.

Source: `model/twocompartment.cpp:214-219`, `271-284` and `691-705`. The starting level decays with $\beta$ alone, so the closed form ignores whatever the peripheral compartment held at time zero.

## Doses from a target

The table shows which method each common target uses. "Search" means `Model::target_binary_search`, described after the formulas.

| Target | One-compartment IV | One-compartment oral, IM, SC | Two-compartment IV | Two-compartment other routes |
| --- | --- | --- | --- | --- |
| Trough | Formula | Search | Formula | Search |
| Peak | Formula | Search | Search | Search |
| Peak and trough | Formula for dose and interval | Formula for dose and interval | Formula, or a search when the peak is defined at the end of distribution | Not supported (empty regimen) |
| AUC24, AUC6, AUC12, AUIC24 | Formula | Formula for oral and SC. IM returns an empty regimen. | Formula | Search for oral |
| AUC per dose | Not handled (empty regimen) | Not handled (empty regimen) | Search | Search |
| Average concentration, continuous IV | Formula | Not applicable | Formula | Not applicable |
| AUC48, AUC72, AUC96 | Cumulative formula | Cumulative formula | Cumulative formula | Cumulative formula |
| Trough range (short course) | `LinearPK` | Throws (IV only) | `LinearPK` | Throws (IV only) |

AUC6, AUC12 and AUIC24 targets are converted to an equivalent AUC24 before dosing (`cast_to_AUC24()`). Carboplatin's only target is AUC per dose (`drug/carboplatin.hpp:40-42`), so its doses always come from the search, which simulates its infusion-time-dependent clearance (`study/carboplatin_lindauer2010.hpp:53-60`). An average-concentration target on an intermittent route is converted to an AUC24 of $24\,C_{\text{avg}}$.

### One-compartment intermittent IV

```math
D = \frac{CL\, C_{\text{peak}}\, t_{\text{inf}} \left(1 - e^{-k_e \tau}\right)}{S F \left(1 - e^{-k_e t_{\text{inf}}}\right) e^{-k_e t_p}}
```

where:

- $D$ is the maintenance dose (mg).
- $CL$ is clearance (L/h), and $k_e$ is the elimination rate constant (1/h).
- $C_{\text{peak}}$ is the target peak (mg/L).
- $t_{\text{inf}}$ is the infusion duration (h), and $\tau$ is the dosing interval (h).
- $S$ is the salt fraction, and $F$ is bioavailability.
- $t_p$ is the time from the end of the infusion to the peak draw (h). It comes from the institution's peak-time protocol for peak targets (`onecompartment.cpp:501-502`) and is 0 for trough targets.

Source: `dose_iv`, `onecompartment.cpp:766-770`. The other intermittent-IV targets reuse it:

```math
C_{\text{peak}} = C_{\text{trough}}\, e^{k_e (\tau - t_{\text{inf}})}, \qquad \tau = t_{\text{inf}} + t_p + \frac{\ln(C_{\text{peak}} / C_{\text{trough}})}{k_e}, \qquad D = \frac{AUC_{24}\,\tau}{24}\cdot\frac{CL}{S F}
```

where:

- $C_{\text{peak}}$ and $C_{\text{trough}}$ are the steady-state peak and trough (mg/L).
- $k_e$ is the elimination rate constant (1/h), and $CL$ is clearance (L/h).
- $\tau$ is the dosing interval (h), and $t_{\text{inf}}$ is the infusion duration (h).
- $t_p$ is the time from the end of the infusion to the peak draw (h).
- $D$ is the maintenance dose (mg), and $AUC_{24}$ is the target area under the curve over 24 hours (mg·h/L).
- $S$ is the salt fraction, and $F$ is bioavailability.

The first expression turns a trough target into the peak that feeds the dose formula (`peak_iv_from_interval`, `onecompartment.cpp:746-748`). The second gives the interval for a peak-and-trough target (`interval_iv`, `onecompartment.cpp:761-763`). The third is the AUC dose (`intermittent_iv_from_auc` and `dose_from_auc`, `onecompartment.cpp:544-560` and `780-782`).

For continuous IV, the rate that holds an average concentration is:

```math
R = \frac{C_{\text{avg}}\, CL}{S F}
```

where:

- $R$ is the infusion rate (mg/h).
- $C_{\text{avg}}$ is the target average concentration (mg/L). An AUC target on a continuous route uses $C_{\text{avg}} = AUC_{24} / 24$.
- $CL$ is clearance (L/h).
- $S$ is the salt fraction, and $F$ is bioavailability.

Source: `onecompartment.cpp:623-628`.

### One-compartment loading dose or wait

When the starting level is at or below the steady-state trough, the engine adds a loading dose. Otherwise it recommends waiting until the level decays to the trough (`onecompartment.cpp:483-492`). When the target does not fix the steady-state peak or trough, they come from `peak_iv` and `trough_iv` (`onecompartment.cpp:726-737`).

```math
\begin{aligned}
D_L &= \frac{CL\, t_{\text{inf}} \left(C_{\text{peak}} - C_0\, e^{-k_e t_{\text{inf}}}\right)}{S F \left(1 - e^{-k_e t_{\text{inf}}}\right)}, \qquad t_{\text{wait}} = \frac{\ln(C_0 / C_{\text{trough}})}{k_e} \\
C_{\text{peak}} &= \frac{S F R \left(1 - e^{-k_e t_{\text{inf}}}\right)}{CL \left(1 - e^{-k_e \tau}\right)}, \qquad C_{\text{trough}} = C_{\text{peak}}\, e^{-k_e (\tau - t_{\text{inf}})}
\end{aligned}
```

where:

- $D_L$ is the loading dose (mg), and $t_{\text{wait}}$ is the time to wait before the first maintenance dose (h).
- $CL$ is clearance (L/h), and $k_e$ is the elimination rate constant (1/h).
- $t_{\text{inf}}$ is the infusion duration (h), and $\tau$ is the dosing interval (h).
- $C_{\text{peak}}$ and $C_{\text{trough}}$ are the regimen's steady-state peak and trough (mg/L).
- $C_0$ is the current level (mg/L).
- $S$ is the salt fraction, and $F$ is bioavailability.
- $R = D / t_{\text{inf}}$ is the maintenance infusion rate (mg/h), where $D$ is the maintenance dose (mg).

Source: `onecompartment.cpp:787-798` and `164-175`.

### One-compartment oral and IM

```math
t_{\max} = t_{\text{lag}} + \frac{1}{k_a - k_e}\ln\frac{k_a\left(1 - e^{-k_e \tau}\right)}{k_e\left(1 - e^{-k_a \tau}\right)}, \qquad D = \frac{C_{\text{peak}}\, V \left(1 - e^{-k_e \tau}\right)}{F S\, e^{-k_e t_{\max}}}, \qquad \tau = t_{\text{lag}} + \frac{\ln(k_a / k_e)}{k_a - k_e} + \frac{\ln(C_{\text{peak}} / C_{\text{trough}})}{k_e}
```

where:

- $t_{\max}$ is the time of the steady-state peak after a dose (h).
- $t_{\text{lag}}$ is the absorption lag time (h).
- $k_a$ is the absorption rate constant, and $k_e$ is the elimination rate constant (1/h).
- $\tau$ is the dosing interval (h).
- $D$ is the maintenance dose (mg), and $V$ is the volume (L).
- $C_{\text{peak}}$ and $C_{\text{trough}}$ are the target peak and trough (mg/L).
- $F$ is bioavailability, and $S$ is the salt fraction.

Source: `onecompartment.cpp:835-862`. The third expression is the interval for a peak-and-trough target. It uses the single-dose peak time (`tmax_iv`, `onecompartment.cpp:714-718`). When $k_a$ and $k_e$ differ by less than $5 \times 10^{-6}$, the code adds $10^{-4}$ to $k_a$ to avoid dividing by zero.

The oral loading dose raises the current level to the target peak (`onecompartment.cpp:800-820`):

```math
D_L = \frac{(C_{\text{peak}} - C_0)\, V (k_a - k_e)}{S F k_a \left(e^{-k_e t^{*}} - e^{-k_a t^{*}}\right)}, \qquad t^{*} = t_{\text{lag}} + \frac{\ln(k_a / k_e)}{k_a - k_e}
```

where:

- $D_L$ is the loading dose (mg).
- $C_{\text{peak}}$ is the target peak, and $C_0$ is the current level (mg/L).
- $V$ is the volume (L).
- $k_a$ is the absorption rate constant, and $k_e$ is the elimination rate constant (1/h).
- $S$ is the salt fraction, and $F$ is bioavailability.
- $t^{*}$ is the single-dose peak time (h), and $t_{\text{lag}}$ is the absorption lag time (h).

### Two-compartment intermittent IV

The two-compartment dose formulas reuse the phase coefficients $a$ and $b$ from the closed-form section.

```math
D = \frac{C_{\text{trough}}\, t_{\text{inf}}}{\dfrac{a}{\alpha}\left(1 - e^{-\alpha t_{\text{inf}}}\right) e^{-\alpha (\tau - t_{\text{inf}})} + \dfrac{b}{\beta}\cdot\dfrac{\left(1 - e^{-\beta t_{\text{inf}}}\right) e^{-\beta (\tau - t_{\text{inf}})}}{1 - e^{-\beta \tau}}}
```

where:

- $D$ is the maintenance dose for a trough target (mg).
- $C_{\text{trough}}$ is the target steady-state trough (mg/L).
- $t_{\text{inf}}$ is the infusion duration (h), and $\tau$ is the dosing interval (h).
- $a$ and $b$ are the fast- and slow-phase coefficients (1/L).
- $\alpha$ and $\beta$ are the fast and slow hybrid rate constants (1/h).

Source: `dose_iv_from_trough`, `twocompartment.cpp:1038-1049`. `trough_iv` solves the same expression for the trough (`twocompartment.cpp:1091-1101`).

For a peak-and-trough target, the engine first solves for the infusion rate, then for the interval (`twocompartment.cpp:878-904`, `989-1035`):

```math
\begin{aligned}
R &= \frac{C_{\text{peak}} - C_{\text{trough}}\, e^{-\beta (t_{\text{inf}} + t_p)}}{\dfrac{a}{\alpha}\left(1 - e^{-\alpha t_{\text{inf}}}\right) e^{-\alpha t_p} + \dfrac{b}{\beta}\left(1 - e^{-\beta t_{\text{inf}}}\right) e^{-\beta t_p}}, \qquad D = R\, t_{\text{inf}} \\
0 &= R\left[\frac{a}{\alpha}\left(1 - e^{-\alpha t_{\text{inf}}}\right) e^{-\alpha (\tau - t_{\text{inf}})} + \frac{b}{\beta}\left(1 - e^{-\beta t_{\text{inf}}}\right) e^{-\beta (\tau - t_{\text{inf}})}\right] + C_{\text{trough}}\left(e^{-\beta \tau} - 1\right)
\end{aligned}
```

where:

- $R$ is the infusion rate (mg/h), and $D$ is the dose (mg).
- $C_{\text{peak}}$ and $C_{\text{trough}}$ are the target peak and trough (mg/L).
- $t_p$ is the time from the end of the infusion to the peak draw (h).
- $t_{\text{inf}}$ is the infusion duration (h), and $\tau$ is the interval being solved for (h).
- $a$ and $b$ are the fast- and slow-phase coefficients (1/L).
- $\alpha$ and $\beta$ are the fast and slow hybrid rate constants (1/h).

The rate formula treats the previous trough as decaying with $\beta$ while the new dose infuses. A secant iteration solves the interval equation. It starts at $\ln 2 / \beta$, stops within $10^{-4}$, and runs at most 30 times. When the peak-time protocol says "end of distribution phase", the dose comes from a search on a simulated single dose instead (`twocompartment.cpp:854-876`, `892-894`).

The AUC and continuous-rate doses use the one-compartment formulas: the AUC dose is $AUC_{24}\,\tau\,CL / (24\,S F)$ and the continuous rate is $C_{\text{avg}}\,CL / (S F)$ (`twocompartment.cpp:721-730`, `921-942`, `1052-1054`).

The loading dose lifts the level from its current value to the target trough after one interval. Every caller gives it the same infusion time as the maintenance dose (`twocompartment.cpp:840-852`, `1104-1127`):

```math
D_L = \frac{t_{\text{inf}}\left(C_{\text{trough}} - C_0\, e^{-\beta \tau}\right)}{\dfrac{a}{\alpha}\left(1 - e^{-\alpha t_{\text{inf}}}\right) e^{-\alpha (\tau - t_{\text{inf}})} + \dfrac{b}{\beta}\left(1 - e^{-\beta t_{\text{inf}}}\right) e^{-\beta (\tau - t_{\text{inf}})}}, \qquad t_{\text{wait}} = \frac{\ln(C_0 / C_{\text{trough}})}{\beta}
```

where:

- $D_L$ is the loading dose (mg).
- $t_{\text{inf}}$ is the infusion duration (h), and $\tau$ is the dosing interval (h).
- $C_{\text{trough}}$ is the target steady-state trough, and $C_0$ is the current level (mg/L).
- $a$ and $b$ are the fast- and slow-phase coefficients (1/L).
- $\alpha$ and $\beta$ are the fast and slow hybrid rate constants (1/h).
- $t_{\text{wait}}$ is the wait before the first maintenance dose when $C_0$ is above the trough (h).

### Cumulative AUC targets

AUC48, AUC72 and AUC96 split the AUC still to be delivered evenly across the doses that fit in the remaining window (`model/linearmodel.cpp:122-186`):

```math
D = \frac{AUC_{\text{rem}}}{n}\cdot\frac{CL}{F S}, \qquad AUC_{\text{rem}} = \max\left(0,\ AUC_{\text{target}} - AUC_{\text{given}}\right), \qquad n = \operatorname{round}\left(\frac{W - T_{\text{next}}}{\tau}\right)
```

where:

- $D$ is each remaining dose (mg).
- $AUC_{\text{target}}$ is the cumulative target, and $AUC_{\text{given}}$ is the AUC predicted from the doses already given (mg·h/L).
- $AUC_{\text{rem}}$ is what remains to deliver (mg·h/L).
- $n$ is the number of remaining doses.
- $W$ is the window length: 48, 72 or 96 h.
- $T_{\text{next}}$ is the time from the start of the history to the next dose, or 0 when no dose has been given (h).
- $\tau$ is the dosing interval (h).
- $CL$ is clearance at the next dose time (L/h).
- $F$ is bioavailability, and $S$ is the salt fraction.

When $n \le 0$ or $AUC_{\text{rem}} \le 0$ the engine returns `DosageRegimen::NoDose`, with a flag that says which limit was hit.

### Binary search

`Model::target_binary_search` (`model/model.cpp:335-422`) handles every target and route without a formula.

1. It starts from doses of 250 and 500, halving or doubling until the error changes sign.
2. It bisects until the error is within 0.001 target units, up to 200 iterations. Each evaluation simulates the regimen to steady state with `Drug::steadystate_dt()`.
3. It searches for a loading dose the same way when the current level is below 0.95 times the steady-state trough, and recommends a wait instead when the level is above 1.05 times the trough (`common/pkconstants.cpp:13-14`). The loading search runs only for drugs where `requires_loading_dose()` is true, and only on repeated-dose routes.

## Matrix solution for short courses

`LinearPK` (`math/linear_pk.h`, `math/linear_pk.cpp`) solves the N-compartment IV model exactly by eigendecomposition. It backs the trough-range target and `LinearModel::amounts_at_time` (`model/linearmodel.cpp:79-120`).

```math
\begin{aligned}
\frac{d\mathbf{x}}{dT} &= \mathbf{K}\mathbf{x} + \mathbf{u}(T), \qquad \mathbf{K} = -\mathbf{U}\operatorname{diag}(\lambda_i)\,\mathbf{U}^{-1} \\
\boldsymbol{\Phi}(t) &= \mathbf{U}\operatorname{diag}\left(\frac{1 - e^{-\lambda_i t_{\text{on}}}}{\lambda_i}\, e^{-\lambda_i (t - t_{\text{on}})}\right)\mathbf{U}^{-1}, \qquad t_{\text{on}} = \min(t, t_{\text{inf}}) \\
\mathbf{H}(\tau, N) &= \mathbf{U}\operatorname{diag}\left(\frac{1 - e^{-N \lambda_i \tau}}{1 - e^{-\lambda_i \tau}}\right)\mathbf{U}^{-1} \\
\mathbf{x}_N &= e^{\mathbf{K} N \tau}\,\mathbf{x}_0 + \mathbf{H}(\tau, N)\,\boldsymbol{\Phi}(\tau)\,\mathbf{u}(D) \\
D &= \frac{C_{\text{target}} - \left[e^{\mathbf{K} N \tau}\mathbf{x}_0\right]_1 / V_c}{\kappa}, \qquad \kappa = \frac{\left[\mathbf{H}(\tau, N)\,\boldsymbol{\Phi}(\tau)\,\mathbf{u}(1)\right]_1}{V_c}
\end{aligned}
```

where:

- $\mathbf{x}$ is the vector of compartment amounts, central first (mg), and $T$ is time since the start of the history (h).
- $\mathbf{K}$ is the rate matrix built from the central elimination constant and each central-peripheral pair of transfer constants (`linear_pk.cpp:54-65`).
- $\mathbf{u}(D)$ is the infusion input $[D / t_{\text{inf}}, 0, \dots]$ into the central compartment for a dose $D$ (mg/h). Between infusions it is zero.
- $\mathbf{U}$ is the eigenvector matrix, and $\lambda_i$ are the positive eigenvalues (1/h). A complex or non-positive eigenvalue throws (`linear_pk.cpp:24-46`).
- $\boldsymbol{\Phi}(t)$ maps a unit infusion rate to the state $t$ hours after the infusion started.
- $t_{\text{on}}$ is how long the infusion has run by time $t$, and $t_{\text{inf}}$ is the infusion duration (h).
- $\mathbf{H}(\tau, N)$ accumulates the doses of a course, where $N$ is the number of doses and $\tau$ is the dosing interval (h).
- $\mathbf{x}_0$ is the current state, rebuilt from the doses already given (`state_from_history`), and $\mathbf{x}_N$ is the state at the trough after $N$ more doses.
- $D$ is the dose that puts the central concentration at $C_{\text{target}}$ (mg/L) at that trough.
- $[\cdot]_1$ takes the central component, $V_c$ is the central volume (L), and $\kappa$ is the trough concentration per unit dose (1/L).

`LinearPK` applies neither the salt fraction nor bioavailability (`linear_pk.h:50-55`), and it refuses oral, IM and subcutaneous routes (`linearmodel.cpp:31-35`).

The trough-range target (used by teicoplanin) builds a loading course and a maintenance dose from this solution (`model/linearmodel.cpp:190-349`):

```math
C_{\text{mid}} = \sqrt{C_{\min}\, C_{\max}}, \qquad C_L = \frac{-q + \sqrt{q^2 + 4 p\, C_{\text{mid}}^2}}{2p}
```

where:

- $C_{\min}$ and $C_{\max}$ are the ends of the target trough range (mg/L).
- $C_{\text{mid}}$ is their geometric mean, which the maintenance dose holds at steady state (mg/L).
- $C_L$ is the trough the loading course aims for (mg/L). It makes the geometric mean of the last loading trough and the first maintenance trough equal $C_{\text{mid}}$.
- $p$ is the fraction of the last loading trough that survives one maintenance interval.
- $q$ is the first maintenance trough produced by the maintenance dose alone (mg/L).

The engine then works in four steps.

1. The maintenance dose solves the $D$ equation from an empty state, with 1000 doses at the maintenance interval and $C_{\text{target}} = C_{\text{mid}}$.
2. The loading dose solves the same equation from the current state, with the loading doses not yet given and $C_{\text{target}} = C_L$.
3. After the loading course is complete, the engine recommends a single re-load only when maintenance alone would let a trough fall below $C_{\min}$, and only when that re-load is larger than the maintenance dose.
4. `round_trough_range` rounds the loading dose down to the drug's increment unless that would drop its trough below $C_{\min}$, in which case it rounds up. It rounds the maintenance dose down or up, whichever gives the average trough over seven doses closer to $C_{\text{mid}}$ on a log scale (`linearmodel.cpp:351-430`).

## Known discrepancies

These are places where the code departs from the textbook form of the equations above. Check them before relying on the affected output.

- The one-compartment oral steady-state trough adds $t_{\text{lag}}$, a time, to a concentration (`onecompartment.cpp:850`). The oral AUC path uses that trough to decide on a loading dose (`onecompartment.cpp:574-576`).
- The two-compartment IV trough and trough-dose formulas omit the accumulation factor $1 / (1 - e^{-\alpha \tau})$ on the fast phase (`twocompartment.cpp:1043`, `1095`). The error is small only when $\alpha \tau$ is large.
- The two-compartment IV dose formulas omit the salt fraction and bioavailability, while the concentration formulas apply the salt fraction. They agree only when both are 1 for the route.
- A one-compartment AUC target on an IM route returns an empty regimen, because `from_auc` handles only oral and subcutaneous non-IV routes (`onecompartment.cpp:353`).
