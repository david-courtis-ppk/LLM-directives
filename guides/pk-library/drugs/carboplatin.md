# Carboplatin in PK-Library

This guide covers how PK-Library doses carboplatin with its single model, Lindauer 2010, including the infusion-duration effect on clearance. Read it before you change carboplatin code or explain a carboplatin recommendation.

Paths are relative to PK-Library (`src/packages/cpp/PK-Library` in the umbrella repository).

## Drug settings

| Setting | Value | Source |
| --- | --- | --- |
| Routes | Intermittent IV and continuous IV. The code comment above `routes()` that says "only intermittent IV" is stale. | `src/drug/carboplatin.hpp:32-37` |
| Target | AUC per dose only, in min·mg/mL. Concentrations are in mg/L. | `src/drug/carboplatin.hpp:40-42, 61-70` |
| Dosage type | Single dose. There is no nomogram and no loading dose. | `src/drug/carboplatin.hpp:73-82, 93` |
| Default interval | 336 h (14 days). | `src/drug/carboplatin.hpp:84-86` |
| Default infusion time | 1 h for intermittent IV and 24 h for continuous IV. | `src/drug/carboplatin.hpp:88-90` |
| Dose increment | 5 mg, the `Drug` default. | `src/drug/drug.cpp:339-341` |
| Fitting defaults | Assay error 0.1, fixed error (SEM) 1.25 mg/L, time-weight factor 1.01. The code marks these as placeholders to revisit. | `src/drug/carboplatin.hpp:55-58` |
| Therapeutic and toxic ranges | None are defined; both limits return 0. | `src/drug/carboplatin.hpp:47-53` |
| Antibiotic | No. | `src/drug/carboplatin.hpp:45` |

## The model: Lindauer 2010

Lindauer 2010 is the only carboplatin model, and auto-select always returns it (`src/drug/carboplatin.hpp:21-29`). It is a two-compartment model with first-order elimination, built from 69 patients aged 2 to 60 on high-dose carboplatin (Lindauer A, et al. Ther Drug Monit. 2010;32(2):159-68). The engine shows a note whenever it is selected: the model is for high-dose carboplatin with autologous stem cell rescue, not conventional dosing, where the Calvert formula may be more accurate (`src/common/pkconstants.cpp:819-827`).

The model fits four parameters: CL, V_c, V_p and Q (`src/pharmacokinetics/study/carboplatin_lindauer2010.hpp:23-25`). Patients under 12 use the pediatric coefficients, and everyone else uses the non-pediatric ones.

### Clearance

```math
\mathrm{CL}_{<12} = 0.06 \times 114.2 \left(\frac{\mathrm{CrCl}}{103.1}\right)^{0.34} \left(\frac{W}{70}\right)^{0.75}
\qquad
\mathrm{CL}_{\ge 12} = 0.06 \times 109.8 \left(\frac{\mathrm{CrCl}}{103.1}\right)^{0.57} \left(\frac{H}{176}\right)^{1.43}
```

Where:

- CL is the clearance prior in L/h, for patients under 12 or 12 and older as subscripted. The factor 0.06 converts the study's mL/min to L/h.
- CrCl is the creatinine clearance in mL/min at the time of the estimate.
- W is total body weight in kg.
- H is height in cm.

Source: `carboplatin_lindauer2010.hpp:234-255`.

### Volumes and intercompartmental clearance

```math
V_c = c_V \cdot W, \qquad V_p = p_V \cdot W, \qquad Q = 0.06 \cdot q_Q \cdot W
```

Where:

- V_c is the central volume prior in L, and V_p is the peripheral volume prior in L.
- Q is the intercompartmental clearance prior in L/h.
- W is total body weight in kg.
- c_V, p_V and q_Q are the per-kg coefficients in the table below. The factor 0.06 converts q_Q from mL/min/kg to L/h/kg.

| Parameter | Under 12 | 12 and older | Relative SD, under 12 | Relative SD, 12 and older |
| --- | --- | --- | --- | --- |
| CL | See the formula above | See the formula above | 0.129 | 0.084 |
| c_V (L/kg) | 0.3132 | 0.2931 | 0.078 | 0.036 |
| p_V (L/kg) | 0.4813 | 0.4641 | 0.0731 | 0.0879 |
| q_Q (mL/min/kg) | 0.2040 | 0.1997 | 0.166 | 0.161 |

Source: `carboplatin_lindauer2010.hpp:113-175`.

### Infusion duration changes clearance

Carboplatin clears faster the longer it is infused. The engine keeps the base CL formula with the study's DUR covariate (infusion duration effect) at 0, then multiplies CL by a factor that depends on the infusion time of each dose:

```math
\mathrm{CL}_{\mathrm{eff}} = \mathrm{CL} \cdot \left(1 + f(T)\right),
\qquad
f(T) = \begin{cases} -0.00002\,T^2 + 0.0075\,T - 0.0075 & T < 96 \\ 0.536 & T \ge 96 \end{cases}
```

Where:

- CL_eff is the clearance used in simulation for a dose infused over T hours.
- CL is the clearance prior from the formulas above.
- T is the infusion duration of the dose in hours.
- f(T) is the fitted infusion-duration effect. It is about 0 for a 1 h infusion, 0.161 at 24 h, and 0.536 from 96 h, matching the study's values for those durations.

Source: `carboplatin_lindauer2010.hpp:53-60`, applied through `adjusts_params_by_infusion_time()` (`:66`) and `PKContainer::adjust_to_infusion_time` (`src/pharmacokinetics/model/pkcontainer.hpp:185-197`).

### Derived values

```math
k_{10} = \frac{\mathrm{CL}}{V_c}, \quad k_{12} = \frac{Q}{V_c}, \quad k_{21} = \frac{Q}{V_p}, \quad
\alpha, \beta = \frac{(k_{10} + k_{12} + k_{21}) \pm \sqrt{(k_{10} + k_{12} + k_{21})^2 - 4\,k_{10}\,k_{21}}}{2}
```

Where k_10 is the elimination rate constant, k_12 and k_21 are the transfer rate constants between the central and peripheral compartments, α is the distribution rate constant (the + root), and β is the terminal rate constant (the − root), all in 1/h. Bioavailability F is 1 with a relative SD of 0.05. Source: `carboplatin_lindauer2010.hpp:105-110, 259-315`.

## Details that are easy to miss

- Every carboplatin prediction is simulated numerically. The infusion-duration factor disables the closed-form shortcut (`src/pharmacokinetics/model/model.cpp:738`).
- With two or more CrCl entries, CL also carries a per-entry multiplier over time (`carboplatin_lindauer2010.hpp:44-51`).
- The model overrides its CrCl formula: Cockcroft-Gault for patients 12 and older, using adjusted body weight when BMI is 25 or above and flooring SCr at 0.7 mg/dL, and the child Schwartz formula under 12 (`carboplatin_lindauer2010.hpp:177-204`). That override feeds `Model::crcl_used` and the model-aware CrCl history the bindings return. The CL prior instead reads `Patient::crcl_at` (`:240`), which builds CrCl from the institution's configured formula without the model (`src/patient/patient.cpp:52-54`, `src/patient/labreport.cpp:233-242`). The two CrCl values can differ for the same patient.
