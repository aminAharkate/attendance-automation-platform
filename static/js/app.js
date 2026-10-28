/**
 * ATTENDANCE MASTER - CLIENT-SIDE APPLICATION LOGIC
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        baseFiles: [],
        dailyFiles: [],
        selectedBasePath: null,
        selectedDailyPaths: [],
        currentPreviewData: null,
        filterStatus: 'all',
        searchQuery: ''
    };

    // DOM Elements
    const elements = {
        baseFileSelect: document.getElementById('baseFileSelect'),
        dailyFileSelect: document.getElementById('dailyFileSelect'),
        baseFileNameDisplay: document.getElementById('baseFileNameDisplay'),
        baseFileMetaDisplay: document.getElementById('baseFileMetaDisplay'),
        dailyFileNameDisplay: document.getElementById('dailyFileNameDisplay'),
        dailyFileMetaDisplay: document.getElementById('dailyFileMetaDisplay'),
        uploadBaseInput: document.getElementById('uploadBaseInput'),
        uploadDailyInput: document.getElementById('uploadDailyInput'),
        btnRefreshFiles: document.getElementById('btnRefreshFiles'),
        btnAnalyze: document.getElementById('btnAnalyze'),
        previewSection: document.getElementById('previewSection'),
        successSection: document.getElementById('successSection'),
        detectionBanner: document.getElementById('detectionBanner'),
        bannerDateTitle: document.getElementById('bannerDateTitle'),
        bannerDetails: document.getElementById('bannerDetails'),
        kpiTotal: document.getElementById('kpiTotal'),
        kpiMatched: document.getElementById('kpiMatched'),
        kpiPresents: document.getElementById('kpiPresents'),
        kpiDayOffs: document.getElementById('kpiDayOffs'),
        kpiRecups: document.getElementById('kpiRecups'),
        kpiResigned: document.getElementById('kpiResigned'),
        chkExtendResigned: document.getElementById('chkExtendResigned'),
        chkCarryForward: document.getElementById('chkCarryForward'),
        chkUnmarkedAbsent: document.getElementById('chkUnmarkedAbsent'),
        tableSearchInput: document.getElementById('tableSearchInput'),
        statusFilterPills: document.getElementById('statusFilterPills'),
        previewTableBody: document.getElementById('previewTableBody'),
        btnExecuteProcess: document.getElementById('btnExecuteProcess'),
        btnDownloadOutput: document.getElementById('btnDownloadOutput'),
        btnProcessAnother: document.getElementById('btnProcessAnother'),
        outputFileNameDisplay: document.getElementById('outputFileNameDisplay'),
        successSummaryText: document.getElementById('successSummaryText'),
        toastContainer: document.getElementById('toastContainer'),
        pillCountAll: document.getElementById('pillCountAll'),
        pillCountPresent: document.getElementById('pillCountPresent'),
        pillCountDayOff: document.getElementById('pillCountDayOff'),
        pillCountRecup: document.getElementById('pillCountRecup'),
        pillCountResigned: document.getElementById('pillCountResigned')
    };

    // --- Toast Notifications ---
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span>${message}</span>
        `;
        elements.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- Scan & Detect Files ---
    async function loadDetectedFiles() {
        try {
            const res = await fetch('/api/detect-local-files');
            const data = await res.json();
            
            state.baseFiles = data.base_files || [];
            state.dailyFiles = data.daily_files || [];

            // Populate Base Select
            elements.baseFileSelect.innerHTML = '<option value="">Select detected Base RH file...</option>';
            state.baseFiles.forEach((f, idx) => {
                const opt = document.createElement('option');
                opt.value = f.path;
                opt.textContent = `${f.name} (${f.size})`;
                elements.baseFileSelect.appendChild(opt);
            });

            // Populate Daily Select
            elements.dailyFileSelect.innerHTML = '<option value="">Select detected daily attendance file...</option>';
            state.dailyFiles.forEach((f, idx) => {
                const opt = document.createElement('option');
                opt.value = f.path;
                opt.textContent = `${f.name} (${f.size})`;
                elements.dailyFileSelect.appendChild(opt);
            });

            // Auto-select latest files if available
            if (state.baseFiles.length > 0) {
                const latestBase = state.baseFiles[0];
                elements.baseFileSelect.value = latestBase.path;
                selectBaseFile(latestBase.path, latestBase.name, `${latestBase.size} • Modified: ${latestBase.modified}`);
            }

            if (state.dailyFiles.length > 0) {
                const latestDaily = state.dailyFiles[0];
                elements.dailyFileSelect.value = latestDaily.path;
                selectDailyFile(latestDaily.path, latestDaily.name, `${latestDaily.size} • Modified: ${latestDaily.modified}`);
            }

            showToast(`Found ${state.baseFiles.length} Base RH and ${state.dailyFiles.length} Daily attendance files`, 'success');
        } catch (err) {
            console.error('Error scanning files:', err);
            showToast('Failed to scan local directories', 'error');
        }
    }

    function selectBaseFile(path, name, meta) {
        state.selectedBasePath = path;
        elements.baseFileNameDisplay.textContent = name;
        elements.baseFileMetaDisplay.textContent = meta;
    }

    function selectDailyFile(path, name, meta) {
        state.selectedDailyPaths = [path];
        elements.dailyFileNameDisplay.textContent = name;
        elements.dailyFileMetaDisplay.textContent = meta;
    }

    // --- Upload Handlers ---
    elements.uploadBaseInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', 'base');

        try {
            showToast(`Uploading ${file.name}...`, 'info');
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) {
                selectBaseFile(data.path, data.filename, `${data.size} • Uploaded`);
                showToast('Base RH file loaded', 'success');
            } else {
                showToast(data.error || 'Upload failed', 'error');
            }
        } catch (err) {
            showToast('Error uploading file', 'error');
        }
    });

    elements.uploadDailyInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        try {
            const paths = [];
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('type', 'daily');
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.success) {
                    paths.push(data.path);
                }
            }
            if (paths.length > 0) {
                state.selectedDailyPaths = paths;
                const firstName = files[0].name;
                const extra = paths.length > 1 ? ` (+${paths.length - 1} more files)` : '';
                selectDailyFile(paths[0], `${firstName}${extra}`, `${paths.length} file(s) ready`);
                showToast(`Loaded ${paths.length} daily file(s)`, 'success');
            }
        } catch (err) {
            showToast('Error uploading daily files', 'error');
        }
    });

    elements.baseFileSelect.addEventListener('change', (e) => {
        const path = e.target.value;
        const file = state.baseFiles.find(f => f.path === path);
        if (file) {
            selectBaseFile(file.path, file.name, `${file.size} • Modified: ${file.modified}`);
        }
    });

    elements.dailyFileSelect.addEventListener('change', (e) => {
        const path = e.target.value;
        const file = state.dailyFiles.find(f => f.path === path);
        if (file) {
            selectDailyFile(file.path, file.name, `${file.size} • Modified: ${file.modified}`);
        }
    });

    elements.btnRefreshFiles.addEventListener('click', loadDetectedFiles);

    // --- Analyze & Preview ---
    elements.btnAnalyze.addEventListener('click', async () => {
        if (!state.selectedBasePath) {
            showToast('Please select or upload a Base RH file first.', 'error');
            return;
        }
        if (!state.selectedDailyPaths || state.selectedDailyPaths.length === 0) {
            showToast('Please select or upload daily attendance file(s).', 'error');
            return;
        }

        elements.btnAnalyze.disabled = true;
        elements.btnAnalyze.innerHTML = `
            <svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
            Analyzing Workbooks...
        `;

        try {
            const res = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_path: state.selectedBasePath,
                    daily_paths: state.selectedDailyPaths
                })
            });

            const data = await res.json();
            if (!data.success) {
                showToast(data.error || 'Analysis failed', 'error');
                return;
            }

            state.currentPreviewData = data;
            renderPreview(data);

            elements.previewSection.classList.remove('hidden');
            elements.successSection.classList.add('hidden');
            elements.previewSection.scrollIntoView({ behavior: 'smooth' });
            showToast('Analysis complete: All merchandisers matched!', 'success');
        } catch (err) {
            console.error('Analysis error:', err);
            showToast('Failed to analyze files', 'error');
        } finally {
            elements.btnAnalyze.disabled = false;
            elements.btnAnalyze.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                Analyze &amp; Preview Matches
            `;
        }
    });

    // --- Render Preview Function ---
    function renderPreview(data) {
        const baseInfo = data.base_info;
        const dailyPrev = data.daily_previews[0]; // primary preview
        const stats = dailyPrev.stats;

        // Banner
        elements.bannerDateTitle.textContent = `Detected Date: ${dailyPrev.date} (Day ${dailyPrev.day})`;
        elements.bannerDetails.innerHTML = `Targeting Day Column <strong>${dailyPrev.day_col}</strong> in Sheet: <code>${baseInfo.main_sheet}</code> (${baseInfo.total_employees} staff members tracked)`;

        // KPI
        elements.kpiTotal.textContent = stats.total;
        elements.kpiMatched.textContent = `${Math.round((stats.matched / stats.total) * 100)}% Matched (${stats.matched}/${stats.total})`;
        elements.kpiPresents.textContent = stats.presents;
        elements.kpiDayOffs.textContent = stats.day_offs;
        elements.kpiRecups.textContent = stats.recups;
        elements.kpiResigned.textContent = stats.resigned;

        // Pill counts
        elements.pillCountAll.textContent = stats.total;
        elements.pillCountPresent.textContent = stats.presents;
        elements.pillCountDayOff.textContent = stats.day_offs;
        elements.pillCountRecup.textContent = stats.recups;
        elements.pillCountResigned.textContent = stats.resigned;

        renderTableRows();
    }

    // --- Render Table Rows with Filtering ---
    function renderTableRows() {
        if (!state.currentPreviewData) return;
        const records = state.currentPreviewData.daily_previews[0].records;
        const dayNumber = state.currentPreviewData.daily_previews[0].day;

        const filtered = records.filter(r => {
            // Status filter
            if (state.filterStatus === 'present' && ![0.5, 1.0].includes(r.mapped_value)) return false;
            if (state.filterStatus === 'dayoff' && r.mapped_value !== 'D-O') return false;
            if (state.filterStatus === 'recup' && r.mapped_value !== 'R') return false;
            if (state.filterStatus === 'resigned' && r.mapped_value !== 'Démission') return false;

            // Search query
            if (state.searchQuery) {
                const q = state.searchQuery.toLowerCase();
                const merch = r.merch.toLowerCase();
                return merch.includes(q);
            }
            return true;
        });

        elements.previewTableBody.innerHTML = '';
        if (filtered.length === 0) {
            elements.previewTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 32px; color: var(--text-muted);">
                        No merchandiser records match your filter criteria.
                    </td>
                </tr>
            `;
            return;
        }

        filtered.forEach(r => {
            const tr = document.createElement('tr');

            // Badge for mapped value
            let badgeClass = 'badge-matched';
            let badgeText = r.mapped_value;
            if ([0.5, 1.0].includes(r.mapped_value)) {
                badgeClass = 'badge-present';
                badgeText = `${r.mapped_value} (Present)`;
            } else if (r.mapped_value === 'D-O') {
                badgeClass = 'badge-dayoff';
            } else if (r.mapped_value === 'R') {
                badgeClass = 'badge-recup';
                badgeText = 'R (Récup)';
            } else if (r.mapped_value === 'Démission') {
                badgeClass = 'badge-resigned';
            }

            const compBadges = r.matched_companies.map(c => `<span class="badge" style="background: rgba(255,255,255,0.06); margin-right: 4px;">${c}</span>`).join('');

            tr.innerHTML = `
                <td style="font-family: var(--font-mono); color: var(--text-muted);">${r.index}</td>
                <td><strong>${r.merch}</strong></td>
                <td style="color: var(--text-secondary);">${r.effective_status}</td>
                <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                <td style="font-family: var(--font-mono); font-weight: 600;">Day ${dayNumber}</td>
                <td style="font-family: var(--font-mono);">${r.matched_rows.length} row(s) [R${r.matched_rows.join(', R')}]</td>
                <td>${compBadges || '—'}</td>
                <td><span class="badge ${r.match_status === 'MATCHED' ? 'badge-matched' : 'badge-unmatched'}">${r.match_status}</span></td>
            `;
            elements.previewTableBody.appendChild(tr);
        });
    }

    // --- Search & Filter Events ---
    elements.tableSearchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim();
        renderTableRows();
    });

    elements.statusFilterPills.addEventListener('click', (e) => {
        const pill = e.target.closest('.pill');
        if (!pill) return;

        elements.statusFilterPills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        state.filterStatus = pill.getAttribute('data-filter');
        renderTableRows();
    });

    // --- Execute Process & Save ---
    elements.btnExecuteProcess.addEventListener('click', async () => {
        if (!state.selectedBasePath || !state.selectedDailyPaths) return;

        elements.btnExecuteProcess.disabled = true;
        elements.btnExecuteProcess.innerHTML = `
            <svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
            Updating Workbook &amp; Propagating...
        `;

        try {
            const res = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_path: state.selectedBasePath,
                    daily_paths: state.selectedDailyPaths,
                    carry_forward_resigned: elements.chkCarryForward.checked,
                    extend_resigned_to_rest_of_month: elements.chkExtendResigned.checked,
                    fill_unmarked_as_absent: elements.chkUnmarkedAbsent.checked,
                    save_in_project_folder: true
                })
            });

            const data = await res.json();
            if (!data.success) {
                showToast(data.error || 'Failed to update Excel workbook', 'error');
                return;
            }

            // Success View
            elements.outputFileNameDisplay.textContent = data.output_file;
            elements.successSummaryText.textContent = `Successfully updated ${data.total_changes} cells across day(s): ${data.days_updated.join(', ')}. Resignations extended through end of month.`;
            elements.btnDownloadOutput.href = `/api/download/${encodeURIComponent(data.output_file)}`;

            elements.previewSection.classList.add('hidden');
            elements.successSection.classList.remove('hidden');
            elements.successSection.scrollIntoView({ behavior: 'smooth' });

            showToast('Workbook saved successfully!', 'success');
        } catch (err) {
            console.error('Process error:', err);
            showToast('Error during Excel update', 'error');
        } finally {
            elements.btnExecuteProcess.disabled = false;
            elements.btnExecuteProcess.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                    <polyline points="17 21 17 13 7 13 7 21"></polyline>
                    <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                Apply &amp; Save Updated Workbook
            `;
        }
    });

    elements.btnProcessAnother.addEventListener('click', () => {
        elements.successSection.classList.add('hidden');
        elements.previewSection.classList.remove('hidden');
        loadDetectedFiles();
    });

    // Initial Load
    loadDetectedFiles();
});
