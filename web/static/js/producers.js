// Producers Page JavaScript - Following the existing pattern from importers.js

let allProducers = [];
let filteredProducers = [];
let currentPage = 1;
let producersPerPage = 24;
let currentSort = 'name';
let currentDirection = 'asc';
let currentSearch = '';
let currentTypeFilter = 'all';

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadProducerStats();
    loadProducers();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    const searchInput = document.getElementById('producer-search');
    const searchBtn = document.getElementById('search-btn');
    const perPageSelect = document.getElementById('per-page-select');
    const typeFilter = document.getElementById('type-filter');
    const sortSelect = document.getElementById('sort-select');
    const directionSelect = document.getElementById('direction-select');
    
    // Search functionality
    searchInput.addEventListener('input', handleSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
    searchBtn.addEventListener('click', handleSearch);
    
    // Controls
    perPageSelect.addEventListener('change', handlePerPageChange);
    typeFilter.addEventListener('change', handleTypeFilterChange);
    sortSelect.addEventListener('change', handleSortChange);
    directionSelect.addEventListener('change', handleDirectionChange);
    
    // Table header sorting
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => handleHeaderSort(header.dataset.sort));
    });
}

// Load producer statistics
async function loadProducerStats() {
    try {
        const response = await fetch('/get_producer_stats');
        const data = await response.json();
        
        document.getElementById('total-producers').textContent = data.total_producers.toLocaleString();
        document.getElementById('spirit-producers').textContent = data.spirit_producers.toLocaleString();
        document.getElementById('wine-producers').textContent = data.wine_producers.toLocaleString();
    } catch (error) {
        console.error('Error loading producer stats:', error);
    }
}

// Load all producers
async function loadProducers() {
    try {
        showLoading(true);
        
        const response = await fetch('/get_all_producers?per_page=25000');
        const data = await response.json();
        
        allProducers = data.producers || [];
        applyFilters();
        
    } catch (error) {
        console.error('Error loading producers:', error);
        showError('Failed to load producers. Please try again.');
    } finally {
        showLoading(false);
    }
}

// Apply current filters and sorting
function applyFilters() {
    filteredProducers = allProducers.filter(producer => {
        // Search filter
        if (currentSearch) {
            const searchLower = currentSearch.toLowerCase();
            const searchMatch = (
                producer.owner_name.toLowerCase().includes(searchLower) ||
                producer.operating_name.toLowerCase().includes(searchLower) ||
                producer.permit_number.toLowerCase().includes(searchLower) ||
                producer.city.toLowerCase().includes(searchLower) ||
                producer.state.toLowerCase().includes(searchLower)
            );
            if (!searchMatch) return false;
        }
        
        // Type filter
        if (currentTypeFilter !== 'all' && producer.type !== currentTypeFilter) {
            return false;
        }
        
        return true;
    });
    
    // Apply sorting
    sortProducers();
    
    // Reset to first page
    currentPage = 1;
    
    // Render results
    renderProducers();
    renderPagination();
}

// Sort producers
function sortProducers() {
    filteredProducers.sort((a, b) => {
        let aVal = '';
        let bVal = '';
        
        switch (currentSort) {
            case 'name':
                aVal = a.owner_name || '';
                bVal = b.owner_name || '';
                break;
            case 'permit':
                aVal = a.permit_number || '';
                bVal = b.permit_number || '';
                break;
            case 'operating_name':
                aVal = a.operating_name || '';
                bVal = b.operating_name || '';
                break;
            case 'type':
                aVal = a.type || '';
                bVal = b.type || '';
                break;
            case 'city':
                aVal = a.city || '';
                bVal = b.city || '';
                break;
            case 'state':
                aVal = a.state || '';
                bVal = b.state || '';
                break;
            default:
                aVal = a.owner_name || '';
                bVal = b.owner_name || '';
        }
        
        // Convert to lowercase for case-insensitive sorting
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
        
        if (currentDirection === 'asc') {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }
    });
}

// Render producers table
function renderProducers() {
    const tbody = document.getElementById('producers-table-body');
    const noResults = document.getElementById('no-results');
    
    if (filteredProducers.length === 0) {
        tbody.innerHTML = '';
        noResults.style.display = 'block';
        return;
    }
    
    noResults.style.display = 'none';
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * producersPerPage;
    const endIndex = startIndex + producersPerPage;
    const pageProducers = filteredProducers.slice(startIndex, endIndex);
    
    // Generate table rows
    tbody.innerHTML = pageProducers.map(producer => {
        const ownerName = producer.owner_name || 'N/A';
        const operatingName = producer.operating_name || '';
        const permitNumber = producer.permit_number || '';
        const city = producer.city || '';
        const state = producer.state || '';
        const brandCount = (producer.brands && producer.brands.length) || 0;
        const producerType = producer.type || 'Unknown';
        
        // Determine display values
        const displayOperatingName = operatingName || '<em>None</em>';
        const locationDisplay = city && state ? `${city}, ${state}` : (city || state || 'N/A');
        
        return `
            <tr>
                <td>
                    <a href="/producer/${encodeURIComponent(permitNumber)}" class="producer-link">
                        ${escapeHtml(ownerName)}
                    </a>
                </td>
                <td><code>${escapeHtml(permitNumber)}</code></td>
                <td>${displayOperatingName !== '<em>None</em>' ? escapeHtml(displayOperatingName) : displayOperatingName}</td>
                <td>
                    <span class="status-badge status-${producerType.toLowerCase()}">
                        ${producerType === 'Spirit' ? '🥃' : '🍷'} ${producerType}
                    </span>
                </td>
                <td class="location">${escapeHtml(locationDisplay)}</td>
                <td>${escapeHtml(state)}</td>
                <td>
                    <span class="brand-count ${brandCount > 0 ? 'has-brands' : ''}">
                        ${brandCount}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

// Render pagination
function renderPagination() {
    const totalPages = Math.ceil(filteredProducers.length / producersPerPage);
    const paginationInfo = document.getElementById('pagination-info');
    const paginationControls = document.getElementById('pagination-controls');
    
    // Update info
    const startIndex = (currentPage - 1) * producersPerPage + 1;
    const endIndex = Math.min(currentPage * producersPerPage, filteredProducers.length);
    paginationInfo.textContent = `Showing ${startIndex}-${endIndex} of ${filteredProducers.length.toLocaleString()} producers`;
    
    // Generate pagination controls
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">
            ← Previous
        </button>
    `;
    
    // Page numbers
    const maxVisiblePages = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    if (startPage > 1) {
        paginationHTML += `<button class="pagination-btn" onclick="goToPage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">
                ${i}
            </button>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
        paginationHTML += `<button class="pagination-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    paginationHTML += `
        <button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">
            Next →
        </button>
    `;
    
    paginationControls.innerHTML = paginationHTML;
}

// Event handlers
function handleSearch() {
    currentSearch = document.getElementById('producer-search').value.trim();
    applyFilters();
}

function handlePerPageChange() {
    producersPerPage = parseInt(document.getElementById('per-page-select').value);
    applyFilters();
}

function handleTypeFilterChange() {
    currentTypeFilter = document.getElementById('type-filter').value;
    applyFilters();
}

function handleSortChange() {
    currentSort = document.getElementById('sort-select').value;
    updateSortDirection();
    applyFilters();
}

function handleDirectionChange() {
    currentDirection = document.getElementById('direction-select').value;
    updateSortDirection();
    applyFilters();
}

function handleHeaderSort(sortField) {
    if (currentSort === sortField) {
        // Toggle direction if same field
        currentDirection = currentDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // New field, default to ascending
        currentSort = sortField;
        currentDirection = 'asc';
    }
    
    // Update select elements
    document.getElementById('sort-select').value = currentSort;
    document.getElementById('direction-select').value = currentDirection;
    
    updateSortDirection();
    applyFilters();
}

function updateSortDirection() {
    // Update table header indicators
    document.querySelectorAll('.sortable').forEach(header => {
        header.classList.remove('sorted-asc', 'sorted-desc');
        if (header.dataset.sort === currentSort) {
            header.classList.add(currentDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    });
}

function goToPage(page) {
    const totalPages = Math.ceil(filteredProducers.length / producersPerPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    renderProducers();
    renderPagination();
    
    // Scroll to top of table
    document.querySelector('.table-container').scrollIntoView({ behavior: 'smooth' });
}

// Utility functions
function showLoading(show) {
    const loading = document.getElementById('loading-indicator');
    const table = document.querySelector('.table-container');
    const pagination = document.querySelector('.pagination-container');
    
    if (show) {
        loading.style.display = 'block';
        table.style.display = 'none';
        pagination.style.display = 'none';
    } else {
        loading.style.display = 'none';
        table.style.display = 'block';
        pagination.style.display = 'flex';
    }
}

function showError(message) {
    const tbody = document.getElementById('producers-table-body');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 2rem; color: var(--error);">
                ⚠️ ${message}
            </td>
        </tr>
    `;
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}