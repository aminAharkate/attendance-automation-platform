# Attendance Master (Pointage RH Automation)

An automated solution for integrating daily biometric/supervisor attendance Excel exports (`atacadao_attendance_YYYY-MM-DD.xlsx`) into the monthly **Base RH Pointage Quotidien** master workbook.

---

## Features

1. **Intelligent Name Matching**:
   - Handles `NOM PRENOM` vs `PRENOM NOM` inversions.
   - Accents and special character normalization (e.g. `É` vs `E`, `-`).
   - Fuzzy typo tolerance (e.g. matches `LAMYAE LAHMANE` in daily export to `LAHMAME LAMYAE` in Base RH).
   - Multi-contract synchronization (automatically updates both `INTERIM EXPRESS - OUBAHA` and `INTERIM EXPRESS - OGLO NUTS` rows for part-time merchandisers).

2. **Accurate Status Conversion**:
   - `Present (P)` &rarr; `0.5` (for Part-Time) or `1.0` (Full-Time)
   - `Day off (D-O)` &rarr; `'D-O'`
   - `Récup (R)` &rarr; `'R'`
   - `Resigned (Démission)` &rarr; `'Démission'`
   - `Absent` &rarr; `0`
   - `Congé Maladie (CM)` &rarr; `'CM'`
   - `Congé Payé (CP)` &rarr; `'CP'`

3. **Rest-of-Month Propagation**:
   - Automatically carries forward past resignations (`Démission`).
   - Extends any new resignations to the remaining days of the month (Days X to 31).
   - Option to mark unmarked active staff as Absent (`0`).

4. **100% Excel Style & Formula Preservation**:
   - Uses OpenPyXL to preserve sheet formatting, colors, column widths, and other tabs (`Entrants`, `Sortants`, `Part Time`, `Renfort`, etc.).

---

## How to Run

### Method 1: Web Application (Recommended)
1. Double-click the file:
   ```
   Start_Attendance_App.bat
   ```
2. Your browser will automatically open:
   ```
   http://localhost:5000
   ```
3. Click **"Analyze & Preview Matches"** to see live KPIs and row matches.
4. Click **"Apply & Save Updated Workbook"** to generate the updated Excel file.

### Method 2: Command Line (CLI)
Using your Anaconda terminal:
```bash
cd "c:\Users\Dell\Downloads\ATTANDECE_PROJECT"
C:\Users\Dell\anaconda3\python.exe run_cli.py
```
Or specify explicit files:
```bash
C:\Users\Dell\anaconda3\python.exe run_cli.py --base "Base RH_Pointage Quotidien Octobre 2026 (18).xlsx" --daily "atacadao_attendance_2026-10-20_to_2026-10-20 (1).xlsx"
```
