"""
Attendance Core Processor
Handles matching between daily attendance exports (e.g. atacadao_attendance_YYYY-MM-DD.xlsx)
and monthly Base RH tracking workbooks (e.g. Base RH_Pointage Quotidien [Month] [Year].xlsx).
"""

import os
import re
import difflib
import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment

def normalize_str(s):
    """Normalize names for robust matching (removes accents, extra spaces, uppercase)."""
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = re.sub(r'[\s\-_]+', ' ', s)
    s = s.replace('É', 'E').replace('È', 'E').replace('Ê', 'E').replace('Ë', 'E')
    s = s.replace('À', 'A').replace('Â', 'A').replace('Ä', 'A')
    s = s.replace('Î', 'I').replace('Ï', 'I')
    s = s.replace('Ô', 'O').replace('Ö', 'O')
    s = s.replace('Ù', 'U').replace('Û', 'U').replace('Ü', 'U')
    s = s.replace('Ç', 'C')
    return s.strip()

def fuzzy_match(name1, name2, threshold=0.84):
    """Fuzzy check if two names match, handling inversions, middle names, and small typos."""
    n1 = normalize_str(name1)
    n2 = normalize_str(name2)
    
    if not n1 or not n2:
        return False
        
    if n1 == n2:
        return True
        
    tokens1 = sorted(n1.split())
    tokens2 = sorted(n2.split())
    if tokens1 == tokens2:
        return True
        
    # Check token overlap
    s1, s2 = set(tokens1), set(tokens2)
    if s1 and s2 and (s1.issubset(s2) or s2.issubset(s1)):
        return True
        
    # SequenceMatcher ratio
    ratio1 = difflib.SequenceMatcher(None, n1, n2).ratio()
    ratio2 = difflib.SequenceMatcher(None, " ".join(tokens1), " ".join(tokens2)).ratio()
    
    return max(ratio1, ratio2) >= threshold

def map_status(status_str, matricule="Part Time", part_time_val=0.5, full_time_val=1.0):
    """
    Translates raw supervisor/merch status into the standard Base RH value:
    - Present -> 0.5 (for Part Time) or 1.0 (Full Time)
    - Day off (D-O) -> 'D-O'
    - Récup (R) -> 'R'
    - Resigned (Démission) -> 'Démission'
    - Absent -> 0
    - Congé Maladie -> 'CM'
    - Congé Payé -> 'CP'
    - Congé Spécial -> 'CS'
    - Jour Férié -> 'JF'
    """
    if not status_str or pd.isna(status_str):
        return None
        
    s = str(status_str).strip()
    s_clean = normalize_str(s)
    
    is_part_time = "PART TIME" in normalize_str(matricule)
    present_score = part_time_val if is_part_time else full_time_val
    
    if "PRESENT" in s_clean or "(P)" in s or s == "P":
        return present_score
    elif "DAY OFF" in s_clean or "(D-O)" in s or "D-O" in s:
        return "D-O"
    elif "RECUP" in s_clean or "(R)" in s or s == "R":
        return "R"
    elif "RESIGNED" in s_clean or "DEMISSION" in s_clean or "MISSION" in s_clean:
        return "Démission"
    elif "MALADIE" in s_clean or "(CM)" in s or s == "CM":
        return "CM"
    elif "PAYE" in s_clean or "PAY" in s_clean or "(CP)" in s or s == "CP":
        return "CP"
    elif "SPECIAL" in s_clean or "(CS)" in s or s == "CS":
        return "CS"
    elif "ABSENT" in s_clean or "ABS" in s:
        return 0
    elif "FERIE" in s_clean or "JF" in s:
        return "JF"
        
    return s

class AttendanceProcessor:
    def __init__(self, base_file_path):
        self.base_file_path = base_file_path
        self.wb = openpyxl.load_workbook(base_file_path)
        self.main_sheet_name = self._detect_main_sheet()
        self.ws = self.wb[self.main_sheet_name]
        self.header_row_idx = self._detect_header_row()
        self.day_columns = self._detect_day_columns()
        self.employees = self._load_employees()

    def _detect_main_sheet(self):
        """Find the main EFFECTIF GLOBAL sheet."""
        for sheet in self.wb.sheetnames:
            if "EFFECTIF" in sheet.upper() or "GLOBAL" in sheet.upper():
                return sheet
        # Fallback to first sheet
        return self.wb.sheetnames[0]

    def _detect_header_row(self):
        """Identify row containing Day numbers (1..30/31)."""
        for r in range(1, min(25, self.ws.max_row + 1)):
            row_vals = [self.ws.cell(r, c).value for c in range(1, min(45, self.ws.max_column + 1))]
            numbers = [v for v in row_vals if isinstance(v, int) and 1 <= v <= 31]
            if len(numbers) >= 20: # Strong signal for days 1..28+
                return r
        return 12 # Standard fallback for Base RH

    def _detect_day_columns(self):
        """Map day integer (1..31) to column index."""
        day_map = {}
        for c in range(1, self.ws.max_column + 2):
            val = self.ws.cell(self.header_row_idx, c).value
            if isinstance(val, int) and 1 <= val <= 31:
                day_map[val] = c
            elif isinstance(val, str) and val.strip().isdigit():
                d = int(val.strip())
                if 1 <= d <= 31:
                    day_map[d] = c
                    
        # If Day 31 is missing from header row in months with 31 days, add to next column
        if 30 in day_map and 31 not in day_map:
            col_31 = day_map[30] + 1
            day_map[31] = col_31
            self.ws.cell(self.header_row_idx, col_31).value = 31
            
        return day_map

    def _load_employees(self):
        """Read all employee rows starting right after the header row."""
        employees = []
        for r in range(self.header_row_idx + 1, self.ws.max_row + 1):
            soc = self.ws.cell(r, 1).value
            contract_type = self.ws.cell(r, 2).value
            cin = self.ws.cell(r, 3).value
            matricule = self.ws.cell(r, 4).value
            nom = self.ws.cell(r, 5).value or ""
            prenom = self.ws.cell(r, 6).value or ""
            function = self.ws.cell(r, 7).value
            dept = self.ws.cell(r, 8).value
            ville = self.ws.cell(r, 9).value
            user_id = self.ws.cell(r, 10).value
            supervisor = self.ws.cell(r, 11).value
            
            # Skip empty rows
            if not nom and not prenom and not cin and not user_id:
                continue
                
            nom_str = str(nom).strip()
            prenom_str = str(prenom).strip()
            
            employees.append({
                'row': r,
                'soc': str(soc or "").strip(),
                'contract_type': str(contract_type or "").strip(),
                'cin': str(cin or "").strip(),
                'matricule': str(matricule or "").strip(),
                'nom': nom_str,
                'prenom': prenom_str,
                'full_name_1': f"{nom_str} {prenom_str}".strip(),
                'full_name_2': f"{prenom_str} {nom_str}".strip(),
                'function': str(function or "").strip(),
                'dept': str(dept or "").strip(),
                'ville': str(ville or "").strip(),
                'user_id': str(user_id or "").strip(),
                'supervisor': str(supervisor or "").strip()
            })
        return employees

    def match_employee(self, daily_name):
        """Return all matching employee rows for a given merchandiser name."""
        matches = []
        for emp in self.employees:
            if (fuzzy_match(daily_name, emp['full_name_1']) or 
                fuzzy_match(daily_name, emp['full_name_2'])):
                matches.append(emp)
        return matches

    def preview_daily_file(self, daily_file_path):
        """Parse daily file and generate a preview of records and matches."""
        df = pd.read_excel(daily_file_path)
        
        # Determine date
        dates = df['date'].dropna().tolist() if 'date' in df.columns else []
        detected_date_str = str(dates[0])[:10] if dates else datetime.date.today().isoformat()
        try:
            parsed_date = pd.to_datetime(detected_date_str)
            day_number = parsed_date.day
            month_number = parsed_date.month
            year_number = parsed_date.year
        except Exception:
            today = datetime.date.today()
            day_number = today.day
            month_number = today.month
            year_number = today.year

        records = []
        for idx, row in df.iterrows():
            merch = str(row.get('merch', '')).strip()
            sup_status = row.get('supervisorStatus')
            merch_status = row.get('merchStatus')
            note = row.get('supervisorNote') or row.get('note') or ""
            if pd.isna(note):
                note = ""
                
            chosen_status = sup_status if pd.notna(sup_status) and str(sup_status).strip() else merch_status
            
            matched_emps = self.match_employee(merch)
            
            # Map preview value
            sample_matricule = matched_emps[0]['matricule'] if matched_emps else "Part Time"
            mapped_val = map_status(chosen_status, sample_matricule)
            
            records.append({
                'index': idx + 1,
                'merch': merch,
                'supervisor_status': str(sup_status) if pd.notna(sup_status) else "",
                'merch_status': str(merch_status) if pd.notna(merch_status) else "",
                'effective_status': str(chosen_status),
                'mapped_value': mapped_val,
                'note': str(note),
                'matches_count': len(matched_emps),
                'matched_rows': [m['row'] for m in matched_emps],
                'matched_companies': [m['soc'] for m in matched_emps],
                'match_status': "MATCHED" if matched_emps else "NOT_FOUND"
            })
            
        stats = {
            'total': len(records),
            'matched': sum(1 for r in records if r['match_status'] == "MATCHED"),
            'unmatched': sum(1 for r in records if r['match_status'] == "NOT_FOUND"),
            'presents': sum(1 for r in records if r['mapped_value'] in [0.5, 1.0]),
            'day_offs': sum(1 for r in records if r['mapped_value'] == "D-O"),
            'recups': sum(1 for r in records if r['mapped_value'] == "R"),
            'resigned': sum(1 for r in records if r['mapped_value'] == "Démission"),
            'others': sum(1 for r in records if r['mapped_value'] not in [0.5, 1.0, "D-O", "R", "Démission"])
        }
        
        return {
            'date': detected_date_str,
            'day': day_number,
            'month': month_number,
            'year': year_number,
            'day_col': self.day_columns.get(day_number),
            'stats': stats,
            'records': records
        }

    def process_attendance(self, daily_file_path, 
                           target_day=None,
                           carry_forward_resigned=True, 
                           extend_resigned_to_rest_of_month=True,
                           fill_unmarked_as_absent=False,
                           custom_status_map=None):
        """
        Applies daily attendance onto the base workbook.
        Returns a detailed summary of changes.
        """
        preview = self.preview_daily_file(daily_file_path)
        day = target_day if target_day is not None else preview['day']
        
        if day not in self.day_columns:
            raise ValueError(f"Day {day} does not have a corresponding column in header row {self.header_row_idx} of '{self.main_sheet_name}'.")
            
        target_col = self.day_columns[day]
        max_day = max(self.day_columns.keys())
        
        updated_rows = set()
        change_logs = []
        
        # 1. Apply from daily records
        for rec in preview['records']:
            if rec['match_status'] == "MATCHED":
                status_to_map = rec['effective_status']
                if custom_status_map and status_to_map in custom_status_map:
                    val = custom_status_map[status_to_map]
                else:
                    val = rec['mapped_value']
                    
                for r in rec['matched_rows']:
                    cell = self.ws.cell(r, target_col)
                    old_val = cell.value
                    cell.value = val
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    updated_rows.add(r)
                    change_logs.append({
                        'row': r,
                        'name': rec['merch'],
                        'day': day,
                        'col': target_col,
                        'old_val': old_val,
                        'new_val': val,
                        'reason': 'Daily file update'
                    })
                    
        # 2. Carry forward Resigned (Démission) from previous day if empty
        if carry_forward_resigned and day > 1:
            prev_day = day - 1
            if prev_day in self.day_columns:
                prev_col = self.day_columns[prev_day]
                for emp in self.employees:
                    r = emp['row']
                    current_val = self.ws.cell(r, target_col).value
                    if current_val is None:
                        prev_val = str(self.ws.cell(r, prev_col).value or "").strip().lower()
                        if "mission" in prev_val:
                            self.ws.cell(r, target_col).value = "Démission"
                            self.ws.cell(r, target_col).alignment = Alignment(horizontal="center", vertical="center")
                            updated_rows.add(r)
                            change_logs.append({
                                'row': r,
                                'name': emp['full_name_1'],
                                'day': day,
                                'col': target_col,
                                'old_val': None,
                                'new_val': 'Démission',
                                'reason': 'Carried forward from previous day'
                            })

        # 3. Extend Démission to the rest of the month (Days day+1 .. max_day)
        if extend_resigned_to_rest_of_month:
            for emp in self.employees:
                r = emp['row']
                val_now = str(self.ws.cell(r, target_col).value or "").strip().lower()
                if "mission" in val_now:
                    for d_future in range(day + 1, max_day + 1):
                        if d_future in self.day_columns:
                            future_col = self.day_columns[d_future]
                            old_future = self.ws.cell(r, future_col).value
                            self.ws.cell(r, future_col).value = "Démission"
                            self.ws.cell(r, future_col).alignment = Alignment(horizontal="center", vertical="center")
                            change_logs.append({
                                'row': r,
                                'name': emp['full_name_1'],
                                'day': d_future,
                                'col': future_col,
                                'old_val': old_future,
                                'new_val': 'Démission',
                                'reason': 'Extended resignation to rest of month'
                            })

        # 4. Fill unmarked active rows as absent (if enabled)
        if fill_unmarked_as_absent:
            for emp in self.employees:
                r = emp['row']
                if r not in updated_rows:
                    if self.ws.cell(r, target_col).value is None:
                        self.ws.cell(r, target_col).value = 0
                        self.ws.cell(r, target_col).alignment = Alignment(horizontal="center", vertical="center")
                        change_logs.append({
                            'row': r,
                            'name': emp['full_name_1'],
                            'day': day,
                            'col': target_col,
                            'old_val': None,
                            'new_val': 0,
                            'reason': 'Unmarked row set to Absent'
                        })

        return {
            'day': day,
            'target_col': target_col,
            'changes_count': len(change_logs),
            'unique_rows_updated': len(updated_rows),
            'preview': preview,
            'logs': change_logs
        }

    def save(self, output_path=None):
        """Saves workbook to output_path or generates standard version."""
        if not output_path:
            dir_name = os.path.dirname(self.base_file_path)
            base_name = os.path.splitext(os.path.basename(self.base_file_path))[0]
            output_path = os.path.join(dir_name, f"{base_name} (Updated).xlsx")
            
        self.wb.save(output_path)
        return output_path
