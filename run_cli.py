"""
Attendance Master - Command Line Tool (CLI)
Automates daily attendance integration directly from the terminal or automated tasks.
"""

import os
import sys
import argparse
import glob
from attendance_core import AttendanceProcessor

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.expanduser(r"~\Downloads")

def find_latest_file(patterns, search_dirs):
    candidates = []
    for s_dir in search_dirs:
        for pat in patterns:
            for p in glob.glob(os.path.join(s_dir, pat)):
                if not os.path.basename(p).startswith("~$"):
                    candidates.append((os.path.getmtime(p), p))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]

def main():
    parser = argparse.ArgumentParser(description="Automate daily attendance into monthly Base RH Excel workbook.")
    parser.add_argument("--base", help="Path to Base RH monthly workbook (e.g. Base RH_Pointage Quotidien...xlsx)")
    parser.add_argument("--daily", nargs="+", help="Path to one or more daily attendance export files (e.g. atacadao_attendance...xlsx)")
    parser.add_argument("--day", type=int, help="Optional day number override (1-31)")
    parser.add_argument("--no-extend-resigned", action="store_true", help="Do not extend resignation to rest of the month")
    parser.add_argument("--no-carry-forward", action="store_true", help="Do not carry forward yesterday's resignation")
    parser.add_argument("--absent-unmarked", action="store_true", help="Mark unmarked active employees as absent (0)")
    parser.add_argument("--output", help="Optional custom output path for updated Excel file")
    
    args = parser.parse_args()
    
    # Auto-detect if not provided
    search_dirs = [PROJECT_DIR, DOWNLOADS_DIR]
    base_file = args.base or find_latest_file(["*Base RH*.xlsx", "*Pointage Quotidien*.xlsx"], search_dirs)
    daily_files = args.daily
    if not daily_files:
        latest_daily = find_latest_file(["*attendance*.xlsx", "*atacadao*.xlsx"], search_dirs)
        if latest_daily:
            daily_files = [latest_daily]
            
    if not base_file:
        print("[ERROR] Could not find any Base RH monthly Excel file.")
        sys.exit(1)
        
    if not daily_files:
        print("[ERROR] Could not find any Daily attendance Excel file.")
        sys.exit(1)
        
    print("=" * 65)
    print("  ATTENDANCE MASTER - CLI PROCESSOR")
    print("=" * 65)
    print(f"Base RH File   : {os.path.basename(base_file)}")
    print(f"Daily File(s)  : {[os.path.basename(f) for f in daily_files]}")
    print("-" * 65)
    
    processor = AttendanceProcessor(base_file)
    print(f"[OK] Workbook loaded. Active Sheet: '{processor.main_sheet_name}', Total staff: {len(processor.employees)}")
    
    total_changes = 0
    for d_path in daily_files:
        print(f"\nProcessing: {os.path.basename(d_path)} ...")
        res = processor.process_attendance(
            daily_file_path=d_path,
            target_day=args.day,
            carry_forward_resigned=not args.no_carry_forward,
            extend_resigned_to_rest_of_month=not args.no_extend_resigned,
            fill_unmarked_as_absent=args.absent_unmarked
        )
        prev = res['preview']
        stats = prev['stats']
        print(f"  Detected Date: {prev['date']} (Day {res['day']}) -> Target Column {res['target_col']}")
        print(f"  Matched Staff: {stats['matched']}/{stats['total']} ({stats['presents']} Presents, {stats['day_offs']} Day-Off, {stats['recups']} Récup, {stats['resigned']} Démission)")
        print(f"  Cells Updated: {res['changes_count']} across {res['unique_rows_updated']} staff rows.")
        total_changes += res['changes_count']
        
    out_path = processor.save(args.output)
    print("\n" + "=" * 65)
    print(f"[SUCCESS] Total {total_changes} cell changes applied.")
    print(f"[OUTPUT] Saved to: {out_path}")
    print("=" * 65)

if __name__ == "__main__":
    main()
