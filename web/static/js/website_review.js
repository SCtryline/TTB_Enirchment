// Website Review JavaScript

let websitesData = [];
let filteredData = [];
let selectedWebsites = new Set();
let currentPage = 1;
const itemsPerPage = 20;
let currentReviewItem = null;

// Load websites on page load
document.addEventListener('DOMContentLoaded', function() {
    loadWebsitesForReview();
    updateProcessedToday();
});

async function loadWebsitesForReview() {
    try {
        const response = await fetch('/websites_needing_review');
        const data = await response.json();
        
        websitesData = data.websites || [];
        applyFilters();
        updateStatistics();
    } catch (error) {
        console.error('Error loading websites:', error);
        showError('Failed to load websites for review');
    }
}

function updateStatistics() {
    const totalPending = websitesData.length;
    const lowConfidence = websitesData.filter(w => w.confidence < 0.5).length;
    const flaggedCount = websitesData.filter(w => w.verification_status === 'flagged').length;
    
    document.getElementById('total-pending').textContent = totalPending;
    document.getElementById('low-confidence').textContent = lowConfidence;
    document.getElementById('flagged-count').textContent = flaggedCount;
}

function updateProcessedToday() {
    // This would normally fetch from backend
    const processedToday = localStorage.getItem('processed_today_' + new Date().toDateString()) || 0;
    document.getElementById('processed-today').textContent = processedToday;
}

function applyFilters() {
    const statusFilter = document.getElementById('filter-status').value;
    const confidenceFilter = document.getElementById('filter-confidence').value;
    const searchTerm = document.getElementById('search-brand').value.toLowerCase();
    
    filteredData = websitesData.filter(website => {
        // Status filter
        if (statusFilter !== 'all' && website.verification_status !== statusFilter) {
            return false;
        }
        
        // Confidence filter
        if (confidenceFilter !== 'all') {
            const confidence = website.confidence;
            if (confidenceFilter === 'low' && confidence >= 0.5) return false;
            if (confidenceFilter === 'medium' && (confidence < 0.5 || confidence > 0.8)) return false;
            if (confidenceFilter === 'high' && confidence <= 0.8) return false;
        }
        
        // Search filter
        if (searchTerm && !website.brand_name.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        return true;
    });
    
    currentPage = 1;
    renderTable();
    renderPagination();
}

function resetFilters() {
    document.getElementById('filter-status').value = 'all';
    document.getElementById('filter-confidence').value = 'all';
    document.getElementById('search-brand').value = '';
    applyFilters();
}

function renderTable() {
    const tbody = document.getElementById('review-tbody');
    const noResults = document.getElementById('no-results');
    
    if (filteredData.length === 0) {
        tbody.innerHTML = '';
        noResults.style.display = 'block';
        return;
    }
    
    noResults.style.display = 'none';
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = filteredData.slice(startIndex, endIndex);
    
    tbody.innerHTML = pageData.map(website => {
        const isSelected = selectedWebsites.has(website.brand_name);
        const confidenceClass = website.confidence < 0.5 ? 'low' : 
                              website.confidence < 0.8 ? 'medium' : 'high';
        
        return `
            <tr data-brand="${escapeHtml(website.brand_name)}">
                <td class="checkbox-col">
                    <input type="checkbox" 
                           onchange="toggleSelection('${escapeHtml(website.brand_name)}')"
                           ${isSelected ? 'checked' : ''}>
                </td>
                <td>
                    <a href="/brand/${encodeURIComponent(website.brand_name)}" 
                       class="brand-link" target="_blank">
                        ${escapeHtml(website.brand_name)}
                    </a>
                </td>
                <td>
                    <a href="${escapeHtml(website.url)}" 
                       class="website-link" target="_blank">
                        🔗 ${escapeHtml(website.domain)}
                    </a>
                </td>
                <td>
                    <span class="confidence-badge confidence-${confidenceClass}">
                        ${(website.confidence * 100).toFixed(0)}%
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${website.verification_status}">
                        ${website.verification_status}
                    </span>
                </td>
                <td>${escapeHtml(website.source || 'search')}</td>
                <td>${formatDate(website.updated_date)}</td>
                <td class="action-buttons">
                    <button class="action-btn" onclick="quickReview('${escapeHtml(website.brand_name)}')">
                        Quick Review
                    </button>
                    <button class="action-btn" onclick="verifyWebsite('${escapeHtml(website.brand_name)}')">
                        ✅
                    </button>
                    <button class="action-btn" onclick="rejectWebsite('${escapeHtml(website.brand_name)}')">
                        ❌
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function renderPagination() {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    html += `<button class="page-btn" onclick="goToPage(${currentPage - 1})" 
             ${currentPage === 1 ? 'disabled' : ''}>Previous</button>`;
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" 
                     onclick="goToPage(${i})">${i}</button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<span>...</span>';
        }
    }
    
    // Next button
    html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" 
             ${currentPage === totalPages ? 'disabled' : ''}>Next</button>`;
    
    pagination.innerHTML = html;
}

function goToPage(page) {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    renderTable();
    renderPagination();
}

// Selection functions
function toggleSelection(brandName) {
    if (selectedWebsites.has(brandName)) {
        selectedWebsites.delete(brandName);
    } else {
        selectedWebsites.add(brandName);
    }
    updateBulkButtons();
}

function toggleSelectAll() {
    const checkbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('#review-tbody input[type="checkbox"]');
    
    checkboxes.forEach(cb => {
        const brandName = cb.closest('tr').dataset.brand;
        if (checkbox.checked) {
            selectedWebsites.add(brandName);
        } else {
            selectedWebsites.delete(brandName);
        }
        cb.checked = checkbox.checked;
    });
    
    updateBulkButtons();
}

function selectAll() {
    filteredData.forEach(website => {
        selectedWebsites.add(website.brand_name);
    });
    document.getElementById('select-all-checkbox').checked = true;
    renderTable();
    updateBulkButtons();
}

function deselectAll() {
    selectedWebsites.clear();
    document.getElementById('select-all-checkbox').checked = false;
    renderTable();
    updateBulkButtons();
}

function updateBulkButtons() {
    const count = selectedWebsites.size;
    document.getElementById('selected-count').textContent = count;
    
    const bulkVerifyBtn = document.getElementById('bulk-verify-btn');
    const bulkRejectBtn = document.getElementById('bulk-reject-btn');
    const bulkFlagBtn = document.getElementById('bulk-flag-btn');
    
    bulkVerifyBtn.disabled = count === 0;
    bulkRejectBtn.disabled = count === 0;
    bulkFlagBtn.disabled = count === 0;
}

// Bulk actions
async function bulkVerify() {
    if (!confirm(`Verify ${selectedWebsites.size} websites?`)) return;
    
    const results = await processBulkAction('verify', true);
    showResults(results);
}

async function bulkReject() {
    if (!confirm(`Reject ${selectedWebsites.size} websites?`)) return;
    
    const results = await processBulkAction('verify', false);
    showResults(results);
}

async function bulkFlag() {
    const reason = prompt('Reason for flagging (optional):');
    if (reason === null) return;
    
    const results = await processBulkAction('flag', null, reason);
    showResults(results);
}

async function processBulkAction(action, verified, reason) {
    const results = { success: 0, failed: 0 };
    
    for (const brandName of selectedWebsites) {
        try {
            let response;
            if (action === 'verify') {
                response = await fetch('/verify_website', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brand_name: brandName, verified: verified })
                });
            } else if (action === 'flag') {
                response = await fetch('/flag_website', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brand_name: brandName, reason: reason })
                });
            }
            
            if (response.ok) {
                results.success++;
                updateProcessedCount();
            } else {
                results.failed++;
            }
        } catch (error) {
            results.failed++;
        }
    }
    
    return results;
}

function showResults(results) {
    alert(`Processed ${results.success + results.failed} websites:\n` +
          `✅ Success: ${results.success}\n` +
          `❌ Failed: ${results.failed}`);
    
    selectedWebsites.clear();
    loadWebsitesForReview();
}

// Individual actions
async function verifyWebsite(brandName) {
    try {
        const response = await fetch('/verify_website', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand_name: brandName, verified: true })
        });
        
        if (response.ok) {
            showSuccess('Website verified');
            updateProcessedCount();
            loadWebsitesForReview();
        } else {
            showError('Failed to verify website');
        }
    } catch (error) {
        showError('Error verifying website');
    }
}

async function rejectWebsite(brandName) {
    try {
        const response = await fetch('/verify_website', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand_name: brandName, verified: false })
        });
        
        if (response.ok) {
            showSuccess('Website rejected');
            updateProcessedCount();
            loadWebsitesForReview();
        } else {
            showError('Failed to reject website');
        }
    } catch (error) {
        showError('Error rejecting website');
    }
}

// Quick review modal
function quickReview(brandName) {
    const website = websitesData.find(w => w.brand_name === brandName);
    if (!website) return;
    
    currentReviewItem = website;
    
    document.getElementById('modal-brand').textContent = website.brand_name;
    document.getElementById('modal-website').href = website.url;
    document.getElementById('modal-website').textContent = website.domain;
    document.getElementById('modal-confidence').textContent = `${(website.confidence * 100).toFixed(0)}%`;
    document.getElementById('modal-status').textContent = website.verification_status;
    
    document.getElementById('quick-review-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('quick-review-modal').style.display = 'none';
    currentReviewItem = null;
}

async function quickVerify() {
    if (!currentReviewItem) return;
    await verifyWebsite(currentReviewItem.brand_name);
    closeModal();
}

async function quickFlag() {
    if (!currentReviewItem) return;
    const reason = prompt('Reason for flagging:');
    if (reason === null) return;
    
    try {
        const response = await fetch('/flag_website', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                brand_name: currentReviewItem.brand_name, 
                reason: reason 
            })
        });
        
        if (response.ok) {
            showSuccess('Website flagged');
            updateProcessedCount();
            loadWebsitesForReview();
            closeModal();
        }
    } catch (error) {
        showError('Error flagging website');
    }
}

async function quickReject() {
    if (!currentReviewItem) return;
    await rejectWebsite(currentReviewItem.brand_name);
    closeModal();
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
    });
}

function updateProcessedCount() {
    const key = 'processed_today_' + new Date().toDateString();
    const current = parseInt(localStorage.getItem(key) || 0);
    localStorage.setItem(key, current + 1);
    document.getElementById('processed-today').textContent = current + 1;
}

function showSuccess(message) {
    // Simple alert for now, could be replaced with toast
    console.log('Success:', message);
}

function showError(message) {
    console.error('Error:', message);
    alert(message);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('quick-review-modal');
    if (event.target === modal) {
        closeModal();
    }
};