document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    loadDashboardData();
    loadMarketInsights();
    setupCharts();
    loadRecentActivity();
    loadTopBrands();
    loadImporterLeaderboard();
    updateSystemHealth();
    
    // Setup PDF export with a small delay to ensure DOM is ready
    setTimeout(setupPDFExport, 100);
    
    // Also add event delegation as fallback
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'export-pdf') {
            console.log('PDF export clicked via delegation');
            handlePDFExport();
        }
    });
    
    // Auto-refresh every 5 minutes
    setInterval(loadDashboardData, 300000);
});

// Load main dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch('/get_database_stats');
        const stats = await response.json();
        
        console.log('Dashboard stats:', stats);
        
        // Update metrics with animation
        animateCounter('dashboard-brands', stats.total_brands || 0);
        animateCounter('dashboard-skus', stats.total_skus || 0);
        animateCounter('dashboard-importers', stats.total_importers || 0);
        
        // Calculate and display match rate
        await calculateMatchRate();
        
        // Update last updated time
        document.getElementById('last-updated').textContent = 
            `Last updated: ${new Date().toLocaleString()}`;
            
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

// Calculate match rate from recent uploads
async function calculateMatchRate() {
    try {
        // This would ideally come from the backend, for now we'll simulate
        const matchRate = 85; // Placeholder
        document.getElementById('dashboard-matches').textContent = matchRate + '%';
        document.getElementById('matches-change').textContent = 'Quality Score';
    } catch (error) {
        console.error('Failed to calculate match rate:', error);
    }
}

// Animate counter numbers
function animateCounter(elementId, finalValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = 0;
    const duration = 1500;
    const startTime = performance.now();
    
    function updateCounter(currentTime) {
        const elapsedTime = currentTime - startTime;
        const progress = Math.min(elapsedTime / duration, 1);
        
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = Math.floor(startValue + (finalValue - startValue) * easeOutQuart);
        
        element.textContent = currentValue.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        }
    }
    
    requestAnimationFrame(updateCounter);
}

// Setup charts
function setupCharts() {
    setupCountryChart();
    setupClassChart();
}

// Global variables for chart management
let locationChart = null;
let brandsData = null;

// Geographic distribution chart with smart filtering
async function setupCountryChart() {
    try {
        const response = await fetch('/get_all_brands?per_page=50000');  // Get ALL brands (sufficient for complete dataset)
        const data = await response.json();
        
        console.log('Brands data for charts:', data);
        
        if (!data.brands || data.brands.length === 0) {
            document.getElementById('countryChart').parentElement.innerHTML = 
                '<p class="no-data">No brand data available</p>';
            return;
        }
        
        // Store brands data globally
        brandsData = data.brands;
        
        console.log(`Setting up charts with ${brandsData.length} brands`);
        
        // Initial chart setup
        updateLocationChart();
        
    } catch (error) {
        console.error('Failed to setup country chart:', error);
    }
}

// Update location chart based on filter selection
async function updateLocationChart() {
    if (!brandsData) return;
    
    const typeFilter = document.getElementById('location-type-filter').value;
    const limitFilter = document.getElementById('location-limit-filter').value;
    
    // Process location data based on filter type
    const locationCount = {};
    
    brandsData.forEach(brand => {
        if (brand.countries && brand.countries.length > 0) {
            brand.countries.forEach(location => {
                const processedLocation = processLocation(location, typeFilter);
                if (processedLocation) {
                    locationCount[processedLocation] = (locationCount[processedLocation] || 0) + 1;
                }
            });
        }
    });
    
    // Sort and limit results
    let sortedLocations = Object.entries(locationCount)
        .sort(([,a], [,b]) => b - a);
    
    if (limitFilter !== 'all') {
        sortedLocations = sortedLocations.slice(0, parseInt(limitFilter));
    }
    
    const labels = sortedLocations.map(([location]) => location);
    const values = sortedLocations.map(([,count]) => count);
    
    // Update or create chart
    const ctx = document.getElementById('countryChart').getContext('2d');
    
    if (locationChart) {
        locationChart.destroy();
    }
    
    locationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Brands',
                data: values,
                backgroundColor: generateChartColors(labels.length),
                borderWidth: 0,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: getChartTitle(typeFilter),
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    color: '#666'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#f0f0f0'
                    },
                    title: {
                        display: true,
                        text: 'Number of Brands'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

// Process location based on filter type
function processLocation(location, filterType) {
    const usStates = [
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 
        'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 
        'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 
        'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 
        'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 
        'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 
        'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 
        'Wisconsin', 'Wyoming', 'District of Columbia'
    ];
    
    const isUsState = usStates.some(state => 
        location.toLowerCase().includes(state.toLowerCase()) || 
        state.toLowerCase().includes(location.toLowerCase())
    );
    
    switch (filterType) {
        case 'countries':
            // Only return actual countries (not US states)
            return isUsState ? 'United States' : location;
            
        case 'usa-states':
            // Only return US states
            return isUsState ? location : null;
            
        case 'all-regions':
        default:
            // Return everything as-is
            return location;
    }
}

// Get chart title based on filter type
function getChartTitle(filterType) {
    switch (filterType) {
        case 'countries':
            return 'Brand Distribution by Country';
        case 'usa-states':
            return 'Brand Distribution by US State';
        case 'all-regions':
            return 'Brand Distribution by Region';
        default:
            return 'Geographic Distribution';
    }
}

// Global variable for class chart
let classChart = null;
let brandsDataForClass = null;

// Class type distribution chart
async function setupClassChart() {
    try {
        const response = await fetch('/get_all_brands?per_page=50000');  // Get ALL brands (sufficient for complete dataset)
        const data = await response.json();
        
        if (!data.brands || data.brands.length === 0) {
            document.getElementById('classChart').parentElement.innerHTML = 
                '<p class="no-data">No brand data available</p>';
            return;
        }
        
        // Store data globally for filtering
        brandsDataForClass = data.brands;
        
        // Initial chart setup
        updateClassChart();
        
    } catch (error) {
        console.error('Failed to setup class chart:', error);
    }
}

// Update class chart based on filter selection
async function updateClassChart() {
    if (!brandsDataForClass) return;
    
    const limitFilter = document.getElementById('class-limit-filter')?.value || '12';
    const detailFilter = document.getElementById('class-detail-filter')?.value || 'simplified';
    
    // Process class type data
    const classCount = {};
    brandsDataForClass.forEach(brand => {
        if (brand.class_types && brand.class_types.length > 0) {
            brand.class_types.forEach(classType => {
                let processedType;
                if (detailFilter === 'detailed') {
                    // Show original class types (truncated for display)
                    processedType = classType.length > 30 ? classType.substring(0, 30) + '...' : classType;
                } else {
                    // Use simplified categorization
                    processedType = simplifyClassType(classType);
                }
                classCount[processedType] = (classCount[processedType] || 0) + 1;
            });
        }
    });
    
    // Sort and limit results
    let sortedClasses = Object.entries(classCount)
        .sort(([,a], [,b]) => b - a);
    
    if (limitFilter !== 'all') {
        sortedClasses = sortedClasses.slice(0, parseInt(limitFilter));
    }
    
    const labels = sortedClasses.map(([classType]) => classType);
    const values = sortedClasses.map(([,count]) => count);
    
    // Generate colors dynamically based on number of items
    const colors = generateChartColors(labels.length);
    
    const ctx = document.getElementById('classChart').getContext('2d');
    
    if (classChart) {
        classChart.destroy();
    }
    
    classChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 12,
                        font: {
                            size: 10
                        },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map((label, i) => {
                                    const dataset = data.datasets[0];
                                    const value = dataset.data[i];
                                    return {
                                        text: `${label} (${value})`,
                                        fillStyle: dataset.backgroundColor[i],
                                        strokeStyle: dataset.backgroundColor[i],
                                        lineWidth: 0,
                                        pointStyle: 'circle'
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed * 100) / total).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Generate chart colors dynamically
function generateChartColors(count) {
    const baseColors = [
        '#667eea', '#f093fb', '#00d2ff', '#3a7bd5', '#ffc107', '#28a745',
        '#dc3545', '#6f42c1', '#e83e8c', '#fd7e14', '#17a2b8', '#6c757d',
        '#20c997', '#ffb3ba', '#bae1ff', '#ffffba', '#ffdfba', '#c7ceea',
        '#b5b5b5', '#ffd1dc', '#e6e6fa', '#f0e68c', '#dda0dd', '#98fb98'
    ];
    
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// Improved class type categorization - more comprehensive and dynamic
function simplifyClassType(classType) {
    const lower = classType.toLowerCase();
    
    // Wine categories (most common)
    if (lower.includes('wine') || lower.includes('champagne')) {
        if (lower.includes('dessert') || lower.includes('port') || lower.includes('sherry')) return 'Dessert Wine';
        if (lower.includes('sparkling') || lower.includes('champagne')) return 'Sparkling Wine';
        if (lower.includes('red')) return 'Red Wine';
        if (lower.includes('white')) return 'White Wine';
        if (lower.includes('rose')) return 'Rosé Wine';
        if (lower.includes('table')) return 'Table Wine';
        return 'Wine';
    }
    
    // Whiskey family (check before malt beverages to catch "malt whisky")
    if (lower.includes('whiskey') || lower.includes('whisky') || lower.includes('bourbon')) {
        if (lower.includes('scotch')) return 'Scotch Whisky';
        if (lower.includes('bourbon')) return 'Bourbon Whiskey';
        if (lower.includes('rye')) return 'Rye Whiskey';
        if (lower.includes('corn')) return 'Corn Whiskey';
        return 'Whiskey';
    }
    
    // Beer & Malt beverages
    if (lower.includes('beer') || lower.includes('ale') || lower.includes('stout') || lower.includes('malt')) {
        if (lower.includes('near beer') || lower.includes('non alcoholic')) return 'Non-Alcoholic Beer';
        return 'Beer & Malt Beverages';
    }
    
    // Vodka
    if (lower.includes('vodka')) return 'Vodka';
    
    // Rum
    if (lower.includes('rum')) return 'Rum';
    
    // Gin
    if (lower.includes('gin')) return 'Gin';
    
    // Brandy & Cognac
    if (lower.includes('brandy') || lower.includes('cognac') || lower.includes('armagnac') || 
        lower.includes('pisco') || lower.includes('grappa')) {
        if (lower.includes('apple')) return 'Apple Brandy';
        if (lower.includes('cognac')) return 'Cognac';
        return 'Brandy';
    }
    
    // Tequila & Agave spirits
    if (lower.includes('tequila') || lower.includes('mezcal') || lower.includes('agave')) {
        if (lower.includes('mezcal')) return 'Mezcal';
        return 'Tequila';
    }
    
    // Liqueurs & Cordials
    if (lower.includes('liqueur') || lower.includes('cordial')) {
        if (lower.includes('coffee') || lower.includes('cafe')) return 'Coffee Liqueur';
        if (lower.includes('fruit')) return 'Fruit Liqueurs';
        if (lower.includes('herb') || lower.includes('seed')) return 'Herbal Liqueurs';
        return 'Liqueurs';
    }
    
    // Specialty items
    if (lower.includes('sake')) return 'Sake';
    if (lower.includes('vermouth')) return 'Vermouth';
    if (lower.includes('bitters')) return 'Bitters';
    if (lower.includes('cocktail')) return 'Cocktails';
    if (lower.includes('sambuca')) return 'Sambuca';
    
    // If none match, return the original (truncated for display)
    return classType.length > 25 ? classType.substring(0, 25) + '...' : classType;
}

// Load recent activity
async function loadRecentActivity() {
    try {
        const response = await fetch('/get_matched_files');
        const data = await response.json();
        
        const activityList = document.getElementById('activity-list');
        
        if (!data.files || data.files.length === 0) {
            activityList.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon">📋</div>
                    <div class="activity-content">
                        <div class="activity-title">No recent activity</div>
                        <div class="activity-time">Upload files to see activity</div>
                    </div>
                </div>
            `;
            return;
        }
        
        const recentFiles = data.files.slice(0, 5); // Show last 5 files
        activityList.innerHTML = recentFiles.map(file => `
            <div class="activity-item">
                <div class="activity-icon">📄</div>
                <div class="activity-content">
                    <div class="activity-title">Processed: ${file.filename}</div>
                    <div class="activity-time">${file.created} • ${file.rows} records</div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load recent activity:', error);
    }
}

// Load top brands
async function loadTopBrands() {
    try {
        const response = await fetch('/get_all_brands?per_page=50000');  // Get ALL brands for proper sorting (sufficient for complete dataset)
        const data = await response.json();
        
        if (!data.brands || data.brands.length === 0) {
            const tbody = document.getElementById('top-brands-body');
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 30px; color: #666;">
                        No brands available. Upload COLA data to see brands.
                    </td>
                </tr>
            `;
            return;
        }
        
        // Sort by SKU count and store globally
        globalBrandsData = data.brands.sort((a, b) => b.total_skus - a.total_skus);
        
        // Initial display
        updateBrandsTable();
        
    } catch (error) {
        console.error('Failed to load top brands:', error);
    }
}

// Update brands table with pagination
function updateBrandsTable() {
    if (!globalBrandsData) return;
    
    // Get current settings
    brandsPerPage = parseInt(document.getElementById('brands-per-page').value);
    
    const tbody = document.getElementById('top-brands-body');
    const totalBrands = globalBrandsData.length;
    const totalPages = Math.ceil(totalBrands / brandsPerPage);
    
    // Ensure current page is valid
    if (brandsCurrentPage > totalPages) brandsCurrentPage = totalPages;
    if (brandsCurrentPage < 1) brandsCurrentPage = 1;
    
    // Calculate pagination
    const startIndex = (brandsCurrentPage - 1) * brandsPerPage;
    const endIndex = startIndex + brandsPerPage;
    const currentBrands = globalBrandsData.slice(startIndex, endIndex);
    
    // Update table
    tbody.innerHTML = currentBrands.map((brand, index) => {
        const globalRank = startIndex + index + 1;
        return `
            <tr>
                <td style="text-align: center; font-weight: bold; color: #667eea;">#${globalRank}</td>
                <td style="font-weight: 500;">${brand.brand_name}</td>
                <td>${brand.total_skus}</td>
                <td>${brand.countries.slice(0, 2).join(', ')}${brand.countries.length > 2 ? ' +' + (brand.countries.length - 2) : ''}</td>
                <td>${brand.importers.length > 0 && !brand.importers.includes('No importer found') ? brand.importers[0] : 'No importer found'}</td>
                <td>
                    <span class="status-badge ${brand.importers.length > 0 && !brand.importers.includes('No importer found') ? 'matched' : 'unmatched'}">
                        ${brand.importers.length > 0 && !brand.importers.includes('No importer found') ? 'Matched' : 'Unmatched'}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update pagination controls
    updateBrandsPagination(totalPages);
}

// Update brands pagination controls
function updateBrandsPagination(totalPages) {
    document.getElementById('brands-page-info').textContent = `Page ${brandsCurrentPage} of ${totalPages}`;
    document.getElementById('brands-prev').disabled = brandsCurrentPage <= 1;
    document.getElementById('brands-next').disabled = brandsCurrentPage >= totalPages;
}

// Change brands page
function changeBrandsPage(direction) {
    const totalPages = Math.ceil(globalBrandsData.length / brandsPerPage);
    
    if (direction === 1 && brandsCurrentPage < totalPages) {
        brandsCurrentPage++;
    } else if (direction === -1 && brandsCurrentPage > 1) {
        brandsCurrentPage--;
    }
    
    updateBrandsTable();
}

// Update system health
function updateSystemHealth() {
    // This would normally check actual system status
    document.getElementById('data-quality').textContent = '✓ Good';
    document.getElementById('last-backup').textContent = new Date().toLocaleDateString();
}

// Refresh activity
function refreshActivity() {
    const btn = document.querySelector('.refresh-btn');
    btn.style.transform = 'rotate(360deg)';
    setTimeout(() => {
        btn.style.transform = 'rotate(0deg)';
    }, 500);
    
    loadRecentActivity();
    loadTopBrands();
    loadImporterLeaderboard();
    loadDashboardData();
}

// Quick search functionality
function openQuickSearch() {
    document.getElementById('quick-search-modal').style.display = 'block';
    document.getElementById('quick-search-input').focus();
}

function closeQuickSearch() {
    document.getElementById('quick-search-modal').style.display = 'none';
    document.getElementById('search-results').innerHTML = '';
}

// Quick search input handler
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('quick-search-input');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length < 2) {
                document.getElementById('search-results').innerHTML = '';
                return;
            }
            
            searchTimeout = setTimeout(async () => {
                await performQuickSearch(query);
            }, 300);
        });
        
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeQuickSearch();
            }
        });
    }
});

// Perform quick search
async function performQuickSearch(query) {
    try {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '<div class="loading">Searching...</div>';
        
        // Search brands
        const brandsResponse = await fetch(`/search_brands?q=${encodeURIComponent(query)}`);
        const brandsData = await brandsResponse.json();
        
        const results = [];
        
        // Add brand results
        if (brandsData.results && brandsData.results.length > 0) {
            brandsData.results.slice(0, 5).forEach(brandName => {
                results.push({
                    type: 'Brand',
                    name: brandName,
                    action: () => window.location.href = '/brands'
                });
            });
        }
        
        // Display results
        if (results.length === 0) {
            resultsContainer.innerHTML = '<div class="no-results">No results found</div>';
            return;
        }
        
        resultsContainer.innerHTML = results.map(result => `
            <div class="search-result-item" onclick="window.location.href='/brands'">
                <strong>${result.type}:</strong> ${result.name}
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Search failed:', error);
        document.getElementById('search-results').innerHTML = 
            '<div class="error">Search failed. Please try again.</div>';
    }
}

// Export data functionality - open modal
function exportData() {
    document.getElementById('export-modal').style.display = 'block';
}

// Close export modal
function closeExportModal() {
    document.getElementById('export-modal').style.display = 'none';
}

// Update export options based on type
function updateExportOptions() {
    const exportType = document.getElementById('export-type').value;
    const importerSection = document.getElementById('importer-filter-section');
    const statusSection = document.getElementById('status-filter-section');
    const additionalFilters = document.getElementById('additional-filters');
    
    // Show/hide sections based on export type
    switch(exportType) {
        case 'brands':
        case 'skus':
            importerSection.style.display = 'block';
            statusSection.style.display = 'block';
            additionalFilters.style.display = 'block';
            break;
        case 'importers':
            importerSection.style.display = 'none';
            statusSection.style.display = 'none';
            additionalFilters.style.display = 'block';
            break;
        case 'matched':
        case 'unmatched':
            importerSection.style.display = 'block';
            statusSection.style.display = 'none';
            additionalFilters.style.display = 'block';
            break;
    }
}

// Update date range inputs
function updateDateRange() {
    const selectedRange = document.querySelector('input[name="date-range"]:checked').value;
    const dateInputs = document.getElementById('date-inputs');
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const customInputs = document.getElementById('custom-date-inputs');
    
    // Hide all first
    dateInputs.style.display = 'none';
    yearSelect.style.display = 'none';
    monthSelect.style.display = 'none';
    customInputs.style.display = 'none';
    
    switch(selectedRange) {
        case 'year':
            dateInputs.style.display = 'block';
            yearSelect.style.display = 'block';
            break;
        case 'month':
            dateInputs.style.display = 'block';
            yearSelect.style.display = 'inline-block';
            monthSelect.style.display = 'inline-block';
            break;
        case 'custom':
            dateInputs.style.display = 'block';
            customInputs.style.display = 'flex';
            break;
    }
}

// Update importer filter
document.addEventListener('DOMContentLoaded', function() {
    const importerFilter = document.getElementById('importer-filter');
    if (importerFilter) {
        importerFilter.addEventListener('change', function() {
            const specificInput = document.getElementById('specific-importer');
            if (this.value === 'specific') {
                specificInput.style.display = 'block';
            } else {
                specificInput.style.display = 'none';
            }
        });
    }
});

// Perform the export
async function performExport() {
    const exportBtn = document.querySelector('.export-btn.primary');
    const btnText = document.getElementById('export-btn-text');
    
    // Get all filter values
    const filters = {
        type: document.getElementById('export-type').value,
        dateRange: document.querySelector('input[name="date-range"]:checked').value,
        year: document.getElementById('year-select').value,
        month: document.getElementById('month-select').value,
        startDate: document.getElementById('start-date').value,
        endDate: document.getElementById('end-date').value,
        importerFilter: document.getElementById('importer-filter').value,
        specificImporter: document.getElementById('specific-importer').value,
        statusFilter: document.getElementById('status-filter').value,
        includeSkus: document.getElementById('include-skus').checked,
        includeImporters: document.getElementById('include-importers').checked,
        includeCountries: document.getElementById('include-countries').checked,
        includeClassTypes: document.getElementById('include-class-types').checked,
        format: document.getElementById('export-format').value
    };
    
    // Show loading state
    exportBtn.disabled = true;
    btnText.textContent = 'Preparing Export...';
    
    try {
        // Build query parameters
        const params = new URLSearchParams();
        for (const [key, value] of Object.entries(filters)) {
            if (value !== '' && value !== 'all') {
                params.append(key, value);
            }
        }
        
        // Call the appropriate export endpoint
        let endpoint = '';
        switch(filters.type) {
            case 'brands':
                endpoint = '/export_filtered_brands';
                break;
            case 'importers':
                endpoint = '/export_filtered_importers';
                break;
            case 'skus':
                endpoint = '/export_filtered_skus';
                break;
            case 'matched':
                endpoint = '/export_matched_data';
                break;
            case 'unmatched':
                endpoint = '/export_unmatched_data';
                break;
        }
        
        // Download the file
        const response = await fetch(`${endpoint}?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        // Get the filename from the Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'export.csv';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }
        
        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Close modal
        closeExportModal();
        
        // Show success message (optional)
        console.log('Export completed successfully');
        
    } catch (error) {
        console.error('Export failed:', error);
        alert('Export failed. Please try again.');
    } finally {
        // Reset button state
        exportBtn.disabled = false;
        btnText.textContent = 'Export Data';
    }
}

// Show system info
function showSystemInfo() {
    const choice = confirm(`TTB COLA Registry System\n\nVersion: 1.0.0\nLast Updated: ${new Date().toLocaleDateString()}\nStatus: Operational\n\nWould you like to reset the brands/COLA database? (This will keep importers but clear all brand/SKU data)\n\nClick OK to reset, Cancel to just view info.`);
    
    if (choice) {
        resetDatabase();
    }
}

// Reset database function
async function resetDatabase() {
    const confirm_reset = confirm('Are you SURE you want to reset the database?\n\nThis will:\n✓ Clear all brands and SKUs\n✓ Clear upload history\n✓ Keep importer data\n\nYou will need to re-upload your COLA CSV files.\n\nThis cannot be undone!');
    
    if (!confirm_reset) return;
    
    try {
        const response = await fetch('/reset_database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Database reset successful!\n\n${result.message}\n\nRemaining importers: ${result.remaining.master_importers}\n\nPage will reload now.`);
            window.location.reload();
        } else {
            alert(`Reset failed: ${result.error}`);
        }
    } catch (error) {
        alert(`Reset failed: ${error.message}`);
    }
}

// Store metrics globally for sorting
let globalImporterMetrics = null;
let globalBrandsData = null;
let allImporterMetrics = null; // Store all importers for sorting

// Pagination state
let brandsCurrentPage = 1;
let brandsPerPage = 10;
let importersCurrentPage = 1;
let importersPerPage = 10;

// Sorting state for importers
let importerSortField = 'brands'; // default sort by brand count
let importerSortDirection = 'desc'; // default descending

// Load importer leaderboard
async function loadImporterLeaderboard() {
    try {
        // Use the new real-time importer metrics endpoint
        const response = await fetch('/get_importer_metrics');
        const data = await response.json();
        
        console.log('Real-time importer metrics:', data);
        
        const tbody = document.getElementById('importer-leaderboard-body');
        
        if (!data.importers || data.importers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; padding: 30px; color: #666;">
                        No importers available. Upload importer data to see leaderboard.
                    </td>
                </tr>
            `;
            return;
        }
        
        // Convert metrics data to match expected format
        allImporterMetrics = data.importers.map(metric => ({
            permit_number: metric.permit_number,
            owner_name: metric.owner_name,
            operating_name: metric.operating_name,
            brandCount: metric.brand_count
        }));
        
        console.log(`Loaded ${allImporterMetrics.length} importers with real-time brand counts`);
        
        // Initial display
        updateImporterLeaderboard();
        
    } catch (error) {
        console.error('Failed to load importer leaderboard:', error);
    }
}


// Get rank CSS class
function getRankClass(rank) {
    switch (rank) {
        case 1: return 'rank-1';
        case 2: return 'rank-2';
        case 3: return 'rank-3';
        default: return 'rank-other';
    }
}

// Get rank emoji
function getRankEmoji(rank) {
    switch (rank) {
        case 1: return '🥇';
        case 2: return '🥈';
        case 3: return '🥉';
        default: return rank;
    }
}

// Updated updateImporterLeaderboard to use global metrics
function updateImporterLeaderboard() {
    if (!allImporterMetrics) {
        console.log('No metrics data, loading...');
        loadImporterLeaderboard();
        return;
    }
    
    console.log('Updating leaderboard with', allImporterMetrics.length, 'total importers');
    
    // Debug: Show distribution of brand counts
    const brandCountDistribution = {};
    allImporterMetrics.forEach(imp => {
        const count = imp.brandCount || 0;
        brandCountDistribution[count] = (brandCountDistribution[count] || 0) + 1;
    });
    console.log('Brand count distribution:', brandCountDistribution);
    
    // Apply sorting based on current settings
    applySortingToImporters();
    
    // Initial display
    updateImporterTable();
}

// Sort importers function
function sortImporters(field) {
    // If clicking the same field, toggle direction
    if (importerSortField === field) {
        importerSortDirection = importerSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // New field, set default direction
        importerSortField = field;
        importerSortDirection = field === 'brands' ? 'desc' : 'asc'; // Default desc for brands, asc for name
    }
    
    // Update sort indicators
    document.getElementById('importer-name-sort-indicator').textContent = 
        importerSortField === 'name' ? (importerSortDirection === 'asc' ? '▲' : '▼') : '';
    document.getElementById('importer-brands-sort-indicator').textContent = 
        importerSortField === 'brands' ? (importerSortDirection === 'asc' ? '▲' : '▼') : '';
    
    // Apply sorting and update table
    applySortingToImporters();
    updateImporterTable();
}

// Apply sorting to importers
function applySortingToImporters() {
    if (!allImporterMetrics) return;
    
    // First filter to only show importers with brands > 0
    let filteredImporters = allImporterMetrics.filter(imp => imp.brandCount > 0);
    
    // Then sort based on current settings
    filteredImporters.sort((a, b) => {
        let comparison = 0;
        
        if (importerSortField === 'name') {
            const nameA = (a.owner_name || a.operating_name || 'Unknown').toLowerCase();
            const nameB = (b.owner_name || b.operating_name || 'Unknown').toLowerCase();
            comparison = nameA.localeCompare(nameB);
        } else if (importerSortField === 'brands') {
            comparison = a.brandCount - b.brandCount;
        }
        
        return importerSortDirection === 'asc' ? comparison : -comparison;
    });
    
    // Store the sorted result
    globalImporterMetrics = filteredImporters;
    
    // Reset to page 1 when sorting changes
    importersCurrentPage = 1;
    
    console.log(`Sorted ${globalImporterMetrics.length} importers by ${importerSortField} (${importerSortDirection})`);
    if (globalImporterMetrics.length > 0) {
        console.log('Top importers after sorting:', globalImporterMetrics.slice(0, 5).map(i => 
            `${i.owner_name || i.operating_name}: ${i.brandCount} brands`));
    }
}

// Update importer table with pagination
function updateImporterTable() {
    if (!globalImporterMetrics) return;
    
    // Get current settings
    importersPerPage = parseInt(document.getElementById('importers-per-page').value);
    
    const tbody = document.getElementById('importer-leaderboard-body');
    
    if (globalImporterMetrics.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; padding: 30px; color: #666;">
                    No importers with brands found. Most brands are domestic producers.
                </td>
            </tr>
        `;
        return;
    }
    
    const totalImporters = globalImporterMetrics.length;
    const totalPages = Math.ceil(totalImporters / importersPerPage);
    
    // Ensure current page is valid
    if (importersCurrentPage > totalPages) importersCurrentPage = totalPages;
    if (importersCurrentPage < 1) importersCurrentPage = 1;
    
    // Calculate pagination
    const startIndex = (importersCurrentPage - 1) * importersPerPage;
    const endIndex = startIndex + importersPerPage;
    const currentImporters = globalImporterMetrics.slice(startIndex, endIndex);
    
    // Update table
    tbody.innerHTML = currentImporters.map((importer, index) => {
        const globalRank = startIndex + index + 1;
        const rankClass = getRankClass(globalRank);
        
        return `
            <tr>
                <td style="text-align: center;">
                    <div class="leaderboard-rank ${rankClass}">
                        ${globalRank <= 3 ? getRankEmoji(globalRank) : globalRank}
                    </div>
                </td>
                <td style="font-weight: 500;">
                    ${importer.owner_name || importer.operating_name || 'Unknown Importer'}
                    <div class="leaderboard-metric">${importer.permit_number}</div>
                </td>
                <td style="text-align: center;">
                    <strong>${importer.brandCount}</strong>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update pagination controls
    updateImportersPagination(totalPages);
}

// Update importers pagination controls
function updateImportersPagination(totalPages) {
    document.getElementById('importers-page-info').textContent = `Page ${importersCurrentPage} of ${totalPages}`;
    document.getElementById('importers-prev').disabled = importersCurrentPage <= 1;
    document.getElementById('importers-next').disabled = importersCurrentPage >= totalPages;
}

// Change importers page
function changeImportersPage(direction) {
    const totalPages = Math.ceil(globalImporterMetrics.length / importersPerPage);
    
    if (direction === 1 && importersCurrentPage < totalPages) {
        importersCurrentPage++;
    } else if (direction === -1 && importersCurrentPage > 1) {
        importersCurrentPage--;
    }
    
    updateImporterTable();
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('quick-search-modal');
    if (event.target === modal) {
        closeQuickSearch();
    }
};

// Load market insights
async function loadMarketInsights() {
    try {
        const response = await fetch('/api/market_insights');
        const data = await response.json();
        
        if (data.success && data.data) {
            const insights = data.data;
            
            // Update enrichment metrics if elements exist
            const enrichmentRate = document.getElementById('enrichment-rate');
            if (enrichmentRate && insights.overview) {
                enrichmentRate.textContent = `${insights.overview.enrichment_rate}%`;
            }
            
            // Update market concentration if elements exist
            const marketStructure = document.getElementById('market-structure');
            if (marketStructure && insights.market_concentration) {
                marketStructure.textContent = insights.market_concentration.market_structure;
            }
            
            // Store insights for charts
            window.marketInsights = insights;
        }
    } catch (error) {
        console.error('Failed to load market insights:', error);
    }
}

// Handle PDF export - make it global so it can be called from onclick
window.handlePDFExport = async function handlePDFExport() {
    const exportBtn = document.getElementById('export-pdf');
    if (!exportBtn) {
        console.error('Export button not found');
        return;
    }

    try {
        // Show loading state
        exportBtn.disabled = true;
        exportBtn.innerHTML = '⏳ Generating PDF...';

        // Build query parameters based on current date filters if export modal is open
        const params = new URLSearchParams();

        // Check if we have date filters from the export modal
        const dateRangeRadio = document.querySelector('input[name="date-range"]:checked');
        if (dateRangeRadio) {
            const dateRange = dateRangeRadio.value;

            if (dateRange === 'year') {
                const yearSelect = document.getElementById('year-select');
                if (yearSelect && yearSelect.value) {
                    params.append('start_date', `${yearSelect.value}-01-01`);
                    params.append('end_date', `${yearSelect.value}-12-31`);
                }
            } else if (dateRange === 'month') {
                const yearSelect = document.getElementById('year-select');
                const monthSelect = document.getElementById('month-select');
                if (yearSelect && monthSelect && yearSelect.value && monthSelect.value) {
                    const year = yearSelect.value;
                    const month = monthSelect.value;
                    const lastDay = new Date(year, parseInt(month), 0).getDate();
                    params.append('start_date', `${year}-${month}-01`);
                    params.append('end_date', `${year}-${month}-${lastDay.toString().padStart(2, '0')}`);
                }
            } else if (dateRange === 'custom') {
                const startDate = document.getElementById('start-date');
                const endDate = document.getElementById('end-date');
                if (startDate && endDate && startDate.value && endDate.value) {
                    params.append('start_date', startDate.value);
                    params.append('end_date', endDate.value);
                }
            }
            // If 'all' is selected or no valid dates, don't add parameters (gets all data)
        }

        // Build the URL with parameters
        const fetchUrl = params.toString() ? `/api/dashboard/export_pdf?${params.toString()}` : '/api/dashboard/export_pdf';

        // Fetch PDF
        const response = await fetch(fetchUrl);

        if (!response.ok) {
            throw new Error('Failed to generate PDF');
        }

        // Get the blob
        const blob = await response.blob();

        // Create download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `TTB_Market_Insights_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Clean up
        window.URL.revokeObjectURL(downloadUrl);
        
        // Reset button
        exportBtn.disabled = false;
        exportBtn.innerHTML = '📄 Export PDF Report';
        
        // Show success message
        showNotification('PDF report downloaded successfully!', 'success');
        
    } catch (error) {
        console.error('PDF export failed:', error);
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.innerHTML = '📄 Export PDF Report';
        }
        showNotification('Failed to generate PDF report', 'error');
    }
}

// New function to handle PDF export with simple date filter
window.handlePDFExportWithFilter = async function handlePDFExportWithFilter() {
    const exportBtn = document.getElementById('export-pdf');
    if (!exportBtn) {
        console.error('Export button not found');
        return;
    }

    try {
        // Show loading state
        exportBtn.disabled = true;
        exportBtn.innerHTML = '⏳ Generating PDF...';

        // Build query parameters based on the simple date filter
        const params = new URLSearchParams();
        const dateFilter = document.getElementById('pdf-date-filter');
        const startDateInput = document.getElementById('pdf-start-date');
        const endDateInput = document.getElementById('pdf-end-date');

        if (dateFilter && dateFilter.value !== 'all') {
            const filterValue = dateFilter.value;
            const today = new Date();

            if (filterValue === '2025' || filterValue === '2024' || filterValue === '2023') {
                // Year filter
                params.append('start_date', `${filterValue}-01-01`);
                params.append('end_date', `${filterValue}-12-31`);
            } else if (filterValue === 'last30') {
                // Last 30 days
                const startDate = new Date(today);
                startDate.setDate(today.getDate() - 30);
                params.append('start_date', startDate.toISOString().split('T')[0]);
                params.append('end_date', today.toISOString().split('T')[0]);
            } else if (filterValue === 'last90') {
                // Last 90 days
                const startDate = new Date(today);
                startDate.setDate(today.getDate() - 90);
                params.append('start_date', startDate.toISOString().split('T')[0]);
                params.append('end_date', today.toISOString().split('T')[0]);
            } else if (filterValue === 'custom' && startDateInput && endDateInput && startDateInput.value && endDateInput.value) {
                // Custom date range
                params.append('start_date', startDateInput.value);
                params.append('end_date', endDateInput.value);
            }
        }

        // Build the URL with parameters
        const fetchUrl = params.toString() ? `/api/dashboard/export_pdf?${params.toString()}` : '/api/dashboard/export_pdf';

        // Fetch PDF
        const response = await fetch(fetchUrl);

        if (!response.ok) {
            throw new Error('Failed to generate PDF');
        }

        // Get the blob
        const blob = await response.blob();

        // Create download link with date range in filename
        let filename = 'TTB_Market_Insights';
        if (params.get('start_date') && params.get('end_date')) {
            filename += `_${params.get('start_date')}_to_${params.get('end_date')}`;
        } else {
            filename += `_${new Date().toISOString().split('T')[0]}`;
        }
        filename += '.pdf';

        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Clean up
        window.URL.revokeObjectURL(downloadUrl);

        // Reset button
        exportBtn.disabled = false;
        exportBtn.innerHTML = '📄 Export PDF Report';

        // Show success message
        showNotification('PDF report downloaded successfully!', 'success');

    } catch (error) {
        console.error('PDF export failed:', error);
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.innerHTML = '📄 Export PDF Report';
        }
        showNotification('Failed to generate PDF report', 'error');
    }
}

// Setup PDF export functionality
function setupPDFExport() {
    const exportBtn = document.getElementById('export-pdf');
    console.log('Setting up PDF export, button found:', exportBtn);
    if (exportBtn) {
        console.log('Adding click listener to PDF export button');
        // Remove any existing listeners first
        exportBtn.onclick = null;
        exportBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('PDF export button clicked');
            handlePDFExport();
        });
    }

    // Setup date filter change handler
    const dateFilter = document.getElementById('pdf-date-filter');
    if (dateFilter) {
        dateFilter.addEventListener('change', function() {
            const startDateInput = document.getElementById('pdf-start-date');
            const endDateInput = document.getElementById('pdf-end-date');

            if (this.value === 'custom') {
                startDateInput.style.display = 'inline-block';
                endDateInput.style.display = 'inline-block';
            } else {
                startDateInput.style.display = 'none';
                endDateInput.style.display = 'none';
            }
        });
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Close quick search
function closeQuickSearch() {
    const container = document.getElementById('quick-search-container');
    if (container) {
        container.classList.remove('active');
        document.getElementById('search-input').value = '';
        document.getElementById('search-results').innerHTML = '';
    }
}
