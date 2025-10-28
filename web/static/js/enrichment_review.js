/**
 * Enrichment Review Page JavaScript
 * Handles editing, approval, and rejection of enrichment data
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Enrichment review page loaded');
    
    // Initialize review data
    if (window.brandData) {
        console.log('Brand data:', window.brandData);
    }
});

/**
 * Edit field functionality
 */
function editField(fieldName) {
    const item = document.querySelector(`[data-field="${fieldName}"]`);
    if (!item) return;
    
    const displayValue = item.querySelector('.display-value');
    const editValue = item.querySelector('.edit-value');
    
    if (displayValue && editValue) {
        displayValue.style.display = 'none';
        editValue.style.display = 'block';
        
        // Focus on the input
        const input = editValue.querySelector('input, textarea');
        if (input) {
            input.focus();
            input.select();
        }
    }
}

/**
 * Save edited field
 */
function saveField(fieldName) {
    const item = document.querySelector(`[data-field="${fieldName}"]`);
    if (!item) return;
    
    const displayValue = item.querySelector('.display-value');
    const editValue = item.querySelector('.edit-value');
    const input = editValue.querySelector('input, textarea');
    
    if (input && displayValue && editValue) {
        const newValue = input.value.trim();
        
        if (newValue) {
            // Update display based on field type
            updateDisplayValue(fieldName, newValue, displayValue);
            
            // Update the data object
            updateBrandData(fieldName, newValue);
        }
        
        // Return to display mode
        editValue.style.display = 'none';
        displayValue.style.display = 'block';
    }
}

/**
 * Cancel editing
 */
function cancelEdit(fieldName) {
    const item = document.querySelector(`[data-field="${fieldName}"]`);
    if (!item) return;
    
    const displayValue = item.querySelector('.display-value');
    const editValue = item.querySelector('.edit-value');
    
    if (displayValue && editValue) {
        editValue.style.display = 'none';
        displayValue.style.display = 'block';
    }
}

/**
 * Update display value after editing
 */
function updateDisplayValue(fieldName, newValue, displayElement) {
    switch (fieldName) {
        case 'website':
            const strong = displayElement.querySelector('strong');
            if (strong) {
                strong.textContent = newValue;
            }
            break;
            
        case 'founders':
            // Parse founders from textarea (one per line)
            const founderNames = newValue.split('\n').filter(name => name.trim());
            const foundersHtml = founderNames.map(name => `
                <div class="founder-item">
                    <div class="founder-name">${name.trim()}</div>
                    <div class="founder-details">
                        <span class="confidence-badge">Manual Edit</span>
                    </div>
                </div>
            `).join('');
            
            displayElement.innerHTML = foundersHtml;
            break;
    }
}

/**
 * Update brand data object
 */
function updateBrandData(fieldName, newValue) {
    if (!window.brandData) return;
    
    switch (fieldName) {
        case 'website':
            if (window.brandData.enrichment.website) {
                window.brandData.enrichment.website.domain = newValue;
                window.brandData.enrichment.website.url = `https://${newValue}`;
            }
            break;
            
        case 'founders':
            const founderNames = newValue.split('\n').filter(name => name.trim());
            window.brandData.enrichment.founders = founderNames.map(name => ({
                name: name.trim(),
                confidence: 1.0,
                source: 'manual_edit'
            }));
            break;
    }
    
    console.log('Updated brand data:', window.brandData);
}

/**
 * Approve enrichment and save to brand profile
 */
async function approveEnrichment() {
    showLoading('Approving enrichment data...');
    
    try {
        const reviewNotes = document.getElementById('review-notes').value.trim();
        
        const payload = {
            brand_name: window.brandData.name,
            enrichment_data: window.brandData.enrichment,
            action: 'approve',
            notes: reviewNotes
        };
        
        const response = await fetch('/enrichment/review_action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessMessage('Enrichment approved and saved to brand profile!');
            
            // Redirect to brand detail page after a brief delay
            setTimeout(() => {
                window.location.href = `/brand/${encodeURIComponent(window.brandData.name)}`;
            }, 2000);
        } else {
            throw new Error(result.error || 'Failed to approve enrichment');
        }
        
    } catch (error) {
        console.error('Approval error:', error);
        hideLoading();
        alert(`Error approving enrichment: ${error.message}`);
    }
}

/**
 * Reject enrichment
 */
async function rejectEnrichment() {
    if (!confirm('Are you sure you want to reject this enrichment data? It will not be saved to the brand profile.')) {
        return;
    }
    
    showLoading('Rejecting enrichment data...');
    
    try {
        const reviewNotes = document.getElementById('review-notes').value.trim();
        
        const payload = {
            brand_name: window.brandData.name,
            enrichment_data: window.brandData.enrichment,
            action: 'reject',
            notes: reviewNotes
        };
        
        const response = await fetch('/enrichment/review_action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessMessage('Enrichment rejected. No data was saved.');
            
            // Redirect to brands page after a brief delay
            setTimeout(() => {
                window.location.href = '/brands';
            }, 2000);
        } else {
            throw new Error(result.error || 'Failed to reject enrichment');
        }
        
    } catch (error) {
        console.error('Rejection error:', error);
        hideLoading();
        alert(`Error rejecting enrichment: ${error.message}`);
    }
}

/**
 * Re-search for enrichment data
 */
async function researchBrand() {
    if (!confirm('This will start a new enrichment search. Continue?')) {
        return;
    }
    
    showLoading('Starting new enrichment search...');
    
    try {
        const payload = {
            brand_name: window.brandData.name,
            class_type: window.brandData.originalData.class_types?.[0] || '',
            skip_cache: true
        };
        
        const response = await fetch('/enrichment/enrich_brand', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Reload the page with new enrichment data
            window.location.reload();
        } else {
            throw new Error(result.error || 'Re-search failed');
        }
        
    } catch (error) {
        console.error('Re-search error:', error);
        hideLoading();
        alert(`Error re-searching: ${error.message}`);
    }
}

/**
 * Show loading overlay
 */
function showLoading(message) {
    const overlay = document.getElementById('loading-overlay');
    const messageEl = document.getElementById('loading-message');
    
    if (messageEl) {
        messageEl.textContent = message;
    }
    
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Show success message
 */
function showSuccessMessage(message) {
    const messageEl = document.getElementById('loading-message');
    const spinner = document.querySelector('.loading-spinner');
    
    if (spinner) {
        spinner.style.display = 'none';
    }
    
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.parentElement.querySelector('h3').textContent = 'Success!';
        messageEl.parentElement.querySelector('h3').style.color = 'var(--green-600)';
    }
}

/**
 * Keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter = Approve
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        approveEnrichment();
    }
    
    // Escape = Cancel any edit
    if (e.key === 'Escape') {
        const activeEdit = document.querySelector('.edit-value[style*="block"]');
        if (activeEdit) {
            const fieldName = activeEdit.closest('[data-field]').dataset.field;
            cancelEdit(fieldName);
        }
    }
});

/**
 * Auto-save draft notes
 */
let notesTimeout;
document.getElementById('review-notes')?.addEventListener('input', function() {
    clearTimeout(notesTimeout);
    notesTimeout = setTimeout(() => {
        const notes = this.value;
        localStorage.setItem(`review_notes_${window.brandData.name}`, notes);
    }, 1000);
});

/**
 * Load saved draft notes
 */
document.addEventListener('DOMContentLoaded', function() {
    const savedNotes = localStorage.getItem(`review_notes_${window.brandData?.name}`);
    const notesField = document.getElementById('review-notes');
    
    if (savedNotes && notesField && !notesField.value) {
        notesField.value = savedNotes;
    }
});

/**
 * Multi-Choice Website Selection Functions
 */

/**
 * Select a website option from multi-choice
 */
async function selectWebsiteOption(brandName, selectedUrl, selectedRank) {
    try {
        showLoading(`Applying selection and learning from choice ${selectedRank}...`);
        
        // Get all options from the page
        const optionElements = document.querySelectorAll('.website-option');
        const allOptions = Array.from(optionElements).map(el => ({
            rank: parseInt(el.dataset.rank),
            url: el.querySelector('.option-domain a').href,
            domain: el.querySelector('.option-domain a').textContent,
            final_confidence: parseFloat(el.querySelector('.confidence-badge').textContent) / 100
        }));
        
        // Create brand context
        const brandContext = {
            countries: window.brandData?.originalData?.countries || [],
            product_types: window.brandData?.originalData?.class_types || [],
            sku_count: window.brandData?.originalData?.sku_count || 0
        };
        
        const response = await fetch('/enrichment/select_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                selected_url: selectedUrl,
                selected_rank: selectedRank,
                all_options: allOptions,
                brand_context: brandContext,
                user_feedback: 'selected'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessMessage(`Website selected! Learning from your choice to improve future suggestions.`);
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            throw new Error(data.error || 'Failed to process selection');
        }
        
    } catch (error) {
        console.error('Selection error:', error);
        hideLoading();
        alert(`Error processing selection: ${error.message}`);
    }
}

/**
 * Reject all website options
 */
async function rejectAllOptions(brandName) {
    const reason = prompt('Why are none of these options correct? (This helps improve the AI):', 
                         'None of these websites are related to this brand');
    
    if (!reason) return;
    
    try {
        showLoading('Recording rejection and learning from feedback...');
        
        // Get all options from the page
        const optionElements = document.querySelectorAll('.website-option');
        const allOptions = Array.from(optionElements).map(el => ({
            rank: parseInt(el.dataset.rank),
            url: el.querySelector('.option-domain a').href,
            domain: el.querySelector('.option-domain a').textContent,
            final_confidence: parseFloat(el.querySelector('.confidence-badge').textContent) / 100
        }));
        
        // Create brand context
        const brandContext = {
            countries: window.brandData?.originalData?.countries || [],
            product_types: window.brandData?.originalData?.class_types || [],
            sku_count: window.brandData?.originalData?.sku_count || 0
        };
        
        const response = await fetch('/enrichment/select_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                selected_url: null,
                selected_rank: 0,
                all_options: allOptions,
                brand_context: brandContext,
                user_feedback: 'rejected_all',
                rejection_reason: reason
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessMessage(`Rejection recorded. The AI will learn from this feedback to avoid similar suggestions.`);
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            throw new Error(data.error || 'Failed to process rejection');
        }
        
    } catch (error) {
        console.error('Rejection error:', error);
        hideLoading();
        alert(`Error processing rejection: ${error.message}`);
    }
}

/**
 * Show manual input option
 */
function showManualInput(brandName) {
    const url = prompt('Enter the correct website URL for this brand:', 'https://');
    
    if (url && url !== 'https://' && url.includes('.')) {
        // For now, redirect to brand detail page with manual input
        alert('Please use the brand detail page to add manual websites. Redirecting...');
        window.location.href = `/brand/${encodeURIComponent(brandName)}`;
    }
}