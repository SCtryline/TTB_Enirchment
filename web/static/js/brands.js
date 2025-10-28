document.addEventListener('DOMContentLoaded', async function() {
    try {
        console.log('🚀 Brands page initializing...');
        
        const brandsTable = document.getElementById('brands-table');
        const brandsTbody = document.getElementById('brands-tbody');
        const paginationContainer = document.getElementById('pagination-container');
        // Modal references removed since we now use dedicated pages
        const brandSearch = document.getElementById('brand-search');
        const searchBtn = document.getElementById('search-btn');
        const perPageSelect = document.getElementById('per-page-select');
        const sortSelect = document.getElementById('sort-select');
        
        console.log('📋 DOM elements found:', {
            brandsTable: !!brandsTable,
            brandsTbody: !!brandsTbody,
            paginationContainer: !!paginationContainer,
            brandSearch: !!brandSearch,
            searchBtn: !!searchBtn
        });
    
    let currentPage = 1;
    let currentSearch = '';
    let currentPerPage = 24;
    let currentSort = 'name';
    let sortDirection = 'asc';
    
    // Filter state
    let activeFilters = {
        importers: [],
        alcoholTypes: [],
        producers: [],
        countries: [],
        websiteStatus: []
    };
    
    // Filter data cache
    let filterData = {
        importers: {},
        alcoholTypes: {},
        producers: {},
        countries: {},
        websiteStatus: {
            'has_website': 0,
            'verified': 0,
            'no_website': 0
        }
    };
    
        // Load statistics
        console.log('📊 Loading statistics...');
        loadStatistics();
        
        // Initialize filters (this will also load brands)
        console.log('🔧 Initializing filters...');
        await initializeFilters();
        console.log('✅ Brands page initialization complete!');
    
    // Search functionality
    searchBtn.addEventListener('click', performSearch);
    brandSearch.addEventListener('keypress', function(e) {
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
            loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
        });
    }
    
    // Sort change
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentSort = this.value;
            currentPage = 1;
            loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
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
            loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection);
        });
    });
    
    // Modal code removed - using dedicated pages now
    
    async function loadStatistics() {
        try {
            const response = await fetch('/get_database_stats');
            const stats = await response.json();
            
            const totalBrandsElement = document.getElementById('total-brands');
            const totalSkusElement = document.getElementById('total-skus');
            const totalImportersElement = document.getElementById('total-importers');
            
            if (totalBrandsElement) totalBrandsElement.textContent = stats.total_brands || 0;
            if (totalSkusElement) totalSkusElement.textContent = stats.total_skus || 0;
            if (totalImportersElement) totalImportersElement.textContent = stats.total_importers || 0;
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }
    
    async function loadBrands(page = 1, search = '', perPage = currentPerPage, sort = currentSort, direction = sortDirection, filters = null) {
        try {
            let url = `/get_all_brands?page=${page}&per_page=${perPage}&search=${encodeURIComponent(search)}&sort=${sort}&direction=${direction}`;
            
            // Add filters to URL if provided
            if (filters) {
                Object.entries(filters).forEach(([key, values]) => {
                    if (values && values.length > 0) {
                        values.forEach(value => {
                            url += `&${key}=${encodeURIComponent(value)}`;
                        });
                    }
                });
            }
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            displayBrands(data.brands || []);
            displayPagination(data.pagination);
            
            // Update stats
            updateFilteredStats(data);
        } catch (error) {
            console.error('Failed to load brands:', error);
            brandsTbody.innerHTML = `
                <tr class="error-row">
                    <td colspan="7" class="loading-cell">
                        <div class="loading-content">
                            <span style="color: var(--error-color);">❌ Failed to load brands. Please try again.</span>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
    
    function displayBrands(brands) {
        if (brands.length === 0) {
            brandsTbody.innerHTML = `
                <tr class="empty-state-row">
                    <td colspan="8" class="empty-state-cell">
                        <div class="empty-state-content">
                            <div class="empty-state-icon">📁</div>
                            <h3>No Brands Found</h3>
                            <p>Upload COLA registry files to start building your brand database.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        brandsTbody.innerHTML = brands.map(brand => {
            const hasImporter = brand.importers && brand.importers.length > 0 && !brand.importers.includes('No importer found');
            const hasProducer = brand.producers && brand.producers.length > 0;
            
            // Website status display - check both website field and enrichment_data field
            const website = brand.website;
            const enrichment = brand.enrichment_data;
            let websiteDisplay = '❌';
            let websiteClass = 'no-website';
            let websiteTitle = 'No website found';
            
            let websiteData = null;
            
            // First check main website field
            if (website) {
                if (typeof website === 'string') {
                    try {
                        websiteData = JSON.parse(website);
                    } catch (e) {
                        websiteData = {};
                    }
                } else {
                    websiteData = website;
                }
            }
            
            // Also check enrichment_data field for manual entries
            if (!websiteData && enrichment) {
                let enrichmentData;
                if (typeof enrichment === 'string') {
                    try {
                        enrichmentData = JSON.parse(enrichment);
                    } catch (e) {
                        enrichmentData = {};
                    }
                } else {
                    enrichmentData = enrichment;
                }
                
                // If enrichment data has URL or is manual override, use it
                if (enrichmentData.url || enrichmentData.source === 'manual_override') {
                    websiteData = enrichmentData;
                }
                // Also check for nested website structure
                else if (enrichmentData.website && enrichmentData.website.url) {
                    websiteData = enrichmentData.website;
                    websiteData.source = 'manual'; // Mark as manual for display
                }
            }
            
            // Display website status
            if (websiteData && (websiteData.url || websiteData.verification_status || websiteData.verified)) {
                const isVerified = (websiteData.verification_status === 'verified') || (websiteData.verified === true);
                
                if (isVerified) {
                    websiteDisplay = '✅';
                    websiteClass = 'website-verified';
                    const source = (websiteData.source === 'manual_override' || websiteData.source === 'manual') ? '(Manual)' : '';
                    websiteTitle = `Verified ${source}: ${websiteData.domain || websiteData.url || 'Website found'}`;
                } else if (websiteData.url) {
                    websiteDisplay = '✅';
                    websiteClass = 'website-found';
                    const source = (websiteData.source === 'manual_override' || websiteData.source === 'manual') ? '(Manual)' : '';
                    websiteTitle = `Website found ${source}: ${websiteData.domain || websiteData.url}`;
                }
            }
            
            // Primary contact display (placeholder for now - will be implemented in next phase)
            let contactDisplay = '❌';
            let contactClass = 'no-contact';
            let contactTitle = 'No primary contact found';
            
            // Check if enrichment data has contact information
            const contactEnrichment = brand.enrichment_data;
            if (contactEnrichment) {
                let enrichmentData;
                if (typeof contactEnrichment === 'string') {
                    try {
                        enrichmentData = JSON.parse(contactEnrichment);
                    } catch (e) {
                        enrichmentData = {};
                    }
                } else {
                    enrichmentData = contactEnrichment;
                }
                
                // Check for Apollo contacts, founders with contact info, or LinkedIn profiles
                const hasContacts = enrichmentData.apollo_contacts && enrichmentData.apollo_contacts.length > 0;
                const hasFounders = enrichmentData.founders && enrichmentData.founders.length > 0;
                const hasLinkedIn = enrichmentData.linkedin_profiles && enrichmentData.linkedin_profiles.length > 0;
                const hasEmailContacts = enrichmentData.apollo_contacts && 
                                       enrichmentData.apollo_contacts.some(c => c.email);
                
                if (hasContacts || hasFounders || hasLinkedIn) {
                    contactDisplay = '✅';
                    contactClass = 'has-contact';
                    
                    let details = [];
                    if (hasEmailContacts) details.push('Email contacts');
                    if (hasFounders) details.push(`${enrichmentData.founders.length} founder(s)`);
                    if (hasLinkedIn) details.push('LinkedIn profiles');
                    
                    contactTitle = `Contact info: ${details.join(', ')}`;
                }
            }
            
            return `
            <tr class="fade-in" data-brand="${brand.brand_name}">
                <td class="checkbox-cell">
                    <label class="checkbox-container">
                        <input type="checkbox" class="brand-checkbox" data-brand="${brand.brand_name}">
                        <span class="checkmark"></span>
                    </label>
                </td>
                <td class="brand-name-cell">
                    <a href="/brand/${encodeURIComponent(brand.brand_name)}" class="brand-name-link text-ellipsis">
                        ${brand.brand_name}
                    </a>
                </td>
                <td class="countries-cell">
                    <div class="countries-list">
                        ${formatTagList(brand.countries, 'country-tag')}
                    </div>
                </td>
                <td class="types-cell">
                    <div class="types-list">
                        ${formatTagList(brand.class_types, 'type-tag', 2)}
                    </div>
                </td>
                <td class="status-cell text-center">
                    <span class="match-indicator ${hasProducer ? 'matched' : 'unmatched'}" title="${hasProducer ? 'Producer matched' : 'No producer match'}">
                        ${hasProducer ? '✅' : '❌'}
                    </span>
                </td>
                <td class="status-cell text-center">
                    <span class="match-indicator ${hasImporter ? 'matched' : 'unmatched'}" title="${hasImporter ? 'Importer matched' : 'No importer match'}">
                        ${hasImporter ? '✅' : '❌'}
                    </span>
                </td>
                <td class="website-cell text-center">
                    <span class="website-indicator ${websiteClass}" title="${websiteTitle}">
                        ${websiteDisplay}
                    </span>
                </td>
                <td class="contact-cell text-center">
                    <span class="contact-indicator ${contactClass}" title="${contactTitle}">
                        ${contactDisplay}
                    </span>
                </td>
                <td class="actions-cell">
                    <button class="action-btn enrich-btn" 
                            data-brand="${brand.brand_name.replace(/"/g, '&quot;')}"
                            data-class="${(brand.class_types && brand.class_types[0] || '').replace(/"/g, '&quot;')}"
                            title="Enrich Brand">
                        🔍 Enrich
                    </button>
                </td>
            </tr>
            `;
        }).join('');
        
        // Add event listeners to enrichment buttons
        document.querySelectorAll('.enrich-btn').forEach(btn => {
            btn.addEventListener('click', handleEnrichment);
        });
    }
    
    async function handleEnrichment(event) {
        const btn = event.currentTarget;
        const brandName = btn.dataset.brand;
        const classType = btn.dataset.class;
        
        // Disable button and show loading
        btn.disabled = true;
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Working...';
        
        try {
            // Check if enrichment is available
            const statusResponse = await fetch('/enrichment/status');
            const status = await statusResponse.json();
            
            if (!status.available) {
                alert('Brand enrichment system is not available. Please set APOLLO_API_KEY environment variable.');
                return;
            }
            
            // Perform enrichment
            const response = await fetch('/enrichment/enrich_brand', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    brand_name: brandName,
                    class_type: classType,
                    skip_cache: false
                })
            });
            
            // Check if response is ok and content-type is JSON
            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                throw new Error(`Invalid response format. Expected JSON, got: ${contentType}. Response: ${text.substring(0, 200)}...`);
            }
            
            const result = await response.json();
            
            if (result.success && result.enrichment_data) {
                // Enrichment successful - redirect to review page
                btn.innerHTML = '🔍 Opening Review...';
                btn.style.backgroundColor = '#007bff';
                btn.style.color = 'white';
                
                // Small delay to show feedback, then redirect
                setTimeout(() => {
                    window.location.href = `/enrichment/review/${encodeURIComponent(brandName)}`;
                }, 500);
                
            } else {
                alert(`Failed to enrich ${brandName}: ${result.error || 'Unknown error'}`);
                btn.innerHTML = originalText;
            }
            
        } catch (error) {
            console.error('Enrichment error:', error);
            alert(`Error enriching ${brandName}: ${error.message}`);
            btn.innerHTML = originalText;
        } finally {
            btn.disabled = false;
        }
    }
    
    function formatTagList(items, className, maxItems = 3) {
        if (!items || items.length === 0) return '<span class="no-data">None</span>';
        
        const displayItems = items.slice(0, maxItems);
        let html = displayItems.map(item => `<span class="${className}">${item}</span>`).join('');
        
        if (items.length > maxItems) {
            html += `<span class="${className} more-indicator">+${items.length - maxItems}</span>`;
        }
        
        return html;
    }
    
    function formatList(items, maxItems = 3) {
        if (!items || items.length === 0) return 'None';
        if (items.length <= maxItems) return items.join(', ');
        return items.slice(0, maxItems).join(', ') + ` (+${items.length - maxItems} more)`;
    }
    
    // Brand detail modal code removed - now using dedicated pages
    
    async function performSearch() {
        currentSearch = brandSearch.value.trim();
        currentPage = 1;
        await loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection, activeFilters);
        updateURL();
    }
    
    function displayPagination(pagination) {
        if (!pagination) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHtml = '<div class="pagination-controls" style="display: flex; justify-content: space-between; align-items: center;">';
        
        // Info section
        paginationHtml += `<div class="pagination-info">
            Showing ${((pagination.page - 1) * pagination.per_page) + 1}-${Math.min(pagination.page * pagination.per_page, pagination.total)} of ${pagination.total} brands
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
        await loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection, activeFilters);
        updateURL();
    };
    
    // === FILTER FUNCTIONALITY ===
    
    async function initializeFilters() {
        // Load filters from URL
        loadFiltersFromURL();
        
        // Set up filter event listeners
        setupFilterEventListeners();
        
        // Load filter data
        await loadFilterData();
        
        // Initialize filter UI
        populateFilterOptions();
        
        // Apply filters (or load brands if no filters)
        if (hasActiveFilters()) {
            currentPage = 1;
            await loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection, activeFilters);
            updateFilterCount();
            updateURL();
        } else {
            await loadBrands();
        }
    }
    
    function loadFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Load each filter type from URL
        activeFilters.importers = urlParams.getAll('importers') || [];
        activeFilters.alcoholTypes = urlParams.getAll('alcoholTypes') || [];
        activeFilters.producers = urlParams.getAll('producers') || [];
        activeFilters.countries = urlParams.getAll('countries') || [];
        activeFilters.websiteStatus = urlParams.getAll('websiteStatus') || [];
        
        // Load search term
        const searchParam = urlParams.get('search');
        if (searchParam) {
            currentSearch = searchParam;
            if (brandSearch) {
                brandSearch.value = searchParam;
            }
        }
        
        // Load page
        const pageParam = urlParams.get('page');
        if (pageParam) {
            currentPage = parseInt(pageParam);
        }
        
        console.log('Loaded filters from URL:', activeFilters);
    }
    
    function updateURL() {
        const url = new URL(window.location);
        
        // Clear existing filter params
        url.searchParams.delete('importers');
        url.searchParams.delete('alcoholTypes');
        url.searchParams.delete('producers');
        url.searchParams.delete('countries');
        url.searchParams.delete('websiteStatus');
        url.searchParams.delete('search');
        url.searchParams.delete('page');
        
        // Add active filters
        Object.entries(activeFilters).forEach(([key, values]) => {
            values.forEach(value => {
                url.searchParams.append(key, value);
            });
        });
        
        // Add search if present
        if (currentSearch) {
            url.searchParams.set('search', currentSearch);
        }
        
        // Add page if not 1
        if (currentPage > 1) {
            url.searchParams.set('page', currentPage);
        }
        
        // Update URL without page reload
        window.history.replaceState({}, '', url);
    }
    
    function hasActiveFilters() {
        return Object.values(activeFilters).some(filters => filters.length > 0);
    }
    
    function setupFilterEventListeners() {
        // Filter toggle (in sidebar)
        const toggleBtn = document.getElementById('toggle-filters');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleFilterSidebar);
        }
        
        // Floating toggle button
        const floatingToggleBtn = document.getElementById('filter-toggle-float');
        if (floatingToggleBtn) {
            floatingToggleBtn.addEventListener('click', toggleFilterSidebar);
        }
        
        // Clear all filters
        const clearAllBtn = document.getElementById('clear-all-filters');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', clearAllFilters);
        }
        
        // Apply filters button
        const applyBtn = document.querySelector('.apply-filters-btn');
        if (applyBtn) {
            applyBtn.addEventListener('click', function() { window.applyFilters(); });
        }
        
        // Reset filters button  
        const resetBtn = document.querySelector('.reset-filters-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() { window.resetFilters(); });
        }
    }
    
    async function loadFilterData() {
        try {
            const response = await fetch('/get_filter_data');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            filterData = data;
            
            console.log('Filter data loaded:', filterData);
        } catch (error) {
            console.error('Failed to load filter data:', error);
            // Use mock data for development
            filterData = {
                importers: {
                    'PARK STREET IMPORTS LLC': 19,
                    'BARSAC, INC.': 32,
                    'AFTERMATH WINE & SPIRITS LLC': 26
                },
                alcoholTypes: {
                    'Whiskey': 150,
                    'Wine': 200,
                    'Beer': 100,
                    'Vodka': 75
                },
                producers: {
                    'ABC Distillery': 25,
                    'XYZ Winery': 30
                },
                countries: {
                    'United States': 500,
                    'France': 150,
                    'Italy': 120
                },
                websiteStatus: {
                    'has_website': 150,
                    'verified': 75,
                    'no_website': 200
                }
            };
        }
    }
    
    function populateFilterOptions() {
        
        // Populate importer filter
        populateFilterSection('importer', filterData.importers);
        
        // Populate alcohol type filter
        populateFilterSection('alcohol', filterData.alcoholTypes);
        
        // Populate producer filter
        populateFilterSection('producer', filterData.producers);
        
        // Populate country filter
        populateFilterSection('country', filterData.countries);
        
        // Update website status counts
        updateWebsiteStatusCounts();
        
        // Restore selected filters from URL
        restoreSelectedFilters();
        
        // Update active filters display
        updateActiveFiltersDisplay();
    }
    
    function restoreSelectedFilters() {
        // Map section types to filter keys
        const sectionMap = {
            'importer': 'importers',
            'alcohol': 'alcoholTypes',
            'producer': 'producers',
            'country': 'countries'
        };
        
        // Restore checkboxes for each section
        Object.entries(sectionMap).forEach(([sectionType, filterKey]) => {
            const activeValues = activeFilters[filterKey] || [];
            activeValues.forEach(value => {
                const checkbox = document.querySelector(`input[type="checkbox"][value="${value.replace(/"/g, '&quot;')}"]`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
        });
        
        // Restore website status filters
        activeFilters.websiteStatus.forEach(value => {
            const checkbox = document.querySelector(`input[type="checkbox"][value="${value}"]`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
    
    function populateFilterSection(sectionType, data) {
        const optionsContainer = document.getElementById(`${sectionType}-options`);
        const quickTogglesContainer = document.getElementById(`${sectionType}-quick-toggles`);
        const countElement = document.getElementById(`${sectionType}-count`);
        
        
        if (!data) return;
        
        // Sort by count (descending)
        const sortedEntries = Object.entries(data).sort((a, b) => b[1] - a[1]);
        
        // Update section count (total brands, not unique options)
        if (countElement) {
            const totalBrands = sortedEntries.reduce((total, [name, count]) => total + count, 0);
            countElement.textContent = totalBrands;
        }
        
        // Populate Quick Toggles (Top 10)
        if (quickTogglesContainer) {
            const top10 = sortedEntries.slice(0, 10);
            const quickToggleHTML = top10.map(([name, count]) => `
                <div class="quick-toggle-item" onclick="toggleQuickFilter('${sectionType}', '${name.replace(/'/g, "\\'")}', event)">
                    <input type="checkbox" class="quick-toggle-checkbox" 
                           value="${name.replace(/"/g, '&quot;')}" 
                           data-filter-type="${sectionType}"
                           data-filter-value="${name.replace(/"/g, '&quot;')}"
                           onchange="handleQuickToggle('${sectionType}', this)" 
                           onclick="event.stopPropagation()">
                    <span class="quick-toggle-label" title="${name}">${name}</span>
                    <span class="quick-toggle-count">${count}</span>
                </div>
            `).join('');
            
            quickTogglesContainer.innerHTML = quickToggleHTML;
        }
        
        // Populate Full Options List
        if (optionsContainer) {
            const optionsHTML = sortedEntries.map(([name, count]) => `
                <label class="filter-option" data-value="${name.replace(/"/g, '&quot;')}">
                    <input type="checkbox" value="${name.replace(/"/g, '&quot;')}" onchange="updateFilterSelection('${sectionType}', this)">
                    <span>${name}</span>
                    <span class="option-count">${count}</span>
                </label>
            `).join('');
            
            optionsContainer.innerHTML = optionsHTML;
        }
    }
    
    function updateWebsiteStatusCounts() {
        const counts = filterData.websiteStatus || {};
        
        const elements = {
            'has-website-count': counts.has_website || 0,
            'verified-count': counts.verified || 0,
            'no-website-count': counts.no_website || 0
        };
        
        Object.entries(elements).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = count;
            }
        });
        
        // Update website section count
        const websiteCount = document.getElementById('website-count');
        if (websiteCount) {
            const totalWebsiteStatusBrands = Object.values(elements).reduce((total, count) => total + count, 0);
            websiteCount.textContent = totalWebsiteStatusBrands;
        }
    }
    
    // Global functions for HTML event handlers
    window.toggleFilterSection = function(sectionId) {
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
    
    window.filterOptions = function(sectionType) {
        const searchInput = document.getElementById(`${sectionType}-search`);
        const optionsContainer = document.getElementById(`${sectionType}-options`);
        
        if (!searchInput || !optionsContainer) return;
        
        const searchTerm = searchInput.value.toLowerCase();
        const options = optionsContainer.querySelectorAll('.filter-option');
        
        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            const matches = text.includes(searchTerm);
            option.style.display = matches ? 'flex' : 'none';
        });
    };
    
    window.updateFilterSelection = function(sectionType, checkbox) {
        const value = checkbox.value;
        const isChecked = checkbox.checked;
        
        // Map section types to filter keys
        const sectionMap = {
            'importer': 'importers',
            'alcohol': 'alcoholTypes',
            'producer': 'producers',
            'country': 'countries'
        };
        
        const filterKey = sectionMap[sectionType];
        if (!filterKey) return;
        
        if (isChecked) {
            if (!activeFilters[filterKey].includes(value)) {
                activeFilters[filterKey].push(value);
            }
        } else {
            activeFilters[filterKey] = activeFilters[filterKey].filter(item => item !== value);
        }
        
        // Sync with quick toggle if this is from full list
        if (!checkbox.classList.contains('quick-toggle-checkbox')) {
            const quickToggleCheckbox = document.querySelector(`#${sectionType}-quick-toggles input[value="${value.replace(/"/g, '&quot;')}"]`);
            if (quickToggleCheckbox) {
                quickToggleCheckbox.checked = isChecked;
                const quickToggleItem = quickToggleCheckbox.closest('.quick-toggle-item');
                if (quickToggleItem) {
                    if (isChecked) {
                        quickToggleItem.classList.add('active');
                    } else {
                        quickToggleItem.classList.remove('active');
                    }
                }
            }
        }
        
        updateActiveFiltersDisplay();
        window.applyFilters();
    };
    
    window.applyFilters = async function() {
        // Clear current filters
        activeFilters = {
            importers: [],
            alcoholTypes: [],
            producers: [],
            countries: [],
            websiteStatus: []
        };
        
        // Collect all checked filter values
        
        // Importers
        document.querySelectorAll('#importer-filters input[type="checkbox"]:checked').forEach(checkbox => {
            activeFilters.importers.push(checkbox.value);
        });
        
        // Alcohol Types
        document.querySelectorAll('#alcohol-filters input[type="checkbox"]:checked').forEach(checkbox => {
            activeFilters.alcoholTypes.push(checkbox.value);
        });
        
        // Producers
        document.querySelectorAll('#producer-filters input[type="checkbox"]:checked').forEach(checkbox => {
            activeFilters.producers.push(checkbox.value);
        });
        
        // Countries
        document.querySelectorAll('#country-filters input[type="checkbox"]:checked').forEach(checkbox => {
            activeFilters.countries.push(checkbox.value);
        });
        
        // Website Status
        document.querySelectorAll('#website-filters input[type="checkbox"]:checked').forEach(checkbox => {
            activeFilters.websiteStatus.push(checkbox.value);
        });
        
        console.log('Applying filters:', activeFilters);
        
        currentPage = 1;
        await loadBrands(currentPage, currentSearch, currentPerPage, currentSort, sortDirection, activeFilters);
        updateFilterCount();
        updateURL();
    };
    
    window.resetFilters = function() {
        // Clear all filters
        activeFilters = {
            importers: [],
            alcoholTypes: [],
            producers: [],
            countries: [],
            websiteStatus: []
        };
        
        // Uncheck all checkboxes
        document.querySelectorAll('.filter-option input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Uncheck all quick toggle checkboxes and remove active states
        document.querySelectorAll('.quick-toggle-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            const quickToggleItem = checkbox.closest('.quick-toggle-item');
            if (quickToggleItem) {
                quickToggleItem.classList.remove('active');
            }
        });
        
        // Clear search inputs
        document.querySelectorAll('.filter-search').forEach(input => {
            input.value = '';
        });
        
        // Reset filter displays
        document.querySelectorAll('.filter-options .filter-option').forEach(option => {
            option.style.display = 'flex';
        });
        
        updateActiveFiltersDisplay();
        window.applyFilters();
    };
    
    function toggleFilterSidebar() {
        const sidebar = document.getElementById('filter-sidebar');
        const floatingBtn = document.getElementById('filter-toggle-float');
        const toggleIcon = document.querySelector('.toggle-icon');
        
        if (sidebar) {
            const isCollapsed = sidebar.classList.contains('collapsed');
            
            if (isCollapsed) {
                // Expanding sidebar
                sidebar.classList.remove('collapsed');
                if (floatingBtn) floatingBtn.style.display = 'none';
                if (toggleIcon) toggleIcon.textContent = '◀';
            } else {
                // Collapsing sidebar
                sidebar.classList.add('collapsed');
                if (floatingBtn) floatingBtn.style.display = 'block';
                if (toggleIcon) toggleIcon.textContent = '▶';
            }
        }
    }
    
    function clearAllFilters() {
        window.resetFilters();
    }
    
    function updateActiveFiltersDisplay() {
        const activeFiltersContainer = document.getElementById('active-filters');
        const activeFilterTags = document.getElementById('active-filter-tags');
        
        if (!activeFiltersContainer || !activeFilterTags) return;
        
        // Collect all active filters
        const allActiveFilters = [];
        
        Object.entries(activeFilters).forEach(([key, values]) => {
            values.forEach(value => {
                allActiveFilters.push({ type: key, value: value });
            });
        });
        
        if (allActiveFilters.length === 0) {
            activeFiltersContainer.style.display = 'none';
            return;
        }
        
        activeFiltersContainer.style.display = 'block';
        
        // Generate filter tags
        const tagsHTML = allActiveFilters.map(filter => `
            <span class="filter-tag">
                ${filter.value}
                <span class="remove-tag" onclick="removeFilterTag('${filter.type}', '${filter.value.replace(/'/g, "\\'")}')">×</span>
            </span>
        `).join('');
        
        activeFilterTags.innerHTML = tagsHTML;
    }
    
    window.removeFilterTag = function(filterType, value) {
        if (activeFilters[filterType]) {
            activeFilters[filterType] = activeFilters[filterType].filter(item => item !== value);
        }
        
        // Uncheck corresponding checkbox
        const checkbox = document.querySelector(`input[type="checkbox"][value="${value.replace(/"/g, '&quot;')}"]`);
        if (checkbox) {
            checkbox.checked = false;
        }
        
        updateActiveFiltersDisplay();
        applyFilters();
    };
    
    function updateFilterCount() {
        const filterCountElement = document.getElementById('filter-count');
        if (filterCountElement) {
            const totalFilters = Object.values(activeFilters).reduce((total, filters) => total + filters.length, 0);
            filterCountElement.textContent = totalFilters;
        }
    }
    
    
    function updateFilteredStats(data) {
        const filteredBrandsElement = document.getElementById('filtered-brands');
        const totalBrandsElement = document.getElementById('total-brands');
        const totalSkusElement = document.getElementById('total-skus');
        
        if (data.pagination && filteredBrandsElement) {
            filteredBrandsElement.textContent = data.pagination.total || 0;
        }
        
        if (data.total_skus && totalSkusElement) {
            totalSkusElement.textContent = data.total_skus;
        }
    }
    
    // === QUICK TOGGLE FUNCTIONS ===
    
    window.toggleQuickFilter = function(sectionType, value, evt) {
        // This function is called when clicking on the quick toggle item (not the checkbox)
        if (!evt) evt = window.event;
        
        // Don't do anything if the checkbox itself was clicked
        if (evt.target.type === 'checkbox') {
            return;
        }
        
        const checkbox = document.querySelector(`#${sectionType}-quick-toggles input[value="${value.replace(/"/g, '&quot;')}"]`);
        if (checkbox) {
            checkbox.checked = !checkbox.checked;
            window.handleQuickToggle(sectionType, checkbox);
        }
    };
    
    window.handleQuickToggle = function(sectionType, checkbox) {
        const filterKey = sectionType + 's'; // Convert to plural
        const filterValue = checkbox.value;
        const quickToggleItem = checkbox.closest('.quick-toggle-item');
        
        if (checkbox.checked) {
            // Add to active filters
            if (!activeFilters[filterKey]) {
                activeFilters[filterKey] = [];
            }
            if (!activeFilters[filterKey].includes(filterValue)) {
                activeFilters[filterKey].push(filterValue);
            }
            if (quickToggleItem) {
                quickToggleItem.classList.add('active');
            }
        } else {
            // Remove from active filters
            if (activeFilters[filterKey]) {
                const index = activeFilters[filterKey].indexOf(filterValue);
                if (index > -1) {
                    activeFilters[filterKey].splice(index, 1);
                }
            }
            if (quickToggleItem) {
                quickToggleItem.classList.remove('active');
            }
        }
        
        // Sync with full list checkbox if it exists
        const fullListCheckbox = document.querySelector(`#${sectionType}-options input[value="${filterValue.replace(/"/g, '&quot;')}"]`);
        if (fullListCheckbox) {
            fullListCheckbox.checked = checkbox.checked;
        }
        
        updateActiveFiltersDisplay();
        window.applyFilters();
    };
    
    window.toggleAllQuick = function(sectionType) {
        const quickToggles = document.querySelectorAll(`#${sectionType}-quick-toggles .quick-toggle-checkbox`);
        const activeCount = document.querySelectorAll(`#${sectionType}-quick-toggles .quick-toggle-item.active`).length;
        const shouldCheckAll = activeCount < quickToggles.length;
        
        quickToggles.forEach(checkbox => {
            if (checkbox.checked !== shouldCheckAll) {
                checkbox.checked = shouldCheckAll;
                window.handleQuickToggle(sectionType, checkbox);
            }
        });
    };
    
    // Update restoreSelectedFilters to include quick toggles
    const originalRestoreSelectedFilters = restoreSelectedFilters;
    restoreSelectedFilters = function() {
        // Call original function
        originalRestoreSelectedFilters();
        
        // Restore quick toggle states
        const sectionMap = {
            'importer': 'importers',
            'alcohol': 'alcoholTypes',
            'producer': 'producers',
            'country': 'countries'
        };
        
        Object.entries(sectionMap).forEach(([sectionType, filterKey]) => {
            const activeValues = activeFilters[filterKey] || [];
            activeValues.forEach(value => {
                const quickToggleCheckbox = document.querySelector(`#${sectionType}-quick-toggles input[value="${value.replace(/"/g, '&quot;')}"]`);
                if (quickToggleCheckbox) {
                    quickToggleCheckbox.checked = true;
                    const quickToggleItem = quickToggleCheckbox.closest('.quick-toggle-item');
                    if (quickToggleItem) {
                        quickToggleItem.classList.add('active');
                    }
                }
            });
        });
    };
    
    } catch (error) {
        console.error('💥 Error initializing brands page:', error);
        // Show error message to user
        const brandsTbody = document.getElementById('brands-tbody');
        if (brandsTbody) {
            brandsTbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 30px; color: #ef4444;">
                        <div>❌ Error loading brands page</div>
                        <div style="font-size: 0.875rem; margin-top: 8px;">${error.message}</div>
                        <button onclick="location.reload()" style="margin-top: 12px; padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Reload Page
                        </button>
                    </td>
                </tr>
            `;
        }
    }

});