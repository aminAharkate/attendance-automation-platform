"""
Attendance Master Web Application
Flask backend providing real-time file detection, preview, status mapping, and Excel updates.
"""

import os
import glob
import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from attendance_core import AttendanceProcessor, map_status, normalize_str

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Project and Downloads paths for quick auto-detection
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.expanduser(r"~\Downloads")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect-local-files', methods=['GET'])
def detect_local_files():
    """Scans project folder and Downloads for Base RH and Daily attendance files."""
    search_dirs = [PROJECT_DIR, DOWNLOADS_DIR]
    base_files = []
    daily_files = []
    
    seen_base = set()
    seen_daily = set()
    
    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
            
        # Base files
        for p in glob.glob(os.path.join(s_dir, "*Pointage*.xlsx")) + glob.glob(os.path.join(s_dir, "*Base RH*.xlsx")):
            fname = os.path.basename(p)
            if fname not in seen_base and not fname.startswith("~$"):
                seen_base.add(fname)
                mtime = os.path.getmtime(p)
                base_files.append({
                    'name': fname,
                    'path': p,
                    'size': f"{os.path.getsize(p) / 1024:.1f} KB",
                    'modified': datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    'mtime': mtime
                })
                
        # Daily files
        for p in glob.glob(os.path.join(s_dir, "*attendance*.xlsx")) + glob.glob(os.path.join(s_dir, "*atacadao*.xlsx")):
            fname = os.path.basename(p)
            if fname not in seen_daily and not fname.startswith("~$"):
                seen_daily.add(fname)
                mtime = os.path.getmtime(p)
                daily_files.append({
                    'name': fname,
                    'path': p,
                    'size': f"{os.path.getsize(p) / 1024:.1f} KB",
                    'modified': datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    'mtime': mtime
                })
                
    # Sort newest first
    base_files.sort(key=lambda x: x['mtime'], reverse=True)
    daily_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    return jsonify({
        'base_files': base_files,
        'daily_files': daily_files,
        'project_dir': PROJECT_DIR
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Uploads a base or daily file."""
    file_type = request.form.get('type', 'daily')
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    
    return jsonify({
        'success': True,
        'filename': filename,
        'path': save_path,
        'type': file_type,
        'size': f"{os.path.getsize(save_path) / 1024:.1f} KB"
    })

@app.route('/api/preview', methods=['POST'])
def preview_data():
    """Generates preview matching analysis between Base file and Daily file(s)."""
    data = request.json or {}
    base_path = data.get('base_path')
    daily_paths = data.get('daily_paths', [])
    
    if isinstance(daily_paths, str):
        daily_paths = [daily_paths]
        
    if not base_path or not os.path.exists(base_path):
        return jsonify({'error': f'Base file not found: {base_path}'}), 400
        
    if not daily_paths:
        return jsonify({'error': 'No daily files provided'}), 400
        
    try:
        processor = AttendanceProcessor(base_path)
        daily_previews = []
        for dp in daily_paths:
            if os.path.exists(dp):
                prev = processor.preview_daily_file(dp)
                prev['file_name'] = os.path.basename(dp)
                prev['file_path'] = dp
                daily_previews.append(prev)
                
        return jsonify({
            'success': True,
            'base_info': {
                'file_name': os.path.basename(base_path),
                'main_sheet': processor.main_sheet_name,
                'header_row': processor.header_row_idx,
                'total_employees': len(processor.employees),
                'available_days': sorted(list(processor.day_columns.keys()))
            },
            'daily_previews': daily_previews
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_data():
    """Processes daily attendance files and writes into the Base RH workbook."""
    data = request.json or {}
    base_path = data.get('base_path')
    daily_paths = data.get('daily_paths', [])
    if isinstance(daily_paths, str):
        daily_paths = [daily_paths]
        
    carry_forward_resigned = data.get('carry_forward_resigned', True)
    extend_resigned_to_rest_of_month = data.get('extend_resigned_to_rest_of_month', True)
    fill_unmarked_as_absent = data.get('fill_unmarked_as_absent', False)
    save_in_project_folder = data.get('save_in_project_folder', True)
    
    if not base_path or not os.path.exists(base_path):
        return jsonify({'error': f'Base file not found: {base_path}'}), 400
        
    try:
        processor = AttendanceProcessor(base_path)
        all_results = []
        
        for dp in daily_paths:
            if os.path.exists(dp):
                res = processor.process_attendance(
                    daily_file_path=dp,
                    carry_forward_resigned=carry_forward_resigned,
                    extend_resigned_to_rest_of_month=extend_resigned_to_rest_of_month,
                    fill_unmarked_as_absent=fill_unmarked_as_absent
                )
                res['file_name'] = os.path.basename(dp)
                all_results.append(res)
                
        # Generate output filename with clean timestamp/day info
        base_orig_name = os.path.splitext(os.path.basename(base_path))[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_orig_name}_Updated_{timestamp}.xlsx"
        
        if save_in_project_folder:
            output_path = os.path.join(PROJECT_DIR, output_filename)
        else:
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
        processor.save(output_path)
        
        # Summary
        total_changes = sum(r['changes_count'] for r in all_results)
        days_updated = [r['day'] for r in all_results]
        
        return jsonify({
            'success': True,
            'output_file': output_filename,
            'output_path': output_path,
            'total_changes': total_changes,
            'days_updated': days_updated,
            'results': all_results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Direct download endpoint for processed Excel files."""
    # Check in PROJECT_DIR first, then OUTPUT_FOLDER
    proj_path = os.path.join(PROJECT_DIR, filename)
    out_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    target = proj_path if os.path.exists(proj_path) else out_path
    
    if not os.path.exists(target):
        return jsonify({'error': 'File not found'}), 404
        
    return send_file(target, as_attachment=True, download_name=filename)

if __name__ == '__main__':
    print("=" * 60)
    print("  ATTENDANCE AUTOMATION SYSTEM READY")
    print("  Server running on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)
