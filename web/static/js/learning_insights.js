// Learning Insights Dashboard JavaScript

let learningData = null;

// Load insights on page load
document.addEventListener('DOMContentLoaded', function() {
    loadLearningInsights();
    loadRescoreStats();
});

async function loadLearningInsights() {
    try {
        const response = await fetch('/learning_insights?format=json');
        const data = await response.json();
        
        if (data.success) {
            learningData = data.insights;
            updateMetrics(data.insights);
            updatePatterns(data.insights);
            updateEvents(data.insights);
            updateKnowledge(data.insights);
        } else {
            console.error('Failed to load learning insights:', data.error);
            showError('Failed to load learning insights');
        }
    } catch (error) {
        console.error('Error loading learning insights:', error);
        showError('Error loading learning insights');
    }
}

function updateMetrics(insights) {
    // Update main metrics
    document.getElementById('total-events').textContent = insights.total_learning_events || 0;
    document.getElementById('success-rate').textContent = formatPercentage(insights.success_rate);
    document.getElementById('confidence-accuracy').textContent = formatPercentage(insights.confidence_accuracy);
    document.getElementById('patterns-learned').textContent = insights.total_patterns || 0;
    
    // Update performance stats
    document.getElementById('verified-count').textContent = insights.verified_count || 0;
    document.getElementById('rejected-count').textContent = insights.rejected_count || 0;
    document.getElementById('flagged-count').textContent = insights.flagged_count || 0;
    document.getElementById('avg-confidence').textContent = (insights.average_confidence || 0).toFixed(2);
    document.getElementById('learning-rate').textContent = (insights.learning_rate || 0).toFixed(2);
    
    // Update industry knowledge
    const brandsByType = insights.brands_by_type || {};
    document.getElementById('spirits-brands').textContent = brandsByType.spirits || 0;
    document.getElementById('wine-brands').textContent = brandsByType.wine || 0;
    document.getElementById('beer-brands').textContent = brandsByType.beer || 0;
    document.getElementById('industry-patterns').textContent = insights.industry_patterns || 0;
    document.getElementById('domain-patterns').textContent = insights.domain_pattern_count || 0;
}

function updatePatterns(insights) {
    const container = document.getElementById('patterns-container');
    const patterns = insights.top_patterns || [];
    
    if (patterns.length === 0) {
        container.innerHTML = '<p class="no-data">No patterns learned yet</p>';
        return;
    }
    
    container.innerHTML = patterns.map(pattern => `
        <div class="pattern-item">
            <div class="pattern-domain">${escapeHtml(pattern.pattern)}</div>
            <div class="pattern-confidence">Confidence: ${(pattern.confidence * 100).toFixed(0)}%</div>
            <div class="pattern-matches">${pattern.matches} matches</div>
        </div>
    `).join('');
}

function updateEvents(insights) {
    const tbody = document.getElementById('events-tbody');
    const events = insights.recent_events || [];
    
    if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">No learning events recorded yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = events.map(event => {
        const actionClass = getActionClass(event.action);
        const impactClass = getImpactClass(event.impact);
        
        return `
            <tr>
                <td>${formatTimestamp(event.timestamp)}</td>
                <td>${escapeHtml(event.brand_name)}</td>
                <td><span class="event-action ${actionClass}">${event.action}</span></td>
                <td>${escapeHtml(event.domain || '-')}</td>
                <td>${(event.confidence * 100).toFixed(0)}%</td>
                <td><span class="${impactClass}">${formatImpact(event.impact)}</span></td>
            </tr>
        `;
    }).join('');
}

function updateKnowledge(insights) {
    // Update top search terms
    const searchTermsContainer = document.getElementById('top-search-terms');
    const searchTerms = insights.top_search_terms || [];
    
    if (searchTerms.length === 0) {
        searchTermsContainer.innerHTML = '<p class="no-data">No search terms tracked yet</p>';
    } else {
        searchTermsContainer.innerHTML = searchTerms.map(term => `
            <div class="term-item">
                <span class="term-text">${escapeHtml(term.term)}</span>
                <span class="term-count">${term.count} uses</span>
            </div>
        `).join('');
    }
    
    // Update false positive domains
    const falsePositivesContainer = document.getElementById('false-positive-domains');
    const falsePositives = insights.false_positive_domains || [];
    
    if (falsePositives.length === 0) {
        falsePositivesContainer.innerHTML = '<p class="no-data">No false positives identified yet</p>';
    } else {
        falsePositivesContainer.innerHTML = falsePositives.map(domain => `
            <div class="domain-item">
                <span class="domain-text">${escapeHtml(domain.domain)}</span>
                <span class="domain-status">Avoided</span>
            </div>
        `).join('');
    }
    
    // Update confidence calibration
    const calibrationContainer = document.getElementById('confidence-calibration');
    const calibration = insights.confidence_calibration || {};
    
    calibrationContainer.innerHTML = `
        <div class="calibration-item">
            <span>High Confidence (>80%)</span>
            <div class="calibration-bar">
                <div class="calibration-fill" style="width: ${calibration.high_accuracy || 0}%"></div>
            </div>
            <span>${calibration.high_accuracy || 0}%</span>
        </div>
        <div class="calibration-item">
            <span>Medium (50-80%)</span>
            <div class="calibration-bar">
                <div class="calibration-fill" style="width: ${calibration.medium_accuracy || 0}%"></div>
            </div>
            <span>${calibration.medium_accuracy || 0}%</span>
        </div>
        <div class="calibration-item">
            <span>Low (<50%)</span>
            <div class="calibration-bar">
                <div class="calibration-fill" style="width: ${calibration.low_accuracy || 0}%"></div>
            </div>
            <span>${calibration.low_accuracy || 0}%</span>
        </div>
    `;
}

// Action functions
async function exportLearningData() {
    try {
        // Create a temporary link to download the export
        const link = document.createElement('a');
        link.href = '/learning_insights/export';
        link.download = `learning_data_export_${new Date().toISOString().slice(0,10)}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showSuccess('Learning data export started. ZIP file with CSV files will download shortly.');
    } catch (error) {
        console.error('Error exporting learning data:', error);
        showError('Error exporting learning data');
    }
}

async function recalculateConfidence() {
    if (!confirm('This will recalculate confidence scores for all websites based on current learning patterns. Continue?')) {
        return;
    }
    
    try {
        showLoading('Recalculating confidence scores...');
        
        const response = await fetch('/recalculate_all_confidence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Updated ${data.updated_count} confidence scores`);
            loadLearningInsights(); // Reload the insights
        } else {
            showError('Failed to recalculate confidence scores');
        }
    } catch (error) {
        console.error('Error recalculating confidence:', error);
        showError('Error recalculating confidence scores');
    } finally {
        hideLoading();
    }
}

async function clearLearningCache() {
    if (!confirm('This will clear the learning cache but preserve learning events. Continue?')) {
        return;
    }
    
    try {
        const response = await fetch('/clear_learning_cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Learning cache cleared successfully');
            loadLearningInsights(); // Reload the insights
        } else {
            showError('Failed to clear learning cache');
        }
    } catch (error) {
        console.error('Error clearing cache:', error);
        showError('Error clearing learning cache');
    }
}

async function refreshInsights() {
    showLoading('Refreshing insights...');
    await loadLearningInsights();
    hideLoading();
    showSuccess('Insights refreshed successfully');
}

// Helper functions
function formatPercentage(value) {
    if (value === null || value === undefined) return '0%';
    return `${(value * 100).toFixed(1)}%`;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function getActionClass(action) {
    switch (action) {
        case 'verified':
            return 'action-verified';
        case 'rejected':
            return 'action-rejected';
        case 'flagged':
            return 'action-flagged';
        default:
            return '';
    }
}

function getImpactClass(impact) {
    if (impact > 0) return 'impact-positive';
    if (impact < 0) return 'impact-negative';
    return 'impact-neutral';
}

function formatImpact(impact) {
    if (impact > 0) return `+${impact.toFixed(2)}`;
    if (impact < 0) return impact.toFixed(2);
    return '0.00';
}

// Notification functions
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

function showLoading(message) {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-overlay';
    loadingDiv.className = 'loading-overlay';
    loadingDiv.innerHTML = `
        <div class="loading-content">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
    document.body.appendChild(loadingDiv);
}

function hideLoading() {
    const loadingDiv = document.getElementById('loading-overlay');
    if (loadingDiv) {
        document.body.removeChild(loadingDiv);
    }
}

// Add notification styles
const style = document.createElement('style');
style.textContent = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        background: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transform: translateX(400px);
        transition: transform 0.3s ease;
        z-index: 1000;
    }
    
    .notification.show {
        transform: translateX(0);
    }
    
    .notification-success {
        background: #10b981;
        color: white;
    }
    
    .notification-error {
        background: #ef4444;
        color: white;
    }
    
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999;
    }
    
    .loading-content {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        text-align: center;
    }
    
    .no-data {
        text-align: center;
        color: var(--text-secondary);
        padding: 1rem;
        font-style: italic;
    }
`;
document.head.appendChild(style);

// Batch Re-scoring Functions
async function loadRescoreStats() {
    try {
        const response = await fetch('/enrichment/rescore_stats');
        const data = await response.json();
        
        document.getElementById('total-websites-stat').textContent = data.total_websites || 0;
        document.getElementById('category-mismatches-stat').textContent = data.potential_category_mismatches || 0;
        
        const totalPatterns = (data.domain_patterns || 0) + (data.relevance_patterns || 0) + (data.strategy_patterns || 0);
        document.getElementById('patterns-available-stat').textContent = totalPatterns;
        
    } catch (error) {
        console.error('Error loading rescore stats:', error);
        document.getElementById('total-websites-stat').textContent = 'Error';
        document.getElementById('category-mismatches-stat').textContent = 'Error';
        document.getElementById('patterns-available-stat').textContent = 'Error';
    }
}

async function startBatchRescore() {
    if (!confirm('This will re-score all existing website matches with current learning data. This may take a few moments. Continue?')) {
        return;
    }
    
    const btn = document.getElementById('rescore-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Processing...';
    
    try {
        const response = await fetch('/enrichment/batch_rescore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showRescoreResults(data);
            showSuccess(`Successfully re-scored ${data.updated} out of ${data.total_websites} websites`);
        } else {
            showError(`Failed to re-score websites: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error during batch re-scoring:', error);
        showError('Error during batch re-scoring');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
        // Reload stats
        loadRescoreStats();
    }
}

function showRescoreResults(data) {
    const resultsDiv = document.getElementById('rescore-results');
    const summaryDiv = document.getElementById('rescore-summary');
    const updatesDiv = document.getElementById('rescore-updates');
    
    resultsDiv.style.display = 'block';
    
    // Show summary
    summaryDiv.innerHTML = `
        <div class="rescore-summary-stats">
            <div class="stat-item">
                <span class="stat-label">Total Websites:</span>
                <span class="stat-value">${data.total_websites}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Updated:</span>
                <span class="stat-value">${data.updated}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">No Change:</span>
                <span class="stat-value">${data.total_websites - data.updated}</span>
            </div>
        </div>
    `;
    
    // Show individual updates
    if (data.updates && data.updates.length > 0) {
        let updatesHtml = '<h5>Top Changes (by magnitude):</h5>';
        updatesHtml += '<div class="rescore-updates-list">';
        
        data.updates.forEach(update => {
            const changeClass = update.change > 0 ? 'positive' : 'negative';
            const mismatchBadge = update.category_mismatch ? '<span class="badge badge-warning">Category Mismatch</span>' : '';
            const classTypes = update.class_types.length > 0 ? `<span class="class-types">${update.class_types.join(', ')}</span>` : '';
            
            updatesHtml += `
                <div class="update-item ${changeClass}">
                    <div class="update-brand">
                        <strong>${update.brand_name}</strong> ${classTypes}
                    </div>
                    <div class="update-domain">${update.domain}</div>
                    <div class="update-confidence">
                        <span class="old-confidence">${update.old_confidence}</span>
                        →
                        <span class="new-confidence">${update.new_confidence}</span>
                        <span class="confidence-change ${changeClass}">(${update.change > 0 ? '+' : ''}${update.change})</span>
                        ${mismatchBadge}
                    </div>
                </div>
            `;
        });
        
        updatesHtml += '</div>';
        
        if (data.updates.length === 50) {
            updatesHtml += '<p class="update-note">Showing top 50 changes. Check individual brand pages for all updates.</p>';
        }
        
        updatesDiv.innerHTML = updatesHtml;
    } else {
        updatesDiv.innerHTML = '<p>No significant confidence changes detected.</p>';
    }
}