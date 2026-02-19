// Contacts Directory — client-side logic

let currentPage = 1;
const perPage = 50;

document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadFilterOptions();
    loadContacts();
    setupUploadForm();
    setupFilterListeners();
    setupExportButtons();
});

// ── Stats ──────────────────────────────────────────────────────────────

async function loadStats() {
    try {
        const res = await fetch('/contacts_filter_options');
        const data = await res.json();
        if (data.stats) {
            document.getElementById('stat-total').textContent = data.stats.total.toLocaleString();
            document.getElementById('stat-companies').textContent = data.stats.unique_companies.toLocaleString();
            document.getElementById('stat-with-email').textContent = data.stats.with_email.toLocaleString();
            document.getElementById('stat-with-phone').textContent = data.stats.with_phone.toLocaleString();
        }
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

// ── Filter Options ─────────────────────────────────────────────────────

async function loadFilterOptions() {
    try {
        const res = await fetch('/contacts_filter_options');
        const data = await res.json();

        const companySelect = document.getElementById('filter-company');
        (data.companies || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            companySelect.appendChild(opt);
        });

        const sourceSelect = document.getElementById('filter-source');
        (data.sources || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            sourceSelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Error loading filter options:', err);
    }
}

// ── Contacts Table ─────────────────────────────────────────────────────

function getFilters() {
    return {
        search: document.getElementById('search-input').value.trim(),
        company_name: document.getElementById('filter-company').value,
        has_email: document.getElementById('filter-has-email').value,
        has_phone: document.getElementById('filter-has-phone').value,
        source: document.getElementById('filter-source').value,
    };
}

function buildQueryString(filters, page) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
    params.set('page', page);
    params.set('per_page', perPage);
    return params.toString();
}

async function loadContacts(page) {
    if (page !== undefined) currentPage = page;
    const filters = getFilters();
    const qs = buildQueryString(filters, currentPage);
    const tbody = document.getElementById('contacts-tbody');

    try {
        const res = await fetch('/get_contacts?' + qs);
        const data = await res.json();

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
                <td>${c.email ? '<a href="mailto:' + esc(c.email) + '">' + esc(c.email) + '</a>' : '<span class="text-muted">—</span>'}</td>
                <td>${esc(c.phone || '') || '<span class="text-muted">—</span>'}</td>
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
    info.textContent = `Showing ${start}–${end} of ${data.total.toLocaleString()} contacts`;

    let html = '';
    if (data.page > 1) {
        html += `<button class="btn btn-sm" onclick="loadContacts(${data.page - 1})">Prev</button>`;
    }
    // Show up to 7 page buttons around current page
    const maxButtons = 7;
    let startPage = Math.max(1, data.page - Math.floor(maxButtons / 2));
    let endPage = Math.min(data.total_pages, startPage + maxButtons - 1);
    if (endPage - startPage + 1 < maxButtons) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    for (let p = startPage; p <= endPage; p++) {
        const active = p === data.page ? ' active' : '';
        html += `<button class="btn btn-sm${active}" onclick="loadContacts(${p})">${p}</button>`;
    }
    if (data.page < data.total_pages) {
        html += `<button class="btn btn-sm" onclick="loadContacts(${data.page + 1})">Next</button>`;
    }
    controls.innerHTML = html;
}

// ── Upload ─────────────────────────────────────────────────────────────

function setupUploadForm() {
    const form = document.getElementById('contacts-upload-form');
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const fileInput = document.getElementById('contactsFile');
        if (!fileInput.files.length) return;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const btn = document.getElementById('upload-btn');
        const resultsDiv = document.getElementById('upload-results');
        btn.disabled = true;
        btn.textContent = 'Uploading...';
        resultsDiv.classList.add('hidden');

        try {
            const res = await fetch('/upload_contacts', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                resultsDiv.innerHTML = `<div class="upload-error">${esc(data.error)}</div>`;
            } else {
                resultsDiv.innerHTML = `
                    <div class="upload-success">
                        <strong>${esc(data.filename)}</strong> imported successfully<br>
                        ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped
                        (${data.total_rows} total rows)
                    </div>`;
                // Refresh everything
                loadStats();
                loadFilterOptions();
                loadContacts(1);
            }
            resultsDiv.classList.remove('hidden');
        } catch (err) {
            resultsDiv.innerHTML = `<div class="upload-error">Upload failed: ${esc(err.message)}</div>`;
            resultsDiv.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Upload Contacts';
            fileInput.value = '';
        }
    });
}

// ── Filters ────────────────────────────────────────────────────────────

function setupFilterListeners() {
    let searchTimeout;
    document.getElementById('search-input').addEventListener('input', function () {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadContacts(1), 300);
    });

    ['filter-company', 'filter-has-email', 'filter-has-phone', 'filter-source'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => loadContacts(1));
    });
}

// ── Export ──────────────────────────────────────────────────────────────

function setupExportButtons() {
    document.getElementById('export-csv-btn').addEventListener('click', () => exportContacts('csv'));
    document.getElementById('export-excel-btn').addEventListener('click', () => exportContacts('excel'));
}

function exportContacts(format) {
    const filters = getFilters();
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
    params.set('format', format);
    window.location.href = '/export_contacts?' + params.toString();
}

// ── Helpers ─────────────────────────────────────────────────────────────

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
