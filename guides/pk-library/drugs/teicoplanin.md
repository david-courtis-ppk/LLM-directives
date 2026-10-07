# Teicoplanin in PK-Library

This guide covers how PK-Library doses teicoplanin: its settings and models, and the Trough Range target that sizes multiple loading doses, the maintenance dose and any re-loading dose (added in RX-3431, the teicoplanin dose-recommendation work). Read it before you change teicoplanin or trough-range code, or when a clinician asks why the loading doses look higher than the product label.

Paths are relative to PK-Library (`src/packages/cpp/PK-Library` in the umbrella repository). The published package the services pin (1.6.1) includes this work.

## Drug settings

| Setting | Value | Source |
| --- | --- | --- |
| Patients | Adults only (18 and older). | `src/drug/teicoplanin.hpp:28-30` |
| Route | Intermittent IV only. | `src/drug/teicoplanin.hpp:96-98` |
| Target | Trough Range only. | `src/drug/teicoplanin.hpp:100-102` |
| Lab input | Albumin in g/dL, accepted between 0.01 and 15. | `src/drug/teicoplanin.hpp:104-108` |
| Therapeutic range | 15-40 mg/L, spanning the moderate (15-30) and severe (20-40) trough bands. | `src/drug/teicoplanin.hpp:123-134` |
| Toxic trough | 60 mg/L, stored as 0.06 mg/mL. Troughs of 40 mg/L and above carry thrombocytopenia risk and sit at the top of the therapeutic range instead of a separate caution band. | `src/drug/teicoplanin.hpp:110-121` |
| Dose increment | 100 mg. | `src/common/pkconstants.cpp:1406` |
| Fitting defaults | Assay error 0.1, fixed error (SEM) 0.0625 mg/L, time-weight factor 1.005. | `src/drug/teicoplanin.hpp:136-138` |
| Loading | Required, as a course of several loading doses. | `src/drug/teicoplanin.hpp:144-150` |

## Models

Every model is offered to every patient (`src/drug/teicoplanin.hpp:33-35`). Auto-select picks Qian Sun 2025 for patients on CRRT (continuous renal replacement therapy) or ECMO, and Ogami 2019 for everyone else (`src/drug/teicoplanin.hpp:37-50`).

| Model | Structure | Notes |
| --- | --- | --- |
| Ogami 2019 | Two-compartment; fits CL, Vdβ and Q | The default. The constant is named 2019, but the cited paper is Ogami C, et al. Clin Pharmacol Drug Dev. 2020;9(2):175-188 (`src/common/pkconstants.cpp:1409-1416`). |
| Qian Sun 2025 | One-compartment | Auto-selected on CRRT or ECMO. Vd depends on CRRT and sex. |
| Xiao Shan Zhang 2023 | One-compartment | CL depends on CrCl and albumin. |
| Yifan Wang 2025 | Two-compartment | Fits V_c, V_p and CL. |
| Kim 2024 | Three-compartment | Fits CL, three volumes and two intercompartmental clearances. |

Sources: `src/pharmacokinetics/study/teicoplanin/*.hpp`.

## Why teicoplanin needs its own target

Vancomycin's Trough target works with a single loading dose because vancomycin distributes quickly and has a short half-life. Teicoplanin does not. For a standard 70 kg, 176 cm adult male with a Cockcroft-Gault CrCl of 100 mL/min, the Ogami 2019 priors give a distribution half-life of about 7 h and a terminal half-life of about 8 days (`src/pharmacokinetics/study/teicoplanin/ogami_2019.hpp`). A single loading dose large enough to reach a target trough would be very large, and the level would still drift down as the drug moves into tissue.

Guidelines therefore give several loading doses at a shorter interval than maintenance. Even then, the patient is not at steady state when loading ends, so the first maintenance troughs dip. The Trough Range target sizes the loading so that the step-down at the switch to maintenance stays inside the range.

## The inputs

The clinician enters the desired minimum and maximum trough, the number of loading doses, the loading-dose interval, the maintenance interval and the infusion time (`src/pharmacokinetics/therapeutictarget/trough_range.cpp:90-105`). There is no "number of maintenance doses" input. Maintenance is open-ended.

## How the regimen is computed

`LinearModel::from_trough_range` does the work with closed-form linear PK (`src/pharmacokinetics/model/linearmodel.cpp:190-344`). It is used for one-, two- and three-compartment linear models. The maths below uses one helper: 𝒟(x, n, τ, C) is the dose that, given n equal doses every τ hours starting from compartment state x, makes the trough after the n-th dose equal C (`LinearPK::dose_from_state`, `src/pharmacokinetics/math/linear_pk.h:135-137`).

### 1. The target trough

```math
G = \sqrt{C_{\min}\,C_{\max}}
```

Where:

- C_min and C_max are the desired minimum and maximum trough in mg/L.
- G is the target trough, the geometric mean of the range. It is the middle of the range on a log scale, which suits exponential decay and keeps doses lower than the arithmetic midpoint would.

### 2. The maintenance dose

```math
D_M = \mathcal{D}(\mathbf{0},\ 1000,\ \tau_M,\ G)
```

Where:

- D_M is the maintenance dose in mg.
- 𝒟 is the dose helper defined above, and **0** is an empty compartment state.
- 1000 doses is far beyond five half-lives, so the result is the steady-state dose.
- τ_M is the maintenance interval in hours.

The maintenance dose depends only on the patient's fitted clearance, not on the loading (`linearmodel.cpp:230-237`). Early maintenance troughs sit just below G and drift up toward it.

### 3. The loading target

```math
C_{M1} = A\,C_L + B, \qquad \sqrt{C_L\,C_{M1}} = G
\quad\Longrightarrow\quad
C_L = \frac{-B + \sqrt{B^2 + 4\,A\,G^2}}{2A}
```

Where:

- C_L is the trough after the last loading dose, in mg/L.
- C_M1 is the trough after the first maintenance dose, in mg/L.
- A is the fraction of the last-loading trough that remains after one maintenance interval with no dose. It is computed from the state after N unit loading doses spaced τ_L.
- B is the trough one maintenance dose D_M produces on its own, one interval τ_M after it starts from an empty state.
- G is the target trough from step 1.

Because the model is linear, C_M1 is affine in C_L, so one quadratic gives the loading target. Balancing the two troughs around G keeps the last loading trough below the ceiling and the first maintenance trough above the floor (`linearmodel.cpp:239-251`).

### 4. The loading dose

```math
D_L = \mathcal{D}(\mathbf{x}_{\mathrm{now}},\ N_{\mathrm{rem}},\ \tau_L,\ C_L), \qquad N_{\mathrm{rem}} = \max(0,\ N - K_{\mathrm{past}})
```

Where:

- D_L is each remaining loading dose in mg.
- **x**_now is the compartment state at the next dose time, rebuilt from the recorded doses.
- N_rem is the number of loading doses still to give.
- N is the number of loading doses the clinician entered.
- K_past is the number of individual doses already given.
- τ_L is the loading-dose interval in hours.
- C_L is the loading target from step 3.

A fresh patient gets N loading doses, a patient partway through gets the rest, and a zero or negative result means no more loading is needed (`linearmodel.cpp:253-280`).

### 5. The re-loading dose

Once the loading course is complete, the engine checks whether plain maintenance would let a trough fall below C_min. It considers one re-loading dose D given one maintenance interval before the next maintenance dose:

```math
C_{\mathrm{next}}(D) = p\,D + q, \qquad
C_{\mathrm{first}}(D) = r\,D + s, \qquad
D_R = \max\!\left(0,\ \frac{C_{\min} - q}{p},\ \frac{C_{\min} - s}{r}\right)
```

Where:

- D is a candidate re-loading dose in mg.
- C_next(D) is the trough one maintenance interval after the re-load.
- C_first(D) is the trough after the maintenance dose D_M that follows the re-load.
- p and q, and r and s, are the slopes and intercepts of those two troughs. The engine gets them by evaluating each trough at D = 0 and D = 1, and includes a term only when its slope is positive.
- D_R is the re-loading dose: the smallest dose that lifts both troughs to at least C_min.
- C_min is the desired minimum trough.

The engine recommends D_R, as one dose at the maintenance interval, only when it exceeds D_M. Otherwise maintenance alone keeps both troughs at or above the minimum (`linearmodel.cpp:281-317`). Whichever trough is lower decides the dose, which covers both a patient still in the distribution dip and one past it.

### 6. The forecast window

```math
M = 7 - (K_M \bmod 7)
```

Where:

- M is the number of maintenance doses the concentration graph forecasts.
- K_M is the number of maintenance doses already given, that is, doses beyond the N loading doses.

The graph forecasts the rest of the current block of seven maintenance doses, which is one week at daily dosing: 7 for a fresh patient, 1 after six doses, and 7 again after seven (`src/drug/teicoplanin.hpp:152-162`, `linearmodel.cpp:260-267`).

### 7. Rounding

```math
D^{\downarrow} = \max\!\left(\Delta,\ \Delta \left\lfloor D_{\mathrm{raw}}/\Delta \right\rfloor\right), \qquad
D^{\uparrow} = \max\!\left(\Delta,\ \Delta \left\lceil D_{\mathrm{raw}}/\Delta \right\rceil\right)
```

Where:

- D_raw is a raw loading or maintenance dose from the steps above.
- Δ is the dose increment, 100 mg.
- D↓ and D↑ are the rounded-down and rounded-up candidates.

The loading dose rounds down unless the trough after the rounded-down loading course would fall below C_min, in which case it rounds up. The maintenance dose takes whichever candidate brings the average of seven maintenance troughs, C̄, closer to G on a log scale, measured as |ln(C̄ / G)|. Here C̄ is that seven-trough average in mg/L. The seven-dose window is fixed so the rounded maintenance dose stays stable as doses accumulate (`linearmodel.cpp:346-429`, called from `src/pharmacokinetics/doseprediction/dosageregimen.cpp:201`).

`TroughRange::closer_to_target` scores regimens by simulation on the same log-scale objective. It is a model-agnostic fallback, because rounding normally short-circuits to the closed-form path above (`src/pharmacokinetics/therapeutictarget/trough_range.cpp:23-68`).

## Comparison with published regimens

Expect the recommended loading doses to be well above the product label's 6 mg/kg. That is consistent with the literature, not a defect.

| Source | Target trough | Loading | Maintenance | Renal adjustment |
| --- | --- | --- | --- | --- |
| Product label (SmPC), moderate infection | 15-30 mg/L | 6 mg/kg every 12 h, 3 doses | 6 mg/kg daily | From day 4: half the dose for CrCl 40-60 mL/min, one third below 40 or on hemodialysis |
| Product label (SmPC), severe infection (endocarditis, bone and joint) | 20-40 mg/L | 12 mg/kg every 12 h, 3 doses | 12 mg/kg daily | Same as above |
| Ogami 2020, the population model behind the default | 15-30 mg/L | 15 mg/kg every 12 h, 2 doses | 7.5 mg/kg daily | None; individualized by weight and clearance |

- The label's dosing weight is ideal body weight, or actual weight if lower, and loading is never renally adjusted.
- The Ogami paper found that the 6 mg/kg label loading reached the 15-30 mg/L target on day 1 in far fewer patients than 15 mg/kg did.
- Kim 2024 recommends 14 mg/kg every 12 h for 4 doses. Wang 2023 reports that the standard 400 mg every 12 h for 3 doses fails to reach 10 mg/L within three days in more than half of critically ill patients.
- The engine differs from all fixed regimens in one way: it sizes maintenance from the patient's own clearance and targets G, so renal impairment lowers maintenance without a fixed band.

References:

1. Teicoplanin 400 mg Summary of Product Characteristics. electronic medicines compendium (emc), product 14611.
2. Hanai Y, et al. Clinical practice guidelines for therapeutic drug monitoring of teicoplanin: a consensus review by the Japanese Society of Chemotherapy and the Japanese Society of Therapeutic Drug Monitoring. J Antimicrob Chemother. 2022;77(4):869-879. doi:10.1093/jac/dkab499.
3. Ogami C, et al. Population Pharmacokinetics and Pharmacodynamics of Teicoplanin and C-Reactive Protein in Hospitalized Patients With Gram-Positive Infections. Clin Pharmacol Drug Dev. 2020;9(2):175-188. doi:10.1002/cpdd.684.
4. Kim Y-K, et al. Beyond One-Size-Fits-All: Tailoring Teicoplanin Regimens for Normal Renal Function Patients Using Population Pharmacokinetics and Monte Carlo Simulation. Pharmaceutics. 2024;16(4):499. doi:10.3390/pharmaceutics16040499.
5. Wang Y, et al. Optimal Teicoplanin Dosage Regimens in Critically Ill Patients: Population Pharmacokinetics and Dosing Simulations Based on Renal Function and Infection Type. Drug Des Devel Ther. 2023;17:2259-2271. doi:10.2147/DDDT.S413662.
