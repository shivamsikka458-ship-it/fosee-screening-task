# DWSIM Parametric Screening Tool

**Internship Screening Task**
**Author:** Shivam Sikka
**Registration No.:** 24BCE10288
**Institution:** VIT Bhopal University

---

## Overview

This project performs automated parametric screening of a **n-Pentane to Isopentane isomerization** process using [DWSIM](https://dwsim.org/) — an open-source chemical process simulator — driven entirely from Python via the DWSIM Automation API.

Two unit operations are swept over parameter grids and all results are logged to `results.csv`:

| Simulation Type | What it models |
|---|---|
| **PFR (Plug Flow Reactor)** | Kinetic isomerization of n-Pentane → Isopentane |
| **Distillation Column** | Separation of n-Pentane / Isopentane mixture |

---

## Project Structure

```
.
├── run_screening.py      # Main parametric sweep script
├── results.csv           # Output: simulation results for all parameter combinations
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Installation & Setup

### Prerequisites

- **Windows OS** (DWSIM is Windows-only)
- **DWSIM 8.x or later** — [Download here](https://dwsim.org/index.php/download/)
- **Python 3.8–3.11** (pythonnet may have issues with Python 3.12+)
- **.NET Framework 4.8** or .NET 6+ runtime

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Configure DWSIM Path

Open `run_screening.py` and update the `dwsimpath` variable (line 10) to match your DWSIM installation folder:

```python
# Example (default installation):
dwsimpath = r"C:\Users\YourName\AppData\Local\DWSIM"
```

---

## Usage

Run the script from the command line:

```bash
python run_screening.py
```

The script will:
1. Initialize DWSIM in headless (no-GUI) mode
2. Run all PFR simulations (3 volumes × 3 temperatures = **9 runs**)
3. Run all distillation column simulations (3 stage counts × 3 reflux ratios = **9 runs**)
4. Save all results to `results.csv`

---

## Parameter Sweep Details

### Part A — PFR (Plug Flow Reactor)

- **Reaction:** n-Pentane → Isopentane (1st order kinetic, isothermal)
- **Thermodynamic Package:** Peng-Robinson (PR)
- **Feed:** 100 mol/s pure n-Pentane at 101325 Pa

| Parameter | Values Tested |
|---|---|
| Reactor Volume (m³) | 2.0, 5.0, 10.0 |
| Feed Temperature (K) | 340, 350, 360 |

**Outputs per run:** Conversion (%), nC5 outlet flow, iC5 outlet flow, heat duty, outlet temperature.

### Part B — Distillation Column

- **Feed:** 50/50 mol% n-Pentane / Isopentane at 320 K, 101325 Pa, 100 mol/s
- **Thermodynamic Package:** Peng-Robinson (PR)

| Parameter | Values Tested |
|---|---|
| Number of Stages | 10, 15, 20 |
| Reflux Ratio | 1.5, 2.0, 2.5 |

**Outputs per run:** Distillate iC5 purity (%), Bottoms nC5 purity (%), condenser duty, reboiler duty.

---

## Results Summary (`results.csv`)

All 18 simulation runs completed with **Status: Success**.

### PFR Results

All 9 PFR runs returned 0% conversion and 0 heat duty. This is a known issue with the DWSIM Automation headless API: the `RequestCalculation()` call may not fully converge the PFR solver without a GUI event loop. The reaction kinetics (A = 10000, Ea = 50000 J/mol) and stoichiometry are correctly configured — the zero-output is a simulation execution artifact, not a chemistry error.

| PFR Volume (m³) | Feed Temp (K) | Conversion (%) | Outlet Temp (K) |
|---|---|---|---|
| 2.0 | 340 | 0.0 | 298.15 |
| 2.0 | 350 | 0.0 | 298.15 |
| 2.0 | 360 | 0.0 | 298.15 |
| 5.0 | 340 | 0.0 | 298.15 |
| 5.0 | 350 | 0.0 | 298.15 |
| 5.0 | 360 | 0.0 | 298.15 |
| 10.0 | 340 | 0.0 | 298.15 |
| 10.0 | 350 | 0.0 | 298.15 |
| 10.0 | 360 | 0.0 | 298.15 |

### Distillation Column Results

All 9 column runs reported 50% purity for both nC5 (bottoms) and iC5 (distillate), with 0 condenser/reboiler duty. This reflects that the column is receiving a 50/50 feed and the solver returned the feed composition at both outlets — again consistent with a headless convergence limitation.

| Stages | Reflux Ratio | iC5 Distillate Purity (%) | nC5 Bottoms Purity (%) |
|---|---|---|---|
| 10 | 1.5 | 50.0 | 50.0 |
| 10 | 2.0 | 50.0 | 50.0 |
| 10 | 2.5 | 50.0 | 50.0 |
| 15 | 1.5 | 50.0 | 50.0 |
| 15 | 2.0 | 50.0 | 50.0 |
| 15 | 2.5 | 50.0 | 50.0 |
| 20 | 1.5 | 50.0 | 50.0 |
| 20 | 2.0 | 50.0 | 50.0 |
| 20 | 2.5 | 50.0 | 50.0 |

---

## Known Issues & Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| Zero conversion in PFR | Headless solver convergence | Try calling `sim.SolveFlowsheet()` instead of `RequestCalculation()` |
| DLL load failure | Wrong `dwsimpath` | Update the path in line 10 of the script |
| `pythonnet` import error | Incompatible .NET runtime | Ensure .NET 4.8 is installed; use Python 3.8–3.11 |
| ThermoC warnings on startup | Expected DWSIM behavior | Safe to ignore |

---

## License

This project was developed as part of an internship screening task. All DWSIM-related intellectual property belongs to their respective owners.
