document.addEventListener('DOMContentLoaded', function() {
    const importersTable = document.getElementById('importers-table');
    const importersTbody = document.getElementById('importers-tbody');
    const paginationContainer = document.getElementById('pagination-container');
    const importerSearch = document.getElementById('importer-search');
    const searchBtn = document.getElementById('search-btn');
    const perPageSelect = document.getElementById('per-page-select');
    const sortSelect = document.getElementById('sort-select');
    
    let currentPage = 1;
    let currentSearch = '';
    let currentPerPage = 24;
    let currentSort = 'name';
    let sortDirection = 'asc';
    
    // Load statistics
    loadStatistics();
    
    // Load all importers
    loadImporters();
    
    // Search functionality
    searchBtn.addEventListener('click', performSearch);
    importerSearch.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Per page change
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            const value = this.value;
            currentPerPage = value === 'all' ? 9999 : parseInt(value);
            currentPage = 1;
            loadImporters(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
        });
    }
    
    // Sort change
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentSort = this.value;
            currentPage = 1;
            loadImporters(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
        });
    }
    
    // Table header sorting
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            const sortType = this.getAttribute('data-sort');
            if (currentSort === sortType) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort = sortType;
                sortDirection = 'asc';
            }
            
            // Update UI
            document.querySelectorAll('.sortable').forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
            });
            this.classList.add(sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
            
            currentPage = 1;
            loadImporters(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
        });
    });
    
    async function loadStatistics() {
        try {
            const response = await fetch('/get_database_stats');
            const stats = await response.json();
            
            document.getElementById('total-importers').textContent = stats.total_importers || 0;
            document.getElementById('total-brands').textContent = stats.total_brands || 0;
            
            // Calculate active importers (ones with brands)
            const importersResponse = await fetch('/get_all_importers?per_page=10000');
            const importersData = await importersResponse.json();
            const activeImporters = importersData.importers ? 
                importersData.importers.filter(imp => imp.brands && imp.brands.length > 0).length : 0;
            document.getElementById('active-importers').textContent = activeImporters;
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }
    
    async function loadImporters(page = 1, search = '', perPage = currentPerPage, sort = currentSort, direction = sortDirection) {
        try {
            const url = `/get_all_importers?page=${page}&per_page=${perPage}&search=${encodeURIComponent(search)}&sort=${sort}&direction=${direction}`;
            const response = await fetch(url);
            const data = await response.json();
            
            displayImporters(data.importers || []);
            displayPagination(data.pagination);
        } catch (error) {
            console.error('Failed to load importers:', error);
            importersTbody.innerHTML = `
                <tr class="error-row">
                    <td colspan="6" class="loading-cell">
                        <div class="loading-content">
                            <span style="color: var(--error-color);">❌ Failed to load importers. Please try again.</span>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
    
    function displayImporters(importers) {
        if (importers.length === 0) {
            importersTbody.innerHTML = `
                <tr class="empty-state-row">
                    <td colspan="6" class="empty-state-cell">
                        <div class="empty-state-content">
                            <div class="empty-state-icon">🏢</div>
                            <h3>No Importers Found</h3>
                            <p>Upload importer registry files to start building your importer database.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        importersTbody.innerHTML = importers.map(importer => {
            const hasActiveBrands = importer.brands && importer.brands.length > 0;
            const brandCount = hasActiveBrands ? importer.brands.length : 0;
            const status = hasActiveBrands ? 'active' : 'inactive';
            const displayName = importer.owner_name || importer.operating_name || 'Unknown Importer';
            const location = formatLocation(importer);
            
            return `
            <tr class="fade-in" data-importer="${importer.permit_number}">
                <td class="importer-name-cell">
                    <a href="/importer/${encodeURIComponent(importer.permit_number)}" class="importer-name-link text-ellipsis">
                        ${displayName}
                    </a>
                    ${importer.operating_name && importer.owner_name !== importer.operating_name ? 
                        `<div class="location-secondary">${importer.operating_name}</div>` : ''}
                </td>
                <td class="text-center">
                    <span class="permit-number-cell">${importer.permit_number}</span>
                </td>
                <td class="brand-count-cell">
                    <span class="brand-count-badge">${brandCount}</span>
                </td>
                <td class="location-cell">
                    <div class="location-primary">${location.primary}</div>
                    ${location.secondary ? `<div class="location-secondary">${location.secondary}</div>` : ''}
                </td>
                <td class="status-cell">
                    <span class="status-badge ${status}">
                        ${status === 'active' ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td class="actions-cell">
                    <a href="/importer/${encodeURIComponent(importer.permit_number)}" class="action-btn">👁️ View</a>
                </td>
            </tr>
            `;
        }).join('');
    }
    
    function formatLocation(importer) {
        const parts = [];
        
        // Build primary location (city, state)
        if (importer.city) parts.push(importer.city);
        if (importer.state) parts.push(importer.state);
        
        const primary = parts.length > 0 ? parts.join(', ') : 'Unknown Location';
        
        // Build secondary location (country if not US, or full address)
        let secondary = '';
        if (importer.country && importer.country !== 'United States' && importer.country !== 'US') {
            secondary = importer.country;
        } else if (importer.zip) {
            secondary = importer.zip;
        }
        
        return { primary, secondary };
    }
    
    async function performSearch() {
        currentSearch = importerSearch.value.trim();
        currentPage = 1;
        await loadImporters(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
    }
    
    function displayPagination(pagination) {
        if (!pagination) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHtml = '<div class="pagination-controls" style="display: flex; justify-content: space-between; align-items: center;">';
        
        // Info section
        paginationHtml += `<div class="pagination-info">
            Showing ${((pagination.page - 1) * pagination.per_page) + 1}-${Math.min(pagination.page * pagination.per_page, pagination.total)} of ${pagination.total} importers
        </div>`;
        
        if (pagination.pages > 1) {
            paginationHtml += '<div class="pagination">';
            
            // Previous button
            if (pagination.has_prev) {
                paginationHtml += `<button class="pagination-btn" onclick="goToPage(${pagination.page - 1})">← Previous</button>`;
            }
            
            // Page numbers
            const startPage = Math.max(1, pagination.page - 2);
            const endPage = Math.min(pagination.pages, pagination.page + 2);
            
            if (startPage > 1) {
                paginationHtml += `<button class="pagination-btn" onclick="goToPage(1)">1</button>`;
                if (startPage > 2) paginationHtml += '<span class="pagination-ellipsis">...</span>';
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const isActive = i === pagination.page;
                paginationHtml += `<button class="pagination-btn ${isActive ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
            }
            
            if (endPage < pagination.pages) {
                if (endPage < pagination.pages - 1) paginationHtml += '<span class="pagination-ellipsis">...</span>';
                paginationHtml += `<button class="pagination-btn" onclick="goToPage(${pagination.pages})">${pagination.pages}</button>`;
            }
            
            // Next button
            if (pagination.has_next) {
                paginationHtml += `<button class="pagination-btn" onclick="goToPage(${pagination.page + 1})">Next →</button>`;
            }
            
            paginationHtml += '</div>';
        } else {
            paginationHtml += '<div></div>'; // Empty div for spacing
        }
        
        paginationHtml += '</div>';
        paginationContainer.innerHTML = paginationHtml;
    }
    
    window.goToPage = async function(page) {
        currentPage = page;
        await loadImporters(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
    };
});