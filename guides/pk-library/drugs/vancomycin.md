# Vancomycin in PK-Library

This guide covers how PK-Library (the C++ dosing engine) handles vancomycin: its drug settings, how it picks a model, the Rodvold 1988 default adult model with its declared but unapplied fitting constraint, and the Goti 2018 model. Read it before you change vancomycin code or explain a vancomycin result to a clinician.

Paths are relative to PK-Library (`src/packages/cpp/PK-Library` in the umbrella repository). Symbols keep one physical meaning throughout: CL is clearance, V is a volume, and k is a first-order rate constant. Each model section gives that model's own prior formulas.

## Drug settings

| Setting | Value | Source |
| --- | --- | --- |
| Routes | Intermittent IV and continuous IV. | `src/drug/vancomycin.hpp:655-660` |
| Targets, intermittent IV | AUC/MIC, trough, peak, and trough with peak. | `src/drug/vancomycin.hpp:666-672` |
| Targets, continuous IV | AUC/MIC and average concentration. | `src/drug/vancomycin.hpp:673-675` |
| Default target ranges | AUC/MIC 400-600, trough 10-15 mg/L, peak 0-35 mg/L, average concentration 20-25 mg/L. | `src/drug/vancomycin.hpp:997-1017` |
| Therapeutic range | 10-50 mg/L. | `src/drug/vancomycin.hpp:717-722` |
| Toxic levels | Trough 20 mg/L and peak 50 mg/L, stored as 0.02 and 0.05 mg/mL. | `src/drug/vancomycin.hpp:692-699` |
| Dose increment | 250 mg for adults and 5 mg under 18. Dose rounding is enabled only for patients 18 and older by default. | `src/common/pkconstants.cpp:117-118`, `src/drug/drug.cpp:356-358` |
| Recommended intervals | 8, 12 or 24 h for adults and 6, 8 or 12 h under 18 before PK is known. Once PK exists, the choices follow the half-life. | `src/drug/vancomycin.hpp:749-772` |
| Recommended infusion times | 1, 2 or 3 h for adults and 1, 1.5 or 2 h under 18. | `src/drug/vancomycin.hpp:774-780` |
| Default infusion time | 1 h, plus 0.25 h for every 250 mg above 1000 mg. | `src/drug/vancomycin.hpp:782-801` |
| Fitting defaults | Assay error 0.1, fixed error (SEM) 1.25 mg/L, time-weight factor 1.01 when critically ill or in ICU and 1.005 otherwise. | `src/drug/vancomycin.hpp:803-823` |
| Dose and level warnings | Max daily dose, loading dose, AUC, trough, MIC, treatment length and dialysis sampling rules. | `src/drug/vancomycin.hpp:831-970` |

## How a model is chosen

Auto-select (`determine_model`) returns the first rule that matches. IHD means high-flux intermittent hemodialysis, and CRRT means continuous renal replacement therapy.

| Order | Patient | Model |
| --- | --- | --- |
| 1 | Under 18, at least 3 months old, obese-pediatric factor set | Le-Stockmann 2015 |
| 2 | Under 18, at least 9 years old, cystic fibrosis | Stockmann 2019 |
| 3 | Under 6 months, post-cardiac surgery | Moffett 2019 |
| 4 | Under 3 months | Frymoyer-Stockmann |
| 5 | Other patients under 18 | Le-Stockmann-Frymoyer when SCr is below 0.9 mg/dL, otherwise Le-Stockmann 2014 |
| 6 | Adult on IHD and critically ill | Claisse 2019 intermittent |
| 7 | Adult on CRRT | Claisse 2019 continuous |
| 8 | Adult on IHD, not critically ill | Westra 2019 |
| 9 | Adult with a hematologic malignancy or acute myeloid leukemia | Buelga 2005 |
| 10 | Adult, obese class 3, Crass CrCl at least 80 mL/min and at least 30 mL/min/1.73 m², and none of cystic fibrosis, pregnancy, ICU, burn, HLA-A*32:01, IHD or CRRT | Crass 2018 |
| 11 | Any other adult | Rodvold 1988 |

Source: `src/drug/vancomycin.hpp:209-323`.

- An explicitly requested model name is used as given. The default aliases and six unselectable models (Thomson 2009, Moffett 2018, Avedissian 2017, Marques 2010, Zhao 2014, Carreno 2017) fall through to auto-select instead (`src/drug/vancomycin.hpp:223-232`).
- The list a clinician can pick from (`models_for_patient`) is wider than auto-select. Rodvold 1988 is always offered. Goti 2018 is offered only to critically ill adults who are not on IHD or CRRT, and auto-select never returns it (`src/drug/vancomycin.hpp:66-207`).
- Obesity factors are set automatically from BMI: class 1 from 30, class 2 from 35, class 3 from 40, and pediatric obesity for ages 2 to 18 from BMI percentile tables (`src/patient/bodycomposition.cpp:261-282`, `src/drug/drug.cpp:160-173`). Obesity classes 1 and 2 therefore stay on Rodvold 1988.

## Drug factors

| Factor | Offered to | Effect | Source |
| --- | --- | --- | --- |
| Critically ill or ICU | Adults | Raises the Rodvold 1988 volume prior by 13% and sets the time-weight factor to 1.01. | `src/pharmacokinetics/study/vancomycin/vancomycinrodvold1988.hpp:92-95` |
| IHD | Adults | Selects Westra 2019, or Claisse 2019 intermittent when also critically ill. Checking it unchecks CRRT. | `src/drug/vancomycin.hpp:507-516` |
| CRRT | Adults | Selects Claisse 2019 continuous. Checking it also checks ICU and unchecks IHD. | `src/drug/vancomycin.hpp:518-528` |
| Hematologic malignancy or AML | Adults | Selects Buelga 2005. | `src/drug/vancomycin.hpp:538-557` |
| Burn patient | All ages | Caps calculated CrCl at 250 mL/min instead of the usual cap of 2 SD above the mean. This applies to every drug. | `src/patient/labreport.cpp:104-131` |
| Pregnancy | Females | Shows a formulation warning. | `src/drug/vancomycin.hpp:953-955` |
| HLA-A*32:01 allele | All ages | Shows a DRESS risk warning. | `src/drug/vancomycin.hpp:956-959` |
| Post-cardiac surgery | 6 months and younger | Selects Moffett 2019. | `src/drug/vancomycin.hpp:607-612` |
| Cystic fibrosis | 9 to under 18 | Selects Stockmann 2019. | `src/drug/vancomycin.hpp:613-617` |
| Indomethacin or ibuprofen for PDA closure | Under 1 month | Multiplies CL by 0.5 or 0.72 in Caparelli 2001, Frymoyer-Stockmann and Moffett 2019. Rodvold 1988 does not apply it. | `src/pharmacokinetics/study/vancomycin/vancomycincaparelli2001.hpp:41-47` |

## Rodvold 1988, the default adult model

Rodvold 1988 is a two-compartment model inherited from TDMS, the original PrecisePK desktop product. It fits two parameters, CL and the terminal-phase volume Vdβ, and derives everything else (`src/pharmacokinetics/study/vancomycin/vancomycintdms.hpp:16`). `VancomycinRodvold1988` supplies the population formulas. It inherits the fitted-parameter list, the derived constants and the unused constraint from `VancomycinTDMS`, which in turn builds on the shared two-compartment classes `VancomycinTwoCompartment` and `TwoCompartment`.

### Clearance prior

```math
\mathrm{CL} = a \cdot \mathrm{CrCl}(t) + b \cdot W_{\mathrm{adj}}
```

Where:

- CL is the clearance prior in L/h, with a prior coefficient of variation of 0.5.
- CrCl(t) is the creatinine clearance in effect at time t, in mL/min (`Patient::crcl_at`).
- t is the time the estimate applies to. With two or more CrCl entries, the engine stores a CL multiplier per CrCl entry, which makes CL time-varying (`vancomycintdms.hpp:74-85`).
- W_adj is the legacy adjusted weight in kg. It is total body weight when that is at or below ideal body weight, and otherwise the larger of lean body mass and ideal body weight (`src/patient/bodycomposition.cpp:122-146`).
- a is 0.79 × 0.06 = 0.0474 (L/h) per (mL/min). The 0.79 is the Rodvold 1988 slope of CL on CrCl, and 0.06 converts mL/min to L/h.
- b is 0.05 × 0.06 = 0.003 (L/h) per kg. The 0.05 mL/min/kg is non-renal clearance from Rodvold 1989.

Source: `vancomycinrodvold1988.hpp:20-28, 33-66`.

### Volume prior

```math
\mathrm{Vd}_\beta = d \cdot W_{\mathrm{dose}} \cdot m
```

Where:

- Vdβ is the terminal-phase volume prior in L, with a prior coefficient of variation of 0.3.
- W_dose is the dosing weight in kg. When total body weight (TBW) exceeds ideal body weight (IBW), it is the adjusted body weight IBW + 0.4 × (TBW − IBW). Otherwise, and for infants under 1 year, it is TBW (`src/patient/bodycomposition.cpp:148-190`).
- d is 0.7 L/kg. Adults with CrCl below 10 mL/min use 1.0 L/kg (Tan 1990) instead (`vancomycintdms.hpp:149-163`).
- m is 1.13 for critically ill or ICU patients and 1 otherwise. The Tan 1990 branch skips it.

Source: `vancomycinrodvold1988.hpp:71-98`.

### Derived values

```math
V_c = 0.17 \cdot W_{\mathrm{dose}}, \quad
\beta = \frac{\mathrm{CL}}{\mathrm{Vd}_\beta}, \quad
k_{10} = \frac{\mathrm{CL}}{V_c}, \quad
k_{21} = 0.46, \quad
\alpha = \frac{k_{10}\,k_{21}}{\beta}, \quad
k_{12} = \alpha + \beta - k_{21} - k_{10}, \quad
V_p = \frac{V_c\,k_{12}}{k_{21}}, \quad
Q = V_c\,k_{12}
```

Where:

- V_c is the central volume in L. Adults with CrCl below 10 mL/min use 0.45 instead of 0.17.
- β is the terminal (slow) rate constant, in 1/h.
- k_10 is the elimination rate constant from the central compartment, in 1/h.
- k_21 is the peripheral-to-central rate constant, fixed at 0.46 1/h, a value the code attributes to three published data sets.
- α is the distribution (fast) rate constant, in 1/h.
- k_12 is the central-to-peripheral rate constant, in 1/h.
- V_p is the peripheral volume in L, and Q is the intercompartmental clearance in L/h.

Sources: `vancomycinrodvold1988.hpp:100-149`, `vancomycintdms.hpp:106-147, 194-199`, `src/pharmacokinetics/model/twocompartment.cpp:395-420`.

For a 70 kg patient at or below ideal body weight with CrCl 100 mL/min, these give CL 4.95 L/h, Vdβ 49 L, V_c 11.9 L, β 0.101 1/h, k_10 0.416 1/h, α 1.89 1/h and k_12 1.12 1/h.

Details that are easy to miss:

- CL follows CrCl over time, but Vdβ, V_c and the CrCl-below-10 switch read only the latest CrCl (`Patient::crcl()`).
- A time-varying CL turns off the closed-form concentration shortcut, so every prediction for that patient is simulated numerically (`src/pharmacokinetics/model/model.cpp:730-745`).
- The coefficients a, b and d are exposed through `coefficients()` as `CRCL`, `ADJUSTED_WEIGHT` and `DOSING_WEIGHT`, so an institution can refit them. See [Local population models](../local-population.md).
- Nine citations attached to CL carry an in-code question about whether they are used (`vancomycinrodvold1988.hpp:54-63`). Clinicians see these citations, so confirm them before adding more.

### The fitting constraint: declared, not applied

`VancomycinTDMS::fitted_param_constraints` declares bounds that keep β below k_21 (`vancomycintdms.hpp:165-174`). **The engine does not apply them.** Nothing calls `fitted_param_constraints` for any model, the base class returns empty maps (`src/pharmacokinetics/model/model.cpp:49`), and the declaration is marked as a TODO (`src/pharmacokinetics/model/model.hpp:269-272`). The only bound the optimizer enforces is bioavailability F ≤ 1 (`src/pharmacokinetics/bayesianfitting/bayesianfitting.cpp:281, 441-448`). No test covers the constraint.

The constraint exists because k_12 can go negative. Substituting α into the k_12 formula gives:

```math
k_{12} = \frac{(\beta - k_{10})(\beta - k_{21})}{\beta}
```

Where β, k_10, k_12 and k_21 are the rate constants defined above.

While Vdβ stays above V_c, β is below k_10. The priors satisfy this, since 0.7 exceeds 0.17 and 1.0 exceeds 0.45 for the same dosing weight. In that case k_12 is positive exactly when β is below k_21. A fit that reaches β ≥ k_21 produces k_12 ≤ 0, and therefore V_p ≤ 0 and Q ≤ 0, which is not a valid two-compartment model. Typical fits have a wide margin (β is 0.101 against 0.46 in the example above), but a high-CL, low-Vdβ fit can cross it.

The declared bounds add a 1% margin on each side of β = k_21:

```math
\mathrm{Vd}_\beta \ge \frac{1.01\,\mathrm{CL}}{k_{21}}, \qquad \mathrm{CL} \le 0.99\,k_{21}\,\mathrm{Vd}_\beta
```

Where CL and Vdβ are the current fitted values. Each bound is recomputed from the other parameter's current value, because the function receives the current parameter container.

The intended enforcement is a projected step. The Levenberg-Marquardt loop updates the fitted vector θ = (CL, Vdβ) as θ ← θ − δ (`bayesianfitting.cpp:299-300`). An implementation would check the tentative point and, when it violates the constraint, replace it with its orthogonal projection onto the boundary line CL = s · Vdβ:

```math
P(\theta') = \frac{s\,\mathrm{CL}' + \mathrm{Vd}_\beta'}{s^2 + 1}\,(s,\ 1), \qquad s = 0.99\,k_{21}
```

Where:

- θ is the current fitted vector (CL, Vdβ), and δ is the step the optimizer computed.
- θ' = (CL', Vdβ') = θ − δ is the tentative next point.
- s is the slope of the boundary line, set just inside β = k_21.
- P(θ') is the projected point, so the corrected step is θ − P(θ').

Projecting onto the line, instead of stopping where the step crosses it, lets the fit keep moving along the boundary toward the optimum when the step is not perpendicular to the boundary.

## Goti 2018

Goti 2018 is a two-compartment model built from hospitalized adults with and without hemodialysis (Goti et al., Ther Drug Monit 2018;40:212-221). It fits CL, V_c and V_p, and keeps Q constant (`src/pharmacokinetics/study/vancomycin/vancomycingoti2018.hpp:19`). It supports intermittent and continuous IV.

It is used in two places:

- Clinicians can select it for critically ill adults who are not on IHD or CRRT. Auto-select never picks it.
- Its CL, V_c, V_p and Q formulas are the off-dialysis parameters of Claisse 2019 intermittent, which auto-select picks for critically ill adults on IHD (`src/pharmacokinetics/study/vancomycin/vancomycinclaisse2019_intermittent.hpp:73-92, 138`). This is where the dialysis multipliers below take effect in practice.

```math
\mathrm{CL} = 4.5 \left(\frac{\mathrm{GFR}}{120}\right)^{0.8} D_{\mathrm{CL}}
```

Where:

- CL is the clearance prior in L/h, with a relative SD of 0.398.
- GFR is the CKD-EPI 2009 eGFR in mL/min/1.73 m², computed from the current SCr and not de-normalized to the patient's BSA (`src/formulas/crcl.cpp:446`).
- D_CL is 0.7 when the IHD or CRRT factor is set, and 1 otherwise.

```math
V_c = 58.4 \cdot \frac{W_G}{70} \cdot D_V, \qquad V_p = 38.4, \qquad Q = 6.5
```

Where:

- V_c is the central volume prior in L, with a relative SD of 0.816.
- W_G is the Goti dosing weight in kg. It is lean body weight (`src/patient/bodycomposition.cpp:192-215`) for patients 65 or older or with BMI 30 or above, and adjusted body weight otherwise.
- D_V is 0.5 when the IHD or CRRT factor is set, and 1 otherwise.
- V_p is the peripheral volume prior in L, with a relative SD of 0.571.
- Q is the intercompartmental clearance, fixed at 6.5 L/h and not fitted.

```math
k_{10} = \frac{\mathrm{CL}}{V_c}, \qquad k_{12} = \frac{Q}{V_c}, \qquad k_{21} = \frac{Q}{V_p}
```

Where k_10, k_12 and k_21 are the rate constants defined for Rodvold 1988. Here k_21 is derived from Q and V_p instead of fixed. α and β come from these micro-constants as the roots of the two-compartment system (`src/pharmacokinetics/model/twocompartment.cpp:424-452`).

Source for the formulas: `vancomycingoti2018.hpp:68-210`. Some comments in that file say "Claisse 2019". They are stale; the model is Goti 2018.

This model applies no CrCl ceiling of 150 mL/min and no SCr floor of 1.0 mg/dL for patients over 65. It uses CKD-EPI 2009 GFR, not Cockcroft-Gault.
