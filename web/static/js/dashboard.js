document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    loadMarketInsights();
    setupCharts();
    loadRecentActivity();
    loadTopBrands();
    loadImporterLeaderboard();
    setTimeout(setupPDFExport, 100);
    setInterval(loadDashboardData, 300000);
});

// Load main dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch('/get_database_stats');
        const stats = await response.json();

        animateCounter('dashboard-brands', stats.total_brands || 0);
        animateCounter('dashboard-skus', stats.total_skus || 0);
        animateCounter('dashboard-importers', stats.total_importers || 0);

        // Real enriched percentage
        var totalBrands = stats.total_brands || 0;
        var enriched = stats.brands_with_websites || 0;
        var pct = totalBrands > 0 ? Math.round((enriched / totalBrands) * 100) : 0;
        var enrichedEl = document.getElementById('dashboard-enriched');
        var detailEl = document.getElementById('enriched-detail');
        if (enrichedEl) enrichedEl.textContent = pct + '%';
        if (detailEl) detailEl.textContent = enriched.toLocaleString() + ' brands with websites';

        document.getElementById('last-updated').textContent =
            'Updated ' + new Date().toLocaleTimeString();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
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
        
        
        if (!data.brands || data.brands.length === 0) {
            document.getElementById('countryChart').parentElement.innerHTML = 
                '<p class="no-data">No brand data available</p>';
            return;
        }
        
        // Store brands data globally
        brandsData = data.brands;
        
        
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
                    <div class="activity-dot"></div>
                    <div class="activity-content">
                        <div class="activity-title">No recent activity</div>
                        <div class="activity-time">Upload files to see activity</div>
                    </div>
                </div>
            `;
            return;
        }

        const recentFiles = data.files.slice(0, 5);
        activityList.innerHTML = recentFiles.map(file => `
            <div class="activity-item">
                <div class="activity-dot"></div>
                <div class="activity-content">
                    <div class="activity-title">${file.filename}</div>
                    <div class="activity-time">${file.created} &middot; ${file.rows} records</div>
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

// Get rank display text
function getRankEmoji(rank) {
    return rank;
}

// Updated updateImporterLeaderboard to use global metrics
function updateImporterLeaderboard() {
    if (!allImporterMetrics) {
        loadImporterLeaderboard();
        return;
    }
    
    
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

// Handle PDF export with date filter
window.handlePDFExportWithFilter = async function handlePDFExportWithFilter() {
    const exportBtn = document.getElementById('export-pdf');
    if (!exportBtn) {
        console.error('Export button not found');
        return;
    }

    try {
        // Show loading state
        exportBtn.disabled = true;
        exportBtn.textContent = 'Generating PDF...';

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
        exportBtn.textContent = 'Export PDF';

        // Show success message
        showNotification('PDF report downloaded successfully!', 'success');

    } catch (error) {
        console.error('PDF export failed:', error);
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.textContent = 'Export PDF';
        }
        showNotification('Failed to generate PDF report', 'error');
    }
}

// Setup PDF date filter toggle
function setupPDFExport() {
    var dateFilter = document.getElementById('pdf-date-filter');
    if (dateFilter) {
        dateFilter.addEventListener('change', function() {
            var startDateInput = document.getElementById('pdf-start-date');
            var endDateInput = document.getElementById('pdf-end-date');
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

