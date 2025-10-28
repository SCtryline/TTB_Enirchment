document.addEventListener('DOMContentLoaded', function() {
    // Note: checkBrandCache will be called after all functions are defined
    
    // Helper function for safe JSON parsing
    window.safeJsonParse = function(response) {
        if (!response.ok) {
            if (response.status === 400) {
                throw new Error(`Bad request (400): Please check that the brand name is valid and try again`);
            } else if (response.status === 503) {
                throw new Error(`Service unavailable (503): The enrichment system is temporarily unavailable`);
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Response is not JSON');
        }
        
        return response.text().then(text => {
            if (!text.trim()) {
                throw new Error('Empty response from server');
            }
            
            try {
                return JSON.parse(text);
            } catch (parseError) {
                console.error('JSON parse error:', parseError);
                console.error('Response text:', text.substring(0, 200) + '...');
                throw new Error('Invalid JSON response from server');
            }
        });
    };
    
    // View toggle functionality
    window.toggleView = function(viewType) {
        const tableView = document.getElementById('skus-table');
        const gridView = document.getElementById('skus-grid');
        const tableBtn = document.querySelector('[onclick="toggleView(\'table\')"]');
        const gridBtn = document.querySelector('[onclick="toggleView(\'grid\')"]');
        
        if (viewType === 'table') {
            tableView.style.display = 'block';
            gridView.style.display = 'none';
            tableBtn.classList.add('active');
            gridBtn.classList.remove('active');
        } else {
            tableView.style.display = 'none';
            gridView.style.display = 'block';
            gridBtn.classList.add('active');
            tableBtn.classList.remove('active');
        }
    };
    
    // Export functionality
    window.exportBrandData = function() {
        const brandName = document.querySelector('.brand-name').textContent;
        const exportUrl = `/export_brand_detail/${encodeURIComponent(brandName)}`;
        
        // Create a temporary link to trigger download
        const link = document.createElement('a');
        link.href = exportUrl;
        link.download = `${brandName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_details.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };
    
    // Add smooth scrolling to sections
    function addSmoothScrolling() {
        const skusSection = document.querySelector('.skus-section');
        if (skusSection) {
            // Add scroll-to-skus functionality if needed
            const scrollToSkus = document.getElementById('scroll-to-skus');
            if (scrollToSkus) {
                scrollToSkus.addEventListener('click', function(e) {
                    e.preventDefault();
                    skusSection.scrollIntoView({ behavior: 'smooth' });
                });
            }
        }
    }
    
    // Initialize smooth scrolling
    addSmoothScrolling();
    
    // Add table row hover effects
    const skuRows = document.querySelectorAll('.sku-row');
    skuRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'var(--gray-50)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    // Add keyboard navigation for view toggle
    document.addEventListener('keydown', function(e) {
        if (e.altKey && e.key === 't') {
            e.preventDefault();
            toggleView('table');
        } else if (e.altKey && e.key === 'g') {
            e.preventDefault();
            toggleView('grid');
        }
    });
    
    // Add tooltips for truncated text
    function addTooltips() {
        const elements = document.querySelectorAll('[title]');
        elements.forEach(element => {
            if (element.scrollWidth > element.clientWidth) {
                // Element is truncated, tooltip is useful
                element.style.cursor = 'help';
            }
        });
    }
    
    // Initialize tooltips
    addTooltips();
    
    // Add progress indicator functions
    window.showEnrichmentProgress = function() {
        // Create progress modal
        const modal = document.createElement('div');
        modal.id = 'enrichment-progress';
        modal.className = 'enrichment-modal';
        modal.innerHTML = `
            <div class="progress-content">
                <div class="progress-header">
                    <h3>🔍 Searching for Website</h3>
                    <p>This may take 45-90 seconds due to anti-detection measures...</p>
                </div>
                <div class="progress-steps">
                    <div class="step active" data-step="1">
                        <span class="step-icon">🔎</span>
                        <span class="step-text">Initializing search...</span>
                    </div>
                    <div class="step" data-step="2">
                        <span class="step-icon">🕵️</span>
                        <span class="step-text">Applying stealth measures...</span>
                    </div>
                    <div class="step" data-step="3">
                        <span class="step-icon">🌐</span>
                        <span class="step-text">Searching web...</span>
                    </div>
                    <div class="step" data-step="4">
                        <span class="step-icon">🧠</span>
                        <span class="step-text">Analyzing results...</span>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                <div class="progress-text">Step 1 of 4</div>
                <button onclick="cancelEnrichment()" class="cancel-btn">Cancel</button>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Start progress simulation
        startProgressSimulation();
    };
    
    window.hideEnrichmentProgress = function() {
        const modal = document.getElementById('enrichment-progress');
        if (modal) {
            document.body.removeChild(modal);
        }
    };
    
    window.cancelEnrichment = function() {
        // For now, just hide the modal (could implement actual cancellation)
        hideEnrichmentProgress();
        const btn = document.querySelector('.btn-secondary[onclick*="searchForWebsite"]');
        if (btn) {
            btn.textContent = '🔍 Search for Website';
            btn.disabled = false;
        }
    };
    
    let progressInterval;
    window.startProgressSimulation = function() {
        let currentStep = 1;
        let progress = 0;
        
        progressInterval = setInterval(() => {
            progress += Math.random() * 15 + 5; // Random progress 5-20%
            
            if (progress >= 100) {
                progress = 100;
                clearInterval(progressInterval);
            }
            
            // Update progress bar
            const progressFill = document.getElementById('progress-fill');
            if (progressFill) {
                progressFill.style.width = progress + '%';
            }
            
            // Update steps
            const expectedStep = Math.min(4, Math.floor(progress / 25) + 1);
            if (expectedStep > currentStep) {
                // Complete previous step
                const prevStep = document.querySelector(`[data-step="${currentStep}"]`);
                if (prevStep) {
                    prevStep.classList.remove('active');
                    prevStep.classList.add('completed');
                }
                
                // Activate next step
                const nextStep = document.querySelector(`[data-step="${expectedStep}"]`);
                if (nextStep) {
                    nextStep.classList.add('active');
                }
                
                currentStep = expectedStep;
                
                // Update progress text
                const progressText = document.querySelector('.progress-text');
                if (progressText) {
                    progressText.textContent = `Step ${currentStep} of 4`;
                }
            }
        }, 2000); // Update every 2 seconds
    };
    
    // Cache checking function
    window.checkBrandCache = function() {
        const brandNameElement = document.querySelector('.brand-name');
        if (!brandNameElement) return;
        
        const brandName = brandNameElement.textContent;
        
        // Only check if brand doesn't already have website
        const websiteCard = document.querySelector('.website-card:not(.add-website)');
        if (websiteCard) return; // Brand already has website
        
        // Check cache
        fetch('/check_brand_cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.cached && data.data && data.data.website) {
                showCachedResult(data.data);
            }
        })
        .catch(error => {
            console.error('Error checking cache:', error);
        });
    };
    
    window.showCachedResult = function(cacheData) {
        // DISABLED: Using unified website card instead of separate cached display
        console.log('Cached website data available but using unified display:', cacheData);
        return; // Exit early - unified website card handles all display
        
        const addWebsiteCard = document.querySelector('.add-website');
        if (!addWebsiteCard) return;
        
        const website = cacheData.website;
        const confidence = website.confidence || 0;
        const confidenceClass = confidence < 0.5 ? 'low' : confidence < 0.8 ? 'medium' : 'high';
        
        // Replace add website form with cached result
        addWebsiteCard.innerHTML = `
            <div class="info-card-header">
                <h2>🌐 Cached Website Found</h2>
                <div class="status-indicator cached">
                    <span class="status-text">Cached Result</span>
                </div>
            </div>
            <div class="cached-website-info">
                <div class="website-main">
                    <div class="website-url">
                        <a href="${website.url}" target="_blank" class="website-link">
                            <span class="website-icon">🔗</span>
                            <span class="website-domain">${website.domain}</span>
                            <span class="external-icon">↗</span>
                        </a>
                    </div>
                    <div class="confidence-indicator">
                        <span class="info-label">Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill ${confidenceClass}" style="width: ${confidence * 100}%"></div>
                        </div>
                        <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                    </div>
                </div>
                <div class="cached-actions">
                    <button onclick="acceptCachedResult('${website.url}', ${confidence})" class="btn btn-primary">
                        ✅ Accept This Website
                    </button>
                    <button onclick="searchFresh()" class="btn btn-secondary">
                        🔍 Search Fresh
                    </button>
                    <p class="cache-note">
                        Source: ${cacheData.source} (${cacheData.cache_age})
                    </p>
                </div>
            </div>
        `;
    };
    
    window.acceptCachedResult = function(url, confidence) {
        const brandName = document.querySelector('.brand-name').textContent;
        
        fetch('/add_brand_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                website_url: url,
                confidence: confidence,
                source: 'cache_accepted'
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                alert('Website accepted and saved!');
                location.reload();
            } else {
                alert('Error saving website: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving website');
        });
    };
    
    window.searchFresh = function() {
        // Hide cached result and show search in progress
        const brandName = document.querySelector('.brand-name').textContent;
        searchForWebsite(brandName);
    };
    
    // Print functionality
    window.printBrandDetails = function() {
        window.print();
    };
    
    // Website verification functions
    window.verifyWebsite = function(brandName, verified) {
        const message = verified ? 'verify' : 'reject';
        
        if (!confirm(`Are you sure you want to ${message} this website?`)) {
            return;
        }
        
        // Show loading state
        const buttons = document.querySelectorAll('.verification-actions button');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.6';
        });
        
        fetch('/verify_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                brand_name: brandName,
                verified: verified
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // Restore button states on error
                buttons.forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                });
                showNotification(data.error || 'Failed to update website status', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Restore button states on error
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
            });
            showNotification('Network error occurred', 'error');
        });
    };
    
    // Add website function
    window.addWebsite = function(event, brandName) {
        event.preventDefault();
        
        const form = event.target;
        const url = form.url.value;
        const confidence = parseInt(form.confidence.value) / 100;
        const source = form.source.value || 'manual';
        
        // Get brand name from form data attribute if not provided
        const actualBrandName = brandName || form.dataset.brandName;
        
        fetch('/manual_url_training', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: actualBrandName,
                website_url: url,
                confidence: confidence,
                source: source,
                notes: 'Added via manual form'
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                alert('Website added successfully!');
                location.reload();
            } else {
                alert('Error adding website: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error adding website');
        });
    };
    
    // Manual URL training function - integrates with agentic learning
    window.addManualURL = function(event, brandName) {
        event.preventDefault();
        
        const form = event.target;
        const url = form.url.value;
        const confidence = parseInt(form.confidence.value) / 100;
        const source = form.source.value || 'manual';
        const notes = form.notes.value || '';
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '🧠 Training System...';
        submitBtn.disabled = true;
        
        fetch('/manual_url_training', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                website_url: url,
                confidence: confidence,
                source: source,
                notes: notes,
                training_method: 'manual_input'
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                // Show success message with learning details
                const learningInfo = data.learning_applied ? 
                    `\n🧠 Learning Applied: ${data.patterns_learned} patterns learned from this input!` : '';
                
                alert(`✅ Manual URL added and system trained successfully!${learningInfo}\n\nThe system will now be better at finding similar websites.`);
                
                // Close the manual override form
                const details = form.closest('details');
                if (details) details.open = false;
                
                // Reload to show the new website
                location.reload();
            } else {
                alert('❌ Error training system: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ Error submitting manual URL for training');
        })
        .finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    };
    
    // Search for website function
    window.searchForWebsite = function(brandName) {
        if (!confirm('This will search for the brand website using advanced anti-detection measures. This may take 1-2 minutes due to security protocols. Continue?')) {
            return;
        }
        
        // Show loading state
        const btn = document.querySelector('.btn-secondary[onclick*="searchForWebsite"]');
        const originalText = btn.textContent;
        btn.textContent = '🔍 Searching...';
        btn.disabled = true;
        
        // Show progress indicator
        showEnrichmentProgress();
        
        // Create fetch with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout (2 minutes)
        
        fetch('/enrichment/enrich_brand', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                search_website: true,
                search_founders: false,
                search_linkedin: false,
                search_apollo: false
            }),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            return safeJsonParse(response);
        })
        .then(data => {
            clearInterval(progressInterval);
            hideEnrichmentProgress();
            
            // Check if multi-choice selection is needed
            if (data.success && data.needs_website_selection && data.website_options) {
                console.log('🎯 Low confidence detected - showing multi-choice options');
                showWebsiteOptions(data.website_options);
                btn.textContent = originalText;
                btn.disabled = false;
                return;
            }
            
            // Handle normal enrichment results
            if (data.success && data.enrichment_data && data.enrichment_data.website && data.enrichment_data.website.domain) {
                alert('Website found! Refreshing page...');
                location.reload();
            } else if (data.success && data.enrichment_data && data.enrichment_data.website && !data.enrichment_data.website.domain) {
                alert('Search completed but found low-quality results (Wikipedia, etc.). No suitable website domain identified.');
                btn.textContent = originalText;
                btn.disabled = false;
            } else if (data.error) {
                alert('Error enriching brand: ' + data.error);
                btn.textContent = originalText;
                btn.disabled = false;
            } else {
                alert('No website found for this brand');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            clearInterval(progressInterval);
            hideEnrichmentProgress();
            console.error('Error:', error);
            
            if (error.name === 'AbortError') {
                alert('Search timed out after 2 minutes. The enrichment system is currently slow due to anti-detection measures. Please try again later or use manual input.');
            } else {
                alert('Error searching for website: ' + error.message);
            }
            
            btn.textContent = originalText;
            btn.disabled = false;
        });
    };
    
    window.flagWebsite = function(brandName) {
        const reason = prompt('Please provide a reason for flagging this website (optional):');
        if (reason === null) {
            return; // User cancelled
        }
        
        // Show loading state
        const buttons = document.querySelectorAll('.verification-actions button');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.6';
        });
        
        fetch('/flag_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                brand_name: brandName,
                reason: reason || 'Manual review requested'
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'warning');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // Restore button states on error
                buttons.forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                });
                showNotification(data.error || 'Failed to flag website', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Restore button states on error
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
            });
            showNotification('Network error occurred', 'error');
        });
    };
    
    // Notification system
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            animation: slideIn 0.3s ease-out;
        `;
        
        // Set background color based on type
        switch (type) {
            case 'success':
                notification.style.backgroundColor = '#10b981';
                break;
            case 'error':
                notification.style.backgroundColor = '#ef4444';
                break;
            case 'warning':
                notification.style.backgroundColor = '#f59e0b';
                break;
            default:
                notification.style.backgroundColor = '#3b82f6';
        }
        
        // Add slide-in animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        
        if (!document.querySelector('#notification-styles')) {
            style.id = 'notification-styles';
            document.head.appendChild(style);
        }
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
    
    // Add print styles dynamically
    const printStyles = `
        @media print {
            .brand-actions,
            .section-actions,
            .nav-links {
                display: none !important;
            }
            
            .info-card {
                break-inside: avoid;
                box-shadow: none !important;
                border: 1px solid #ccc !important;
            }
            
            .skus-table {
                font-size: 0.75rem !important;
            }
            
            .skus-table th,
            .skus-table td {
                padding: 0.5rem !important;
            }
            
            body {
                background: white !important;
            }
        }
    `;
    
    // Inject print styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = printStyles;
    document.head.appendChild(styleSheet);
    
    // Manual Entry Verification Functions
    window.verifyManualEntry = function(brandName, entryId, verified) {
        const action = verified ? 'verify' : 'reject';
        const confirmMessage = verified ? 
            'Are you sure you want to verify this manual entry?' : 
            'Are you sure you want to reject this manual entry?';
        
        if (!confirm(confirmMessage)) return;
        
        fetch('/verify_manual_entry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                entry_id: entryId,
                verified: verified
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                alert(`Manual entry ${action}d successfully!`);
                location.reload();
            } else {
                alert(`Error ${action}ing manual entry: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error ${action}ing manual entry: ${error.message}`);
        });
    };
    
    window.flagManualEntry = function(brandName, entryId) {
        const reason = prompt('Please provide a reason for flagging this manual entry:');
        if (!reason) return;
        
        fetch('/flag_manual_entry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName,
                entry_id: entryId,
                reason: reason
            })
        })
        .then(response => safeJsonParse(response))
        .then(data => {
            if (data.success) {
                alert('Manual entry flagged successfully!');
                location.reload();
            } else {
                alert(`Error flagging manual entry: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error flagging manual entry: ${error.message}`);
        });
    };
    
    // Website Edit Mode Functions
    window.toggleEditMode = function(brandName) {
        console.log('toggleEditMode called for brand:', brandName);
        const displayDiv = document.getElementById('website-display');
        const editDiv = document.getElementById('website-edit');
        
        console.log('Display div:', displayDiv);
        console.log('Edit div:', editDiv);
        
        if (displayDiv && editDiv) {
            // Use CSS classes instead of style.display
            displayDiv.classList.add('hidden');
            editDiv.classList.remove('hidden');
            
            // Focus on the URL input field
            const urlInput = editDiv.querySelector('input[name="url"]');
            if (urlInput) {
                setTimeout(() => urlInput.focus(), 100);
            }
        } else {
            console.error('Could not find display or edit divs');
        }
    };
    
    window.cancelEditMode = function() {
        console.log('cancelEditMode called');
        const displayDiv = document.getElementById('website-display');
        const editDiv = document.getElementById('website-edit');
        
        if (displayDiv && editDiv) {
            // Use CSS classes instead of style.display
            displayDiv.classList.remove('hidden');
            editDiv.classList.add('hidden');
        } else {
            console.error('Could not find display or edit divs');
        }
    };
    
    // Multi-choice website selection functions
    window.showWebsiteOptions = function(data) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 0.5rem;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            margin: 1rem;
        `;
        
        const brandContext = data.brand_context || {};
        const contextInfo = `
            <div style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #374151;">📊 Brand Context</h4>
                <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">
                    <strong>Types:</strong> ${brandContext.class_types?.join(', ') || 'Unknown'}<br>
                    <strong>Countries:</strong> ${brandContext.countries?.join(', ') || 'Unknown'}<br>
                    <strong>SKUs:</strong> ${brandContext.total_skus || 0}
                </p>
            </div>
        `;
        
        const optionsHtml = data.options.map((option, index) => `
            <div class="option-card" style="border: 2px solid #e5e7eb; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; cursor: pointer; transition: all 0.2s;" 
                 onclick="selectOption(${option.rank}, '${option.url}', '${option.domain}')">
                <div style="display: flex; justify-content: between; align-items: start; margin-bottom: 0.5rem;">
                    <h4 style="margin: 0; color: #111827;">
                        ${option.rank}. ${option.domain}
                        <span style="background: #dbeafe; color: #1e40af; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; margin-left: 0.5rem;">
                            ${Math.round(option.final_confidence * 100)}% confidence
                        </span>
                    </h4>
                </div>
                <p style="margin: 0.5rem 0; font-size: 0.875rem; color: #374151; font-weight: 500;">${option.title}</p>
                <p style="margin: 0.5rem 0; font-size: 0.875rem; color: #6b7280;">${option.snippet}</p>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.75rem; color: #9ca3af;">${option.reasoning}</p>
                <a href="${option.url}" target="_blank" style="font-size: 0.75rem; color: #3b82f6; text-decoration: none;">🔗 ${option.url}</a>
            </div>
        `).join('');
        
        content.innerHTML = `
            <h3 style="margin: 0 0 1rem 0; color: #111827;">🤔 Multiple Website Options Found</h3>
            <p style="margin-bottom: 1.5rem; color: #6b7280;">The AI found multiple potential websites but isn't confident enough to auto-select. Please choose the best option:</p>
            
            ${contextInfo}
            
            <div style="margin-bottom: 1.5rem;">
                ${optionsHtml}
            </div>
            
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button onclick="rejectAllOptions()" style="background: #ef4444; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 0.375rem; cursor: pointer;">
                    🚫 None of these are correct
                </button>
                <button onclick="closeOptionsModal()" style="background: #6b7280; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 0.375rem; cursor: pointer;">
                    Cancel
                </button>
            </div>
        `;
        
        modal.appendChild(content);
        document.body.appendChild(modal);
        window.currentOptionsModal = modal;
        window.currentOptionsData = data;
        
        // Add hover effects
        const optionCards = content.querySelectorAll('.option-card');
        optionCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.borderColor = '#3b82f6';
                card.style.backgroundColor = '#f8fafc';
            });
            card.addEventListener('mouseleave', () => {
                card.style.borderColor = '#e5e7eb';
                card.style.backgroundColor = 'white';
            });
        });
    };
    
    window.selectOption = function(rank, url, domain) {
        const data = window.currentOptionsData;
        if (!data) return;
        
        fetch('/enrichment/select_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: data.brand_name,
                selected_option: rank,
                selected_url: url,
                options: data.options,
                user_feedback: 'selected'
            })
        })
        .then(response => safeJsonParse(response))
        .then(result => {
            if (result.success) {
                showNotification(`✅ Selected website: ${domain}`, 'success');
                displayWebsiteResult(result.selected_website);
                closeOptionsModal();
                
                // Optional: Refresh page to show new website
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification('❌ Error saving selection: ' + result.error, 'error');
            }
        })
        .catch(error => {
            console.error('Selection error:', error);
            showNotification('❌ Network error during selection', 'error');
        });
    };
    
    window.rejectAllOptions = function() {
        const reason = prompt('Why are none of these correct? (This helps improve the AI):', 
                             'Not the official website / Wrong type of business / Different brand with same name');
        
        if (!reason) return;
        
        const data = window.currentOptionsData;
        if (!data) return;
        
        fetch('/enrichment/select_website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: data.brand_name,
                rejection_reason: reason,
                options: data.options,
                user_feedback: 'rejected_all'
            })
        })
        .then(response => safeJsonParse(response))
        .then(result => {
            if (result.success) {
                showNotification('📚 Feedback recorded - AI will learn from this!', 'success');
                closeOptionsModal();
            } else {
                showNotification('❌ Error saving feedback: ' + result.error, 'error');
            }
        })
        .catch(error => {
            console.error('Rejection error:', error);
            showNotification('❌ Network error during feedback', 'error');
        });
    };
    
    window.closeOptionsModal = function() {
        const modal = window.currentOptionsModal;
        if (modal && modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
        window.currentOptionsModal = null;
        window.currentOptionsData = null;
    };
    
    window.displayWebsiteResult = function(website) {
        // Update the website display on the page
        const websiteSection = document.querySelector('.website-section');
        if (websiteSection && website && website.url) {
            // Create new website display
            const websiteHtml = `
                <div class="info-card">
                    <div class="card-header">
                        <h3>🌐 Website Information</h3>
                        <div class="website-status verified">✅ Selected</div>
                    </div>
                    <div class="card-content">
                        <p class="website-url">
                            <a href="${website.url}" target="_blank">${website.url}</a>
                        </p>
                        <p class="website-domain">${website.domain}</p>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${Math.round(website.confidence * 100)}%"></div>
                            <span class="confidence-text">${Math.round(website.confidence * 100)}% confidence</span>
                        </div>
                    </div>
                </div>
            `;
            websiteSection.innerHTML = websiteHtml;
        }
    };

    // Apollo Contact Management Functions
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            // Show brief success indicator
            const event = new CustomEvent('showNotification', {
                detail: { message: 'Copied to clipboard!', type: 'success', duration: 2000 }
            });
            document.dispatchEvent(event);
        }).catch(function(err) {
            console.error('Could not copy text: ', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        });
    };

    window.composeEmail = function(email, brandName, contactName) {
        const subject = encodeURIComponent(`Partnership Opportunity - ${brandName} Distribution`);
        const body = encodeURIComponent(
            `Dear ${contactName},\n\n` +
            `I hope this email finds you well. My name is [Your Name] from Helmsman Imports, ` +
            `a leading alcohol import and distribution company in the United States.\n\n` +
            `We've been following ${brandName} and are impressed with your portfolio. ` +
            `We believe there's a strong opportunity for partnership to expand your distribution ` +
            `reach in the US market.\n\n` +
            `Helmsman Imports specializes in:\n` +
            `• TTB/COLA regulatory compliance and permitting\n` +
            `• Nationwide distribution network\n` +
            `• Premium brand portfolio management\n` +
            `• Marketing and sales support\n\n` +
            `Would you be available for a brief call next week to discuss potential collaboration?\n\n` +
            `Best regards,\n[Your Name]\nHelmsman Imports\n[Your Contact Information]`
        );

        const mailtoLink = `mailto:${email}?subject=${subject}&body=${body}`;
        window.open(mailtoLink);
    };

    window.addToCRM = function(email, brandName, contactName) {
        // This would integrate with your CRM system
        // For now, show a modal or alert
        alert(`Adding ${contactName} from ${brandName} to CRM...\n\nEmail: ${email}\n\nThis would integrate with your CRM system.`);
    };

    window.logContact = function(email, brandName, contactName) {
        // This would log the outreach attempt
        // For now, show a modal for manual logging
        const logData = {
            contact: contactName,
            brand: brandName,
            email: email,
            date: new Date().toISOString().split('T')[0],
            action: 'outreach_logged'
        };

        alert(`Logging outreach for:\n\n${contactName} (${brandName})\nEmail: ${email}\nDate: ${logData.date}\n\nThis would be saved to your outreach tracking system.`);
    };

    window.showAllContacts = function() {
        // This would show a modal with all contacts for the brand
        alert('This would open a modal showing all available contacts for this brand.');
    };

    // Toggle contact dropdown details
    window.toggleContactDetails = function(contactId) {
        const content = document.getElementById(contactId);
        const arrow = document.getElementById('arrow-' + contactId);

        if (content.style.display === 'none' || content.style.display === '') {
            content.style.display = 'block';
            arrow.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            arrow.style.transform = 'rotate(0deg)';
        }
    };

    // Notification system
    document.addEventListener('showNotification', function(e) {
        const { message, type = 'info', duration = 3000 } = e.detail;

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            font-weight: 500;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;

        document.body.appendChild(notification);

        // Trigger animation
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove notification
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    });

    // Load consolidation history
    async function loadConsolidationHistory() {
        const brandName = document.querySelector('.brand-name').textContent;
        const historyCard = document.getElementById('consolidation-history-card');
        const historyContent = document.getElementById('consolidation-history-content');

        if (!historyCard || !historyContent) {
            return; // Card not present in template
        }

        try {
            const response = await fetch(`/api/brand/${encodeURIComponent(brandName)}/consolidation_history`);
            const data = await response.json();

            if (data.success && data.history && data.history.length > 0) {
                // Build history HTML
                let historyHtml = '';

                // Group history by type
                const consolidatedFrom = data.history.filter(h => h.new_brand_name === brandName);
                const consolidatedInto = data.history.filter(h => h.old_brand_name === brandName);

                // Show "Consolidated from" (this brand absorbed others)
                if (consolidatedFrom.length > 0) {
                    historyHtml += '<div class="consolidation-section">';
                    historyHtml += '<h3 class="consolidation-type-header">📥 Consolidated From:</h3>';
                    historyHtml += '<ul class="consolidation-list">';

                    consolidatedFrom.forEach(record => {
                        const typeIcon = record.consolidation_type === 'case_variation' ? '🔤' :
                                       record.consolidation_type === 'punctuation_variation' ? '📝' :
                                       record.consolidation_type === 'sku_consolidation' ? '🎯' : '🔀';

                        historyHtml += `
                            <li class="consolidation-item">
                                <span class="consolidation-icon">${typeIcon}</span>
                                <div class="consolidation-details">
                                    <strong class="old-brand-name">"${record.old_brand_name}"</strong>
                                    <span class="consolidation-reason">${record.consolidation_reason || record.consolidation_type}</span>
                                    <span class="consolidation-meta">
                                        ${record.sku_count_moved} SKU${record.sku_count_moved !== 1 ? 's' : ''} moved
                                        · ${new Date(record.consolidation_date).toLocaleDateString()}
                                    </span>
                                </div>
                            </li>
                        `;
                    });

                    historyHtml += '</ul></div>';
                }

                // Show "Consolidated into" (this brand was absorbed)
                if (consolidatedInto.length > 0) {
                    historyHtml += '<div class="consolidation-section">';
                    historyHtml += '<h3 class="consolidation-type-header">📤 Consolidated Into:</h3>';
                    historyHtml += '<ul class="consolidation-list">';

                    consolidatedInto.forEach(record => {
                        historyHtml += `
                            <li class="consolidation-item">
                                <div class="consolidation-details">
                                    <p class="consolidation-redirect">
                                        This brand was consolidated into
                                        <strong class="new-brand-name">"${record.new_brand_name}"</strong>
                                    </p>
                                    <span class="consolidation-reason">${record.consolidation_reason || record.consolidation_type}</span>
                                </div>
                            </li>
                        `;
                    });

                    historyHtml += '</ul></div>';
                }

                historyContent.innerHTML = historyHtml;
                historyCard.classList.remove('hidden');
            } else {
                // No history found - keep card hidden
                historyCard.classList.add('hidden');
            }
        } catch (error) {
            console.error('Error loading consolidation history:', error);
            // Keep card hidden on error
            historyCard.classList.add('hidden');
        }
    }

    // Load consolidation history on page load
    loadConsolidationHistory();

    // Now call checkBrandCache after all functions are defined
    try {
        checkBrandCache();
    } catch (error) {
        console.error('Error in checkBrandCache:', error);
        // Don't alert for this error as it's not critical for button functionality
    }
});

// Apollo Enrichment: Find Contacts Function
window.findContacts = async function(brandName) {
    const btn = document.getElementById('find-contacts-btn');

    if (!btn) {
        console.error('Find Contacts button not found');
        return;
    }

    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '⏳ Searching...';

    try {
        // Call Apollo enrichment endpoint
        const response = await fetch('/apollo/enrich_brand', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                brand_name: brandName
            })
        });

        const result = await response.json();

        if (result.success) {
            // Success! Reload page to show contacts
            btn.innerHTML = '✅ Success!';
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else if (result.status === 'needs_selection') {
            // Multiple recommendations - show modal for user selection
            btn.innerHTML = '🔍 Find Contacts';
            btn.disabled = false;
            showApolloSelectionModal(brandName, result.recommendations);
        } else if (result.status === 'not_found') {
            // No matches found
            btn.innerHTML = '❌ Not Found';
            btn.disabled = false;
            alert('No company found in Apollo database. You can manually enter contact information.');
        } else {
            // Other statuses
            btn.innerHTML = '🔍 Find Contacts';
            btn.disabled = false;
            alert(result.message || 'Unable to enrich brand');
        }
    } catch (error) {
        console.error('Error enriching brand:', error);
        btn.innerHTML = '❌ Error';
        btn.disabled = false;
        alert('Error finding contacts: ' + error.message);

        // Reset button after 2 seconds
        setTimeout(() => {
            btn.innerHTML = '🔍 Find Contacts';
            btn.disabled = false;
        }, 2000);
    }
};

// Apollo Selection Modal
window.showApolloSelectionModal = function(brandName, recommendations) {
    // Create modal HTML
    const modalHTML = `
        <div id="apollo-selection-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 12px; max-width: 900px; max-height: 90vh; overflow-y: auto; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                <h2 style="margin-top: 0; color: #2c3e50;">Select Company for "${brandName}"</h2>
                <p style="color: #666; margin-bottom: 20px;">Found ${recommendations.length} potential matches. Select the correct company:</p>

                <div id="company-options">
                    ${recommendations.map((rec, idx) => `
                        <div class="company-option" data-company-id="${rec.company.id}" style="border: 2px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 15px; cursor: pointer; transition: all 0.3s;" onmouseover="this.style.borderColor='#3498db'" onmouseout="this.style.borderColor='#e0e0e0'" onclick="selectCompany(${idx})">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <h3 style="margin: 0 0 10px 0; color: #2c3e50;">${rec.company.name}</h3>
                                    <div style="color: #666; font-size: 14px; margin-bottom: 8px;">
                                        ${rec.company.domain ? `<span style="background: #e8f5e9; padding: 3px 8px; border-radius: 4px; margin-right: 8px;">🌐 ${rec.company.domain}</span>` : ''}
                                        ${rec.company.industry ? `<span style="background: #e3f2fd; padding: 3px 8px; border-radius: 4px; margin-right: 8px;">🏭 ${rec.company.industry}</span>` : ''}
                                        ${rec.company.employee_count ? `<span style="background: #fff3e0; padding: 3px 8px; border-radius: 4px;">👥 ${rec.company.employee_count} employees</span>` : ''}
                                    </div>
                                    ${rec.company.location && rec.company.location.city ? `<div style="color: #888; font-size: 13px;">📍 ${rec.company.location.city}, ${rec.company.location.state || ''} ${rec.company.location.country || ''}</div>` : ''}
                                </div>
                                <div style="text-align: right;">
                                    <div style="background: ${rec.confidence >= 80 ? '#4caf50' : rec.confidence >= 60 ? '#ff9800' : '#999'}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                                        ${rec.confidence}% Match
                                    </div>
                                </div>
                            </div>

                            ${rec.contacts_preview && rec.contacts_preview.length > 0 ? `
                                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e0e0e0;">
                                    <strong style="color: #555; font-size: 13px;">Sample Contacts:</strong>
                                    <div style="margin-top: 8px;">
                                        ${rec.contacts_preview.map(contact => `
                                            <div style="background: #f5f5f5; padding: 8px 12px; border-radius: 6px; margin-top: 5px; font-size: 13px;">
                                                👤 <strong>${contact.name}</strong> - ${contact.title || 'No title'}
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>

                <div style="margin-top: 25px; padding-top: 20px; border-top: 2px solid #e0e0e0; display: flex; justify-content: space-between;">
                    <button onclick="closeApolloModal()" style="background: #95a5a6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">
                        Cancel
                    </button>
                    <button onclick="saveManualEntry('${brandName}')" style="background: #e67e22; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">
                        None Match - Enter Manually
                    </button>
                </div>
            </div>
        </div>
    `;

    // Insert modal into page
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Store recommendations globally for selection
    window.apolloRecommendations = recommendations;
    window.apolloBrandName = brandName;
};

window.selectCompany = async function(companyIndex) {
    const recommendation = window.apolloRecommendations[companyIndex];
    const brandName = window.apolloBrandName;

    // Close modal
    closeApolloModal();

    // Show loading message
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'apollo-loading';
    loadingDiv.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); z-index: 10001; text-align: center;';
    loadingDiv.innerHTML = '<h3 style="margin: 0 0 15px 0;">⏳ Fetching Full Contact Details...</h3><p style="color: #666; margin: 0;">This may take a few seconds</p>';
    document.body.appendChild(loadingDiv);

    try {
        // Call backend to save selected company and fetch full contacts
        const response = await fetch('/apollo/approve_match', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                brand_name: brandName,
                company_id: recommendation.company.id,
                company_data: recommendation.company,
                confidence: recommendation.confidence,
                match_factors: recommendation.match_factors
            })
        });

        const result = await response.json();

        // Remove loading
        document.body.removeChild(loadingDiv);

        if (result.success) {
            const contactCount = result.top_contacts ? result.top_contacts.length : 'multiple';
            alert(`✅ Successfully saved contacts for ${recommendation.company.name}!\n\n${result.message}`);
            window.location.reload();
        } else {
            alert('❌ Error: ' + (result.error || 'Failed to save company'));
        }
    } catch (error) {
        document.body.removeChild(loadingDiv);
        alert('❌ Error: ' + error.message);
    }
};

window.closeApolloModal = function() {
    const modal = document.getElementById('apollo-selection-modal');
    if (modal) {
        modal.remove();
    }
};

window.saveManualEntry = function(brandName) {
    closeApolloModal();
    alert('Manual entry feature coming soon! For now, please contact support to add this brand manually.');
};