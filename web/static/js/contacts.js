// Contacts Directory — client-side logic (with brands-style advanced filter drawer)

(function () {
    'use strict';

    let currentPage = 1;
    let currentPerPage = 50;
    let currentSearch = '';
    let filterData = {};

    let activeFilters = {
        companies: [],
        titles: [],
        sources: [],
        emailStatus: [],
        phoneStatus: []
    };

    // Section type → activeFilters key
    const sectionMap = {
        company: 'companies',
        title: 'titles',
        source: 'sources'
    };

    // ── Initialization ────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', async function () {
        loadFiltersFromURL();
        setupEventListeners();
        await loadFilterData();
        populateFilterOptions();

        if (hasActiveFilters() || currentSearch) {
            currentPage = 1;
            await loadContacts();
            updateFilterCount();
            updateURL();
        } else {
            await loadContacts();
        }

        loadStats();
    });

    // ── Stats ─────────────────────────────────────────────────────────────

    async function loadStats() {
        try {
            const res = await fetch('/contacts_filter_options');
            const data = await res.json();
            if (data.stats) {
                const el = document.getElementById('total-contacts');
                if (el) el.textContent = data.stats.total.toLocaleString();
                const sc = document.getElementById('stat-companies');
                if (sc) sc.textContent = data.stats.unique_companies.toLocaleString();
            }
        } catch (err) {
            console.error('Error loading stats:', err);
        }
    }

    // ── Filter Data (global counts) ───────────────────────────────────────

    async function loadFilterData() {
        try {
            const res = await fetch('/contacts_filter_data');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            filterData = await res.json();
        } catch (err) {
            console.error('Failed to load filter data:', err);
            filterData = { companies: {}, sources: {}, titles: {}, emailStatus: {}, phoneStatus: {} };
        }
    }

    function populateFilterOptions() {
        populateFilterSection('company', filterData.companies);
        populateFilterSection('title', filterData.titles);
        populateFilterSection('source', filterData.sources);
        updateEmailStatusCounts();
        updatePhoneStatusCounts();
        restoreSelectedFilters();
        updateActiveFiltersDisplay();
    }

    function populateFilterSection(sectionType, data) {
        const optionsContainer = document.getElementById(`${sectionType}-options`);
        const quickTogglesContainer = document.getElementById(`${sectionType}-quick-toggles`);
        const countElement = document.getElementById(`${sectionType}-count`);

        if (!data) return;
        const sortedEntries = Object.entries(data).sort((a, b) => b[1] - a[1]);

        if (countElement) countElement.textContent = sortedEntries.length;

        // Quick toggles (top 10)
        if (quickTogglesContainer) {
            const top10 = sortedEntries.slice(0, 10);
            quickTogglesContainer.innerHTML = top10.map(([name, count]) => `
                <div class="quick-toggle-item" onclick="toggleQuickFilter('${sectionType}', '${escAttr(name)}', event)">
                    <input type="checkbox" class="quick-toggle-checkbox"
                           value="${escAttr(name)}"
                           data-filter-type="${sectionType}"
                           onchange="handleQuickToggle('${sectionType}', this)"
                           onclick="event.stopPropagation()">
                    <span class="quick-toggle-label" title="${escAttr(name)}">${esc(name)}</span>
                    <span class="quick-toggle-count">${count}</span>
                </div>
            `).join('');
        }

        // Full list
        if (optionsContainer) {
            optionsContainer.innerHTML = sortedEntries.map(([name, count]) => `
                <label class="filter-option" data-value="${escAttr(name)}">
                    <input type="checkbox" value="${escAttr(name)}" onchange="updateFilterSelection('${sectionType}', this)">
                    <span>${esc(name)}</span>
                    <span class="option-count">${count}</span>
                </label>
            `).join('');
        }
    }

    function updateEmailStatusCounts() {
        const counts = filterData.emailStatus || {};
        const hasEl = document.getElementById('has-email-count');
        if (hasEl) hasEl.textContent = counts.has_email || 0;
        const noEl = document.getElementById('no-email-count');
        if (noEl) noEl.textContent = counts.no_email || 0;
        const countEl = document.getElementById('email-count');
        if (countEl) countEl.textContent = (counts.has_email || 0) + (counts.no_email || 0);
    }

    function updatePhoneStatusCounts() {
        const counts = filterData.phoneStatus || {};
        const hasEl = document.getElementById('has-phone-count');
        if (hasEl) hasEl.textContent = counts.has_phone || 0;
        const noEl = document.getElementById('no-phone-count');
        if (noEl) noEl.textContent = counts.no_phone || 0;
        const countEl = document.getElementById('phone-count');
        if (countEl) countEl.textContent = (counts.has_phone || 0) + (counts.no_phone || 0);
    }

    function restoreSelectedFilters() {
        Object.entries(sectionMap).forEach(([sectionType, filterKey]) => {
            (activeFilters[filterKey] || []).forEach(value => {
                const cb = document.querySelector(`#${sectionType}-options input[value="${cssEscVal(value)}"]`);
                if (cb) cb.checked = true;
                const qt = document.querySelector(`#${sectionType}-quick-toggles input[value="${cssEscVal(value)}"]`);
                if (qt) {
                    qt.checked = true;
                    const item = qt.closest('.quick-toggle-item');
                    if (item) item.classList.add('active');
                }
            });
        });
        activeFilters.emailStatus.forEach(v => {
            const cb = document.querySelector(`#email-filters input[value="${v}"]`);
            if (cb) cb.checked = true;
        });
        activeFilters.phoneStatus.forEach(v => {
            const cb = document.querySelector(`#phone-filters input[value="${v}"]`);
            if (cb) cb.checked = true;
        });
    }

    // ── Contacts Table ────────────────────────────────────────────────────

    function getFilterParams() {
        const params = new URLSearchParams();
        if (currentSearch) params.set('search', currentSearch);
        Object.entries(activeFilters).forEach(([key, vals]) => {
            vals.forEach(v => params.append(key, v));
        });
        params.set('page', currentPage);
        params.set('per_page', currentPerPage);
        return params;
    }

    async function loadContacts() {
        const params = getFilterParams();
        const tbody = document.getElementById('contacts-tbody');

        try {
            const res = await fetch('/get_contacts?' + params.toString());
            const data = await res.json();

            // Update filtered count
            const filteredEl = document.getElementById('filtered-contacts');
            if (filteredEl) filteredEl.textContent = (data.total || 0).toLocaleString();

            if (!data.items || data.items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No contacts found</td></tr>';
                document.getElementById('pagination-info').textContent = '';
                document.getElementById('pagination-controls').innerHTML = '';
                return;
            }

            tbody.innerHTML = data.items.map(c => `
                <tr>
                    <td class="cell-company">${esc(c.company_name)}</td>
                    <td>${esc(c.contact_name || '')}</td>
                    <td>${esc(c.title || '')}</td>
                    <td>${c.email ? '<a href="mailto:' + escAttr(c.email) + '">' + esc(c.email) + '</a>' : '<span class="text-muted">\u2014</span>'}</td>
                    <td>${esc(c.phone || '') || '<span class="text-muted">\u2014</span>'}</td>
                    <td><span class="source-badge">${esc(c.source || '')}</span></td>
                </tr>
            `).join('');

            renderPagination(data);
        } catch (err) {
            console.error('Error loading contacts:', err);
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Error loading contacts</td></tr>';
        }
    }

    function renderPagination(data) {
        const info = document.getElementById('pagination-info');
        const controls = document.getElementById('pagination-controls');
        const start = (data.page - 1) * data.per_page + 1;
        const end = Math.min(data.page * data.per_page, data.total);
        info.textContent = `Showing ${start}\u2013${end} of ${data.total.toLocaleString()} contacts`;

        let html = '';
        if (data.page > 1) {
            html += `<button class="pagination-btn" onclick="goToPage(${data.page - 1})">\u2190 Previous</button>`;
        }
        const startPage = Math.max(1, data.page - 2);
        const endPage = Math.min(data.total_pages, data.page + 2);
        if (startPage > 1) {
            html += `<button class="pagination-btn" onclick="goToPage(1)">1</button>`;
            if (startPage > 2) html += '<span class="pagination-ellipsis">...</span>';
        }
        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="pagination-btn ${i === data.page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
        }
        if (endPage < data.total_pages) {
            if (endPage < data.total_pages - 1) html += '<span class="pagination-ellipsis">...</span>';
            html += `<button class="pagination-btn" onclick="goToPage(${data.total_pages})">${data.total_pages}</button>`;
        }
        if (data.page < data.total_pages) {
            html += `<button class="pagination-btn" onclick="goToPage(${data.page + 1})">Next \u2192</button>`;
        }
        controls.innerHTML = html;
    }

    window.goToPage = async function (page) {
        currentPage = page;
        await loadContacts();
        updateURL();
    };

    // ── Event Listeners ───────────────────────────────────────────────────

    function setupEventListeners() {
        // Filter drawer toggle
        const toggleBtn = document.getElementById('toggle-filters');
        if (toggleBtn) toggleBtn.addEventListener('click', toggleFilterSidebar);

        const toolbarBtn = document.getElementById('filter-toolbar-btn');
        if (toolbarBtn) toolbarBtn.addEventListener('click', toggleFilterSidebar);

        const backdrop = document.getElementById('filter-backdrop');
        if (backdrop) backdrop.addEventListener('click', closeFilterSidebar);

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                const sidebar = document.getElementById('filter-sidebar');
                if (sidebar && !sidebar.classList.contains('collapsed')) closeFilterSidebar();
            }
        });

        const clearAllBtn = document.getElementById('clear-all-filters');
        if (clearAllBtn) clearAllBtn.addEventListener('click', function () { window.resetFilters(); });

        // Search
        const searchInput = document.getElementById('search-input');
        let searchTimeout;
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => performSearch(), 300);
            });
            // Restore from URL
            if (currentSearch) searchInput.value = currentSearch;
        }

        const searchBtn = document.getElementById('search-btn');
        if (searchBtn) searchBtn.addEventListener('click', performSearch);

        // Per-page select
        const perPageSelect = document.getElementById('per-page-select');
        if (perPageSelect) {
            perPageSelect.value = currentPerPage;
            perPageSelect.addEventListener('change', function () {
                currentPerPage = parseInt(this.value);
                currentPage = 1;
                loadContacts();
                updateURL();
            });
        }

        // Upload form
        setupUploadForm();
    }

    async function performSearch() {
        const searchInput = document.getElementById('search-input');
        currentSearch = searchInput ? searchInput.value.trim() : '';
        currentPage = 1;
        await Promise.all([loadContacts(), loadScopedFilterCounts()]);
        updateURL();
    }

    // ── Filter Sidebar Toggle ─────────────────────────────────────────────

    function toggleFilterSidebar() {
        const sidebar = document.getElementById('filter-sidebar');
        if (!sidebar) return;
        if (sidebar.classList.contains('collapsed')) {
            openFilterSidebar();
        } else {
            closeFilterSidebar();
        }
    }

    function openFilterSidebar() {
        const sidebar = document.getElementById('filter-sidebar');
        const backdrop = document.getElementById('filter-backdrop');
        if (sidebar) sidebar.classList.remove('collapsed');
        if (backdrop) backdrop.classList.remove('hidden');
    }

    function closeFilterSidebar() {
        const sidebar = document.getElementById('filter-sidebar');
        const backdrop = document.getElementById('filter-backdrop');
        if (sidebar) sidebar.classList.add('collapsed');
        if (backdrop) backdrop.classList.add('hidden');
    }

    // ── Filter Section Expand/Collapse ────────────────────────────────────

    window.toggleFilterSection = function (sectionId) {
        const content = document.getElementById(sectionId);
        const header = content?.previousElementSibling;
        const chevron = header?.querySelector('.chevron');
        if (content) {
            const isExpanded = content.classList.contains('expanded');
            if (isExpanded) {
                content.classList.remove('expanded');
                if (chevron) chevron.style.transform = 'rotate(0deg)';
            } else {
                content.classList.add('expanded');
                if (chevron) chevron.style.transform = 'rotate(180deg)';
            }
        }
    };

    // ── Filter Search (within a section) ──────────────────────────────────

    window.filterOptions = (function () {
        let timer = null;
        return function (sectionType) {
            clearTimeout(timer);
            timer = setTimeout(function () {
                const input = document.getElementById(`${sectionType}-search`);
                const container = document.getElementById(`${sectionType}-options`);
                if (!input || !container) return;
                const term = input.value.toLowerCase();
                container.querySelectorAll('.filter-option').forEach(opt => {
                    opt.style.display = opt.textContent.toLowerCase().includes(term) ? 'flex' : 'none';
                });
            }, 200);
        };
    })();

    // ── Checkbox Selection ────────────────────────────────────────────────

    window.updateFilterSelection = function (sectionType, checkbox) {
        const value = checkbox.value;
        const filterKey = sectionMap[sectionType];
        if (!filterKey) return;

        if (checkbox.checked) {
            if (!activeFilters[filterKey].includes(value)) activeFilters[filterKey].push(value);
        } else {
            activeFilters[filterKey] = activeFilters[filterKey].filter(v => v !== value);
        }

        // Sync quick toggle
        if (!checkbox.classList.contains('quick-toggle-checkbox')) {
            const qt = document.querySelector(`#${sectionType}-quick-toggles input[value="${cssEscVal(value)}"]`);
            if (qt) {
                qt.checked = checkbox.checked;
                const item = qt.closest('.quick-toggle-item');
                if (item) item.classList.toggle('active', checkbox.checked);
            }
        }

        updateActiveFiltersDisplay();
        window.applyFilters();
    };

    // ── Quick Toggles ─────────────────────────────────────────────────────

    window.toggleQuickFilter = function (sectionType, value, evt) {
        if (!evt) evt = window.event;
        if (evt.target.type === 'checkbox') return;
        const cb = document.querySelector(`#${sectionType}-quick-toggles input[value="${cssEscVal(value)}"]`);
        if (cb) {
            cb.checked = !cb.checked;
            window.handleQuickToggle(sectionType, cb);
        }
    };

    window.handleQuickToggle = function (sectionType, checkbox) {
        const filterKey = sectionMap[sectionType];
        if (!filterKey) return;
        const value = checkbox.value;
        const item = checkbox.closest('.quick-toggle-item');

        if (checkbox.checked) {
            if (!activeFilters[filterKey].includes(value)) activeFilters[filterKey].push(value);
            if (item) item.classList.add('active');
        } else {
            activeFilters[filterKey] = activeFilters[filterKey].filter(v => v !== value);
            if (item) item.classList.remove('active');
        }

        // Sync full list checkbox
        const fullCb = document.querySelector(`#${sectionType}-options input[value="${cssEscVal(value)}"]`);
        if (fullCb) fullCb.checked = checkbox.checked;

        updateActiveFiltersDisplay();
        window.applyFilters();
    };

    window.toggleAllQuick = function (sectionType) {
        const toggles = document.querySelectorAll(`#${sectionType}-quick-toggles .quick-toggle-checkbox`);
        const activeCount = document.querySelectorAll(`#${sectionType}-quick-toggles .quick-toggle-item.active`).length;
        const shouldCheck = activeCount < toggles.length;
        toggles.forEach(cb => {
            if (cb.checked !== shouldCheck) {
                cb.checked = shouldCheck;
                window.handleQuickToggle(sectionType, cb);
            }
        });
    };

    // ── Apply / Reset Filters ─────────────────────────────────────────────

    window.applyFilters = async function () {
        // Re-scan email/phone status (they bypass updateFilterSelection)
        activeFilters.emailStatus = [];
        activeFilters.phoneStatus = [];
        document.querySelectorAll('#email-filters input[type="checkbox"]:checked').forEach(cb => {
            activeFilters.emailStatus.push(cb.value);
        });
        document.querySelectorAll('#phone-filters input[type="checkbox"]:checked').forEach(cb => {
            activeFilters.phoneStatus.push(cb.value);
        });

        currentPage = 1;
        await Promise.all([loadContacts(), loadScopedFilterCounts()]);
        updateFilterCount();
        updateURL();
    };

    window.resetFilters = async function () {
        activeFilters = { companies: [], titles: [], sources: [], emailStatus: [], phoneStatus: [] };

        document.querySelectorAll('.filter-option input[type="checkbox"]').forEach(cb => { cb.checked = false; });
        document.querySelectorAll('.quick-toggle-checkbox').forEach(cb => {
            cb.checked = false;
            const item = cb.closest('.quick-toggle-item');
            if (item) item.classList.remove('active');
        });
        document.querySelectorAll('.filter-search').forEach(inp => { inp.value = ''; });
        document.querySelectorAll('.filter-options .filter-option').forEach(opt => { opt.style.display = 'flex'; });

        updateActiveFiltersDisplay();
        populateFilterOptions();
        window.applyFilters();
    };

    // ── Active Filter Tags ────────────────────────────────────────────────

    function updateActiveFiltersDisplay() {
        const container = document.getElementById('active-filters');
        const tagsEl = document.getElementById('active-filter-tags');
        if (!container || !tagsEl) return;

        const all = [];
        Object.entries(activeFilters).forEach(([key, vals]) => {
            vals.forEach(v => all.push({ type: key, value: v }));
        });

        if (all.length === 0) {
            container.style.display = 'none';
            updateFilterCount();
            return;
        }

        container.style.display = 'block';
        updateFilterCount();

        tagsEl.innerHTML = all.map(f => `
            <span class="filter-tag">
                ${esc(f.value)}
                <span class="remove-tag" onclick="removeFilterTag('${f.type}', '${escAttr(f.value)}')">&times;</span>
            </span>
        `).join('');
    }

    window.removeFilterTag = function (filterType, value) {
        if (activeFilters[filterType]) {
            activeFilters[filterType] = activeFilters[filterType].filter(v => v !== value);
        }
        // Uncheck matching checkboxes
        document.querySelectorAll(`input[type="checkbox"][value="${cssEscVal(value)}"]`).forEach(cb => {
            cb.checked = false;
            const item = cb.closest('.quick-toggle-item');
            if (item) item.classList.remove('active');
        });
        updateActiveFiltersDisplay();
        window.applyFilters();
    };

    function updateFilterCount() {
        const total = Object.values(activeFilters).reduce((t, arr) => t + arr.length, 0);
        const el = document.getElementById('filter-count');
        if (el) el.textContent = total;

        const badge = document.getElementById('filter-toolbar-badge');
        const btn = document.getElementById('filter-toolbar-btn');
        if (badge && btn) {
            if (total > 0) {
                badge.textContent = total;
                badge.style.display = '';
                btn.classList.add('has-active');
            } else {
                badge.style.display = 'none';
                btn.classList.remove('has-active');
            }
        }
    }

    // ── Scoped / Faceted Counts ───────────────────────────────────────────

    async function loadScopedFilterCounts() {
        if (!hasActiveFilters() && !currentSearch) return;
        try {
            const res = await fetch('/contacts_scoped_filter_counts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ search: currentSearch, filters: activeFilters })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            updateAllFilterCounts(data);
        } catch (err) {
            console.error('Failed to load scoped filter counts:', err);
        }
    }

    function updateAllFilterCounts(data) {
        Object.entries(sectionMap).forEach(([type, key]) => {
            const counts = data[key] || {};
            // Update full list counts
            const opts = document.getElementById(`${type}-options`);
            if (opts) {
                opts.querySelectorAll('.filter-option').forEach(label => {
                    const cb = label.querySelector('input[type="checkbox"]');
                    const span = label.querySelector('.option-count');
                    if (cb && span) span.textContent = counts[cb.value] || 0;
                });
            }
            // Update quick toggle counts
            const qt = document.getElementById(`${type}-quick-toggles`);
            if (qt) {
                qt.querySelectorAll('.quick-toggle-item').forEach(item => {
                    const cb = item.querySelector('.quick-toggle-checkbox');
                    const span = item.querySelector('.quick-toggle-count');
                    if (cb && span) span.textContent = counts[cb.value] || 0;
                });
            }
            // Update header badge
            const countEl = document.getElementById(`${type}-count`);
            if (countEl) countEl.textContent = Object.values(counts).filter(c => c > 0).length;
        });

        // Email status
        const es = data.emailStatus || {};
        const hasEm = document.getElementById('has-email-count');
        if (hasEm) hasEm.textContent = es.has_email || 0;
        const noEm = document.getElementById('no-email-count');
        if (noEm) noEm.textContent = es.no_email || 0;
        const emCount = document.getElementById('email-count');
        if (emCount) emCount.textContent = (es.has_email || 0) + (es.no_email || 0);

        // Phone status
        const ps = data.phoneStatus || {};
        const hasPh = document.getElementById('has-phone-count');
        if (hasPh) hasPh.textContent = ps.has_phone || 0;
        const noPh = document.getElementById('no-phone-count');
        if (noPh) noPh.textContent = ps.no_phone || 0;
        const phCount = document.getElementById('phone-count');
        if (phCount) phCount.textContent = (ps.has_phone || 0) + (ps.no_phone || 0);
    }

    // ── URL Persistence ───────────────────────────────────────────────────

    function loadFiltersFromURL() {
        const p = new URLSearchParams(window.location.search);
        activeFilters.companies = p.getAll('companies') || [];
        activeFilters.titles = p.getAll('titles') || [];
        activeFilters.sources = p.getAll('sources') || [];
        activeFilters.emailStatus = p.getAll('emailStatus') || [];
        activeFilters.phoneStatus = p.getAll('phoneStatus') || [];

        const s = p.get('search');
        if (s) currentSearch = s;
        const pg = p.get('page');
        if (pg) currentPage = parseInt(pg);
        const pp = p.get('per_page');
        if (pp) currentPerPage = parseInt(pp);
    }

    function updateURL() {
        const url = new URL(window.location);
        ['companies', 'titles', 'sources', 'emailStatus', 'phoneStatus', 'search', 'page', 'per_page'].forEach(k => url.searchParams.delete(k));
        Object.entries(activeFilters).forEach(([key, vals]) => {
            vals.forEach(v => url.searchParams.append(key, v));
        });
        if (currentSearch) url.searchParams.set('search', currentSearch);
        if (currentPage > 1) url.searchParams.set('page', currentPage);
        if (currentPerPage !== 50) url.searchParams.set('per_page', currentPerPage);
        window.history.replaceState({}, '', url);
    }

    function hasActiveFilters() {
        return Object.values(activeFilters).some(arr => arr.length > 0);
    }

    // ── Upload ────────────────────────────────────────────────────────────

    function setupUploadForm() {
        const fileInput = document.getElementById('contactsFile');
        const fileNameEl = document.getElementById('upload-file-name');
        const submitBtn = document.getElementById('upload-btn');
        const form = document.getElementById('contacts-upload-form');
        const resultEl = document.getElementById('upload-results');

        if (!fileInput || !form) return;

        fileInput.addEventListener('change', function () {
            if (this.files[0]) {
                fileNameEl.textContent = this.files[0].name;
                submitBtn.disabled = false;
            } else {
                fileNameEl.textContent = 'No file chosen';
                submitBtn.disabled = true;
            }
        });

        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const file = fileInput.files[0];
            if (!file) return;

            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Uploading...';
            resultEl.style.display = 'none';

            try {
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch('/upload_contacts', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.error) {
                    resultEl.innerHTML = `<div class="upload-error">${esc(data.error)}</div>`;
                } else {
                    resultEl.innerHTML = `<div class="upload-success">
                        <strong>${esc(data.filename)}</strong> imported successfully<br>
                        ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped
                        (${data.total_rows} total rows)
                    </div>`;
                    // Refresh everything
                    await loadFilterData();
                    populateFilterOptions();
                    loadStats();
                    loadContacts();
                }
                resultEl.style.display = 'block';
            } catch (err) {
                resultEl.innerHTML = `<div class="upload-error">Upload failed: ${esc(err.message)}</div>`;
                resultEl.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
                fileInput.value = '';
                fileNameEl.textContent = 'No file chosen';
            }
        });
    }

    // ── Export ─────────────────────────────────────────────────────────────

    window.exportContacts = function (format) {
        const params = new URLSearchParams();
        if (currentSearch) params.set('search', currentSearch);
        Object.entries(activeFilters).forEach(([key, vals]) => {
            vals.forEach(v => params.append(key, v));
        });
        params.set('format', format === 'xlsx' ? 'excel' : 'csv');
        window.location.href = '/export_contacts?' + params.toString();
    };

    // ── Helpers ────────────────────────────────────────────────────────────

    function esc(str) {
        if (!str) return '';
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function escAttr(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function cssEscVal(str) {
        return str.replace(/"/g, '\\"');
    }

})();
