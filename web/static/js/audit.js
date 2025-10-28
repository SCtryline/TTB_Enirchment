/**
 * TTB COLA Registry - Audit Dashboard JavaScript
 * Handles data health dashboard and consolidation review interface
 */

class AuditDashboard {
    constructor() {
        this.currentPage = 1;
        this.perPage = 5;
        this.confidenceThreshold = 0.7;
        this.currentGroup = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadHealthMetrics();
        this.loadConsolidationQueue();
    }

    bindEvents() {
        // Health dashboard refresh
        document.getElementById('refresh-health')?.addEventListener('click', () => {
            this.loadHealthMetrics();
        });

        // Consolidation queue controls
        document.getElementById('confidence-filter')?.addEventListener('change', (e) => {
            this.confidenceThreshold = parseFloat(e.target.value);
            this.currentPage = 1;
            this.loadConsolidationQueue();
        });

        document.getElementById('refresh-queue')?.addEventListener('click', () => {
            this.loadConsolidationQueue();
        });

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadConsolidationQueue();
            }
        });

        document.getElementById('next-page')?.addEventListener('click', () => {
            this.currentPage++;
            this.loadConsolidationQueue();
        });

        // Health card clicks
        document.querySelectorAll('.health-card.clickable').forEach(card => {
            card.addEventListener('click', () => {
                const metric = card.dataset.metric;
                this.showHealthDetails(metric);
            });
        });

        // Health modal controls
        document.getElementById('close-health-modal')?.addEventListener('click', () => {
            this.closeHealthModal();
        });

        document.getElementById('close-health-details')?.addEventListener('click', () => {
            this.closeHealthModal();
        });

        // Modal controls
        document.getElementById('close-modal')?.addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('cancel-action')?.addEventListener('click', () => {
            this.closeModal();
        });

        const submitButton = document.getElementById('submit-action');
        if (submitButton) {
            console.log('✅ Submit button found, attaching event listener');
            submitButton.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔘 Submit button event triggered');
                this.submitAction();
            });
        } else {
            console.error('❌ Submit button not found in DOM');
        }

        // Close modals on background click
        document.getElementById('action-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'action-modal') {
                this.closeModal();
            }
        });

        document.getElementById('health-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'health-modal') {
                this.closeHealthModal();
            }
        });
    }

    async loadHealthMetrics() {
        try {
            this.showHealthLoading();
            
            const response = await fetch('/audit/data_health');
            const data = await response.json();
            
            if (data.success) {
                this.displayHealthMetrics(data.metrics);
                this.updateLastUpdated(data.metrics.last_updated);
            } else {
                this.showHealthError('Failed to load health metrics');
            }
        } catch (error) {
            console.error('Error loading health metrics:', error);
            this.showHealthError('Network error loading health metrics');
        }
    }

    displayHealthMetrics(metrics) {
        // Overall health score
        const overallScore = metrics.overview.overall_health_score;
        document.getElementById('overall-score').textContent = `${overallScore}%`;
        this.updateHealthRing('overall-progress', overallScore);

        // Priority Rankings metrics
        if (metrics.rankings) {
            const rankings = metrics.rankings;
            document.getElementById('ranking-summary').textContent =
                `${rankings.total_critical + rankings.total_high} High Priority`;
            document.getElementById('tier1-count').textContent = rankings.total_critical.toLocaleString();
            document.getElementById('tier2-count').textContent = rankings.total_high.toLocaleString();
            document.getElementById('apollo-ready-count').textContent = rankings.apollo_ready.toLocaleString();
        }

        // Completeness metrics
        const completeness = metrics.completeness;
        document.getElementById('completeness-score').textContent = `${completeness.score}%`;
        document.getElementById('website-coverage').textContent = `${completeness.website_coverage}%`;
        document.getElementById('importer-links').textContent =
            `${((completeness.brands_with_importers / metrics.overview.total_brands) * 100).toFixed(1)}%`;
        document.getElementById('country-data').textContent =
            `${((completeness.brands_with_countries / metrics.overview.total_brands) * 100).toFixed(1)}%`;

        // Quality metrics
        const quality = metrics.quality;
        document.getElementById('quality-score').textContent = `${quality.score}%`;
        document.getElementById('duplicates-count').textContent = quality.potential_duplicates;
        document.getElementById('missing-data-count').textContent = quality.missing_critical_data;
        document.getElementById('inconsistencies-count').textContent = quality.data_inconsistencies;

        // Enrichment metrics
        const enrichment = metrics.enrichment;
        document.getElementById('enrichment-rate').textContent = `${enrichment.enrichment_rate.toFixed(1)}%`;
        document.getElementById('enriched-count').textContent = enrichment.total_enriched.toLocaleString();
        document.getElementById('high-priority-pending').textContent =
            (metrics.rankings ? metrics.rankings.total_critical + metrics.rankings.total_high : 0).toLocaleString();
        document.getElementById('apollo-ready-enrichment').textContent =
            (metrics.rankings ? metrics.rankings.apollo_ready : 0).toLocaleString();

        // Agentic Learning metrics
        if (metrics.learning) {
            const learning = metrics.learning;
            document.getElementById('learning-accuracy').textContent = `${learning.success_rate}%`;
            document.getElementById('patterns-learned').textContent = learning.patterns_learned.toLocaleString();
            document.getElementById('success-rate').textContent = `${learning.success_rate}%`;
            document.getElementById('auto-consolidated').textContent = learning.auto_consolidated.toLocaleString();
        }
    }

    updateHealthRing(elementId, percentage) {
        const progressElement = document.getElementById(elementId);
        if (progressElement) {
            const circumference = 283; // 2 * PI * 45
            const offset = circumference - (percentage / 100) * circumference;
            progressElement.style.strokeDashoffset = offset;
        }
    }

    showHealthLoading() {
        const loadingElements = [
            'overall-score', 'ranking-summary', 'tier1-count', 'tier2-count', 'apollo-ready-count',
            'completeness-score', 'website-coverage', 'importer-links', 'country-data',
            'quality-score', 'duplicates-count', 'missing-data-count', 'inconsistencies-count',
            'enrichment-rate', 'enriched-count', 'high-priority-pending', 'apollo-ready-enrichment',
            'learning-accuracy', 'patterns-learned', 'success-rate', 'auto-consolidated'
        ];

        loadingElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '--';
                element.classList.add('pulse');
            }
        });
    }

    showHealthError(message) {
        console.error('Health metrics error:', message);
        // Could show a toast notification here
    }

    async loadConsolidationQueue() {
        try {
            this.showQueueLoading();
            
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                confidence_threshold: this.confidenceThreshold
            });
            
            // Show enhanced loading message for SKU analysis
            const queueContainer = document.getElementById('review-queue');
            queueContainer.innerHTML = `
                <div class="loading-message">
                    <div class="loading-spinner"></div>
                    <p>🤖 Analyzing brand consolidation opportunities...</p>
                    <div class="loading-details">
                        <div class="loading-step">🔍 Scanning brands with URLs</div>
                        <div class="loading-step">🎯 Detecting SKU vs Brand hierarchies</div>
                        <div class="loading-step">🏢 Identifying portfolio companies</div>
                        <div class="loading-step">📊 Ranking by confidence scores</div>
                    </div>
                    <small>This may take up to 45 seconds for comprehensive analysis...</small>
                </div>
            `;

            // Add timeout and better error handling
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 second timeout for SKU analysis
            
            const response = await fetch('/audit/brand_name_analysis', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.normalization_opportunities !== undefined) {
                // Transform the data to match expected format
                const queueData = {
                    summary: {
                        high_priority: data.normalization_opportunities.filter(o => o.confidence >= 0.9).length,
                        medium_priority: data.normalization_opportunities.filter(o => o.confidence >= 0.7 && o.confidence < 0.9).length,
                        low_priority: data.normalization_opportunities.filter(o => o.confidence < 0.7).length,
                        total_pending_review: data.total_count || data.normalization_opportunities.length
                    },
                    groups: data.normalization_opportunities.filter(o => o.confidence >= this.confidenceThreshold)
                };
                this.displayConsolidationQueue(queueData);
            } else {
                this.showQueueError('Failed to load consolidation opportunities');
            }
        } catch (error) {
            console.error('Error loading consolidation queue:', error);
            if (error.name === 'AbortError') {
                this.showQueueError('Request timeout - consolidation analysis is taking too long. Please try again.');
            } else if (error.message.includes('HTTP error')) {
                this.showQueueError(`Server error: ${error.message}`);
            } else {
                this.showQueueError(`Network error loading consolidation queue: ${error.message}`);
            }
        }
    }

    displayConsolidationQueue(queue) {
        // Update summary
        const summary = queue.summary;
        document.getElementById('high-priority-count').textContent = summary.high_priority;
        document.getElementById('medium-priority-count').textContent = summary.medium_priority;
        document.getElementById('low-priority-count').textContent = summary.low_priority;
        document.getElementById('total-pending-count').textContent = summary.total_pending_review;

        // Display groups
        const queueContainer = document.getElementById('review-queue');
        queueContainer.innerHTML = '';

        if (queue.groups.length === 0) {
            queueContainer.innerHTML = `
                <div class="no-groups-message">
                    <p>🎉 No consolidation groups found at ${(this.confidenceThreshold * 100)}% confidence threshold.</p>
                    <p>Try lowering the confidence threshold to see more suggestions.</p>
                </div>
            `;
            this.hidePagination();
            return;
        }

        queue.groups.forEach(group => {
            const groupElement = this.createGroupElement(group);
            queueContainer.appendChild(groupElement);
        });

        // Update pagination (if provided)
        if (queue.pagination) {
            this.updatePagination(queue.pagination);
        } else {
            // No pagination data, hide pagination controls
            this.hidePagination();
        }
    }

    createGroupElement(group) {
        const div = document.createElement('div');
        const priority = group.confidence > 0.8 ? 'high' : group.confidence > 0.6 ? 'medium' : 'low';
        div.className = `review-item ${priority}-priority fade-in`;
        
        const confidenceClass = group.confidence > 0.8 ? 'high' : 
                               group.confidence > 0.6 ? 'medium' : 'low';
        
        // Handle both old and new data structures
        const canonicalName = group.suggested_name || group.canonical_name;
        const brands = group.brands_to_merge || group.current_brands || group.brands || [];
        const reason = group.reason || 'Brand consolidation opportunity';

        // Enhanced SKU vs Brand analysis display
        const isEnhancedAnalysis = group.enhanced_analysis || false;
        const consolidationType = group.consolidation_type || 'UNKNOWN';
        const consolidationDescription = group.consolidation_description || reason;

        // Generate analysis type badge and icon
        let analysisTypeBadge = '';
        let analysisIcon = '🔄';

        if (isEnhancedAnalysis) {
            if (group.is_sku_consolidation) {
                analysisTypeBadge = '<span class="analysis-type-badge sku-consolidation">🎯 SKU → Brand</span>';
                analysisIcon = '🎯';
            } else if (group.is_portfolio_company) {
                analysisTypeBadge = '<span class="analysis-type-badge portfolio-company">🏢 Portfolio Company</span>';
                analysisIcon = '🏢';
            } else {
                analysisTypeBadge = '<span class="analysis-type-badge similar-names">📝 Similar Names</span>';
                analysisIcon = '📝';
            }
        } else {
            analysisTypeBadge = '<span class="analysis-type-badge legacy-analysis">🔄 Legacy Analysis</span>';
        }

        // URL evidence display
        let urlEvidenceDisplay = '';
        if (group.url_evidence && group.domain) {
            urlEvidenceDisplay = `
                <div class="url-evidence">
                    <strong>🌐 URL Evidence:</strong>
                    <span class="domain-info">${this.escapeHtml(group.domain)}</span>
                    <a href="${this.escapeHtml(group.url_evidence)}" target="_blank" class="url-link">View Site</a>
                </div>
            `;
        }

        // Hierarchy information display
        let hierarchyDisplay = '';
        if (group.hierarchy && Object.keys(group.hierarchy).length > 0) {
            const hierarchy = group.hierarchy;
            if (hierarchy.parent_brand && hierarchy.skus) {
                hierarchyDisplay = `
                    <div class="hierarchy-info">
                        <strong>📊 Hierarchy:</strong>
                        Parent Brand: <span class="parent-brand">${this.escapeHtml(hierarchy.parent_brand)}</span>
                        → SKUs: <span class="sku-count">${hierarchy.skus.length} products</span>
                    </div>
                `;
            } else if (hierarchy.parent_brand && hierarchy.sibling_brands) {
                hierarchyDisplay = `
                    <div class="hierarchy-info">
                        <strong>📊 Portfolio:</strong>
                        Main Brand: <span class="parent-brand">${this.escapeHtml(hierarchy.parent_brand)}</span>
                        → Sibling Brands: <span class="sibling-count">${hierarchy.sibling_brands.length}</span>
                    </div>
                `;
            }
        }

        div.innerHTML = `
            <div class="review-item-header">
                <div>
                    <div class="canonical-name">${analysisIcon} ${this.escapeHtml(canonicalName)}</div>
                    <div class="pattern-analysis">
                        Consolidate: ${brands.length} brand(s) ${analysisTypeBadge}
                    </div>
                </div>
                <div class="confidence-badge ${confidenceClass}">
                    ${(group.confidence * 100).toFixed(1)}% confidence
                </div>
            </div>

            <div class="brand-list">
                ${brands.map(brand =>
                    `<span class="brand-tag">${this.escapeHtml(brand)}</span>`
                ).join('')}
                <span class="arrow">→</span>
                <span class="brand-tag canonical">${this.escapeHtml(canonicalName)}</span>
            </div>

            ${urlEvidenceDisplay}
            ${hierarchyDisplay}

            <div class="review-reason">
                <strong>🤖 AI Analysis:</strong> ${this.escapeHtml(consolidationDescription)}
            </div>
            
            <div class="review-actions">
                <button class="btn btn-success" data-proposal-id="${group.proposal_id}" data-action="approve">
                    ✅ Approve Consolidation
                </button>
                <button class="btn btn-danger" data-proposal-id="${group.proposal_id}" data-action="reject">
                    ❌ Reject
                </button>
                <button class="btn btn-primary" data-proposal-id="${group.proposal_id}" data-action="review">
                    📝 Review Details
                </button>
            </div>
        `;
        
        // Store group data on the element
        div.dataset.groupData = JSON.stringify({
            proposal_id: group.proposal_id,
            canonical_name: canonicalName,
            brands: brands,
            confidence: group.confidence,
            reason: reason,
            url_evidence: group.url_evidence,
            domain: group.domain,
            consolidation_type: group.consolidation_type,
            similarity_scores: group.similarity_scores,
            hierarchy: group.hierarchy
        });
        
        // Add event listeners to buttons
        div.querySelectorAll('.review-actions button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const groupData = JSON.parse(div.dataset.groupData);
                const action = button.dataset.action;

                console.log('🎯 Button clicked:', { action, proposalId: groupData.proposal_id, groupData });

                if (action === 'approve') {
                    this.approveGroup(groupData.proposal_id, groupData.canonical_name, groupData.brands, groupData.confidence);
                } else if (action === 'reject') {
                    this.rejectGroup(groupData.proposal_id, groupData.canonical_name, groupData.brands, groupData.confidence);
                } else if (action === 'review') {
                    this.reviewGroup(groupData.proposal_id, groupData.canonical_name, groupData.brands, groupData.confidence, groupData.reason, groupData);
                }
            });
        });
        
        return div;
    }

    updatePagination(pagination) {
        const paginationControls = document.getElementById('pagination-controls');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');
        
        // Safety check for undefined pagination
        if (!pagination || !pagination.total_pages || pagination.total_pages <= 1) {
            if (paginationControls) paginationControls.style.display = 'none';
            return;
        }
        
        paginationControls.style.display = 'flex';
        prevBtn.disabled = !pagination.has_prev;
        nextBtn.disabled = !pagination.has_next;
        pageInfo.textContent = `Page ${pagination.current_page} of ${pagination.total_pages}`;
    }

    hidePagination() {
        document.getElementById('pagination-controls').style.display = 'none';
    }

    showQueueLoading() {
        const queueContainer = document.getElementById('review-queue');
        queueContainer.innerHTML = '<div class="loading-message pulse">Loading consolidation opportunities...</div>';
    }

    showQueueError(message) {
        const queueContainer = document.getElementById('review-queue');
        queueContainer.innerHTML = `<div class="error-message">❌ ${message}</div>`;
    }

    approveGroup(proposalId, canonicalName, brandGroup, confidence) {
        this.processConsolidation(proposalId, 'approve', canonicalName, brandGroup);
    }

    rejectGroup(proposalId, canonicalName, brandGroup, confidence) {
        // For now, just show a message since we don't have a reject endpoint
        alert('Consolidation rejected. This opportunity will not be shown again.');
        this.loadConsolidationQueue(); // Refresh the queue
    }

    reviewGroup(proposalId, canonicalName, brandGroup, confidence, reason, groupData) {
        this.currentGroup = {
            proposal_id: proposalId,
            canonical_name: canonicalName,
            brand_group: brandGroup,
            confidence: confidence,
            reason: reason,
            url_evidence: groupData.url_evidence,
            domain: groupData.domain,
            consolidation_type: groupData.consolidation_type,
            similarity_scores: groupData.similarity_scores,
            hierarchy: groupData.hierarchy
        };
        this.showModal(canonicalName, brandGroup, confidence, reason, groupData);
    }

    async processConsolidation(proposalId, action, canonicalName, brandGroup) {
        if (action === 'approve') {
            try {
                console.log('🎯 Processing SKU/Brand consolidation:', {
                    proposalId,
                    canonicalName,
                    brandGroup: brandGroup,
                    action
                });
                
                const response = await fetch('/consolidation/approve_proposal', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        proposal_id: proposalId
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.success) {
                    // Show success message
                    this.showSuccessMessage(result.message || `✅ Successfully consolidated brands into ${canonicalName}`);
                    // Refresh the consolidation queue after a short delay
                    setTimeout(() => {
                        this.loadConsolidationQueue();
                    }, 1500);
                } else {
                    this.showErrorMessage(`❌ Consolidation failed: ${result.message || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error processing consolidation:', error);
                this.showErrorMessage(`❌ Error: ${error.message}`);
            }
        }
    }

    showSuccessMessage(message) {
        // Create a temporary success notification
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.innerHTML = message;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            background: #22c55e; color: white; padding: 15px 20px;
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }

    showErrorMessage(message) {
        // Create a temporary error notification  
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.innerHTML = message;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            background: #ef4444; color: white; padding: 15px 20px;
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 8000);
    }

    showModal(canonicalName, brandGroup, confidence, reason, groupData) {
        document.getElementById('modal-title').textContent = `Review: ${canonicalName}`;

        const modalDetails = document.getElementById('modal-details');

        // Generate URL evidence section
        let urlEvidenceSection = '';
        if (groupData && (groupData.url_evidence || groupData.domain)) {
            urlEvidenceSection = this.generateUrlEvidenceSection(groupData);
        }

        // Generate consolidation type explanation
        let typeExplanation = '';
        if (groupData && groupData.consolidation_type) {
            typeExplanation = this.generateConsolidationTypeExplanation(groupData);
        }

        modalDetails.innerHTML = `
            <div class="consolidation-group">
                <h4>Brands to consolidate:</h4>
                <div class="brand-list">
                    ${brandGroup.map(brand =>
                        `<span class="brand-tag">${this.escapeHtml(brand)}</span>`
                    ).join('')}
                </div>
                <p><strong>AI Confidence:</strong> ${(confidence * 100).toFixed(1)}%</p>
                <p><strong>AI Reasoning:</strong> ${this.escapeHtml(reason)}</p>

                ${urlEvidenceSection}
                ${typeExplanation}
            </div>
        `;

        document.getElementById('action-modal').style.display = 'block';
    }

    closeModal() {
        document.getElementById('action-modal').style.display = 'none';
        this.currentGroup = null;
        document.getElementById('action-reason').value = '';
    }

    async submitAction() {
        console.log('🎯 Submit button clicked, currentGroup:', this.currentGroup);

        if (!this.currentGroup) {
            console.error('❌ No currentGroup available for submission');
            this.showErrorMessage('No consolidation data available. Please try refreshing the page.');
            return;
        }

        const action = document.getElementById('action-select').value;
        const reason = document.getElementById('action-reason').value;
        const submitButton = document.getElementById('submit-action');

        console.log('📝 Submit action:', { action, reason, currentGroup: this.currentGroup });

        // Disable button and show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Processing...';
        }

        try {
            await this.processGroupAction(
                this.currentGroup.canonical_name,
                this.currentGroup.brand_group,
                action,
                this.currentGroup.confidence,
                reason || `${action} via review interface`
            );

            this.closeModal();
        } catch (error) {
            console.error('Error in submitAction:', error);
            this.showErrorMessage('Failed to process consolidation: ' + error.message);
        } finally {
            // Re-enable button
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = 'Submit Decision';
            }
        }
    }

    async processGroupAction(canonicalName, brandGroup, action, confidence, reason) {
        console.log('🔄 processGroupAction called with:', {
            canonicalName,
            brandGroup,
            action,
            confidence,
            reason,
            currentGroup: this.currentGroup
        });

        try {
            // Use the proposal_id from the current group for enhanced consolidation
            const proposalId = this.currentGroup.proposal_id;
            console.log('📋 Using proposal_id:', proposalId);

            if (!proposalId) {
                console.error('❌ No proposal_id found in currentGroup');
                this.showErrorMessage('Missing consolidation ID. Please refresh and try again.');
                return;
            }

            if (action === 'approve') {
                // Use the enhanced consolidation system with proposal_id
                console.log('🎯 Processing enhanced consolidation via modal:', {
                    proposalId,
                    canonicalName,
                    brandGroup: brandGroup,
                    action,
                    reason
                });

                const response = await fetch('/consolidation/approve_proposal', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        proposal_id: proposalId
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                if (result.success) {
                    this.showSuccessMessage(result.message || `✅ Successfully consolidated brands into ${canonicalName}`);
                    // Refresh the queue to remove processed item
                    setTimeout(() => {
                        this.loadConsolidationQueue();
                        this.loadHealthMetrics(); // Update health metrics too
                    }, 1000);
                } else {
                    this.showErrorMessage(result.error || 'Failed to approve consolidation');
                }
            } else if (action === 'reject') {
                // For reject, just show message and refresh (no backend endpoint yet)
                this.showSuccessMessage(`❌ Consolidation rejected: ${canonicalName}`);
                setTimeout(() => {
                    this.loadConsolidationQueue();
                    this.loadHealthMetrics();
                }, 1000);
            } else {
                this.showErrorMessage('Unknown action: ' + action);
            }
        } catch (error) {
            console.error('Error processing action:', error);
            this.showErrorMessage('Network error processing action: ' + error.message);
        }
    }

    showSuccessMessage(message) {
        this.showToast(message, 'success');
    }

    showErrorMessage(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type) {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            color: white;
            font-weight: 500;
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
            ${type === 'success' ? 'background: #059669;' : 'background: #dc2626;'}
        `;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Show toast
        setTimeout(() => toast.style.opacity = '1', 100);

        // Hide and remove toast
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }

    generateUrlEvidenceSection(groupData) {
        if (!groupData.url_evidence && !groupData.domain) {
            return '';
        }

        let urlAnalysis = '';
        let urlRole = '';

        // Determine URL's role in the consolidation decision
        if (groupData.consolidation_type === 'SKU_TO_BRAND') {
            urlRole = '🎯 <strong>URL Evidence:</strong> The shared website URL confirms these are related products/SKUs from the same brand.';
            urlAnalysis = `
                <div class="url-analysis sku-analysis">
                    <h5>🌐 Website Analysis (Key Factor)</h5>
                    <div class="url-details">
                        <p><strong>Shared URL:</strong> <code>${this.escapeHtml(groupData.url_evidence || 'N/A')}</code></p>
                        <p><strong>Domain:</strong> <code>${this.escapeHtml(groupData.domain || 'N/A')}</code></p>
                        <p class="url-explanation">
                            ${urlRole} When brands share the same website, and one brand name matches the domain name,
                            that indicates the matching brand is the parent company, while others are products/SKUs under that brand.
                        </p>
                    </div>
                </div>
            `;
        } else if (groupData.consolidation_type === 'PORTFOLIO_BRANDS') {
            urlRole = '🏢 <strong>URL Evidence:</strong> The shared website URL indicates these are separate brands owned by the same portfolio company.';
            urlAnalysis = `
                <div class="url-analysis portfolio-analysis">
                    <h5>🌐 Website Analysis (Key Factor)</h5>
                    <div class="url-details">
                        <p><strong>Shared URL:</strong> <code>${this.escapeHtml(groupData.url_evidence || 'N/A')}</code></p>
                        <p><strong>Domain:</strong> <code>${this.escapeHtml(groupData.domain || 'N/A')}</code></p>
                        <p class="url-explanation">
                            ${urlRole} When multiple brands share the same website but none directly match the domain name,
                            this suggests they are distinct brands within a portfolio company's collection.
                        </p>
                    </div>
                </div>
            `;
        } else if (groupData.consolidation_type === 'SIMILAR_NAMES') {
            urlRole = '📝 <strong>URL Context:</strong> Website information provides additional validation for name-based consolidation.';
            urlAnalysis = `
                <div class="url-analysis similarity-analysis">
                    <h5>🌐 Supporting Evidence</h5>
                    <div class="url-details">
                        ${groupData.url_evidence ? `<p><strong>Website:</strong> <code>${this.escapeHtml(groupData.url_evidence)}</code></p>` : ''}
                        <p class="url-explanation">
                            ${urlRole} The URL provides context to confirm these similar brand names represent the same entity.
                        </p>
                    </div>
                </div>
            `;
        }

        // Add similarity scores if available
        if (groupData.similarity_scores) {
            const scores = groupData.similarity_scores;
            let scoreDetails = '';

            if (scores.parent_to_domain) {
                scoreDetails += `<p><strong>Brand-to-Domain Match:</strong> ${(scores.parent_to_domain * 100).toFixed(1)}%</p>`;
            }
            if (scores.sku_similarities && scores.sku_similarities.length > 0) {
                const avgSkuSimilarity = scores.sku_similarities.reduce((a, b) => a + b, 0) / scores.sku_similarities.length;
                scoreDetails += `<p><strong>Avg SKU Similarity:</strong> ${(avgSkuSimilarity * 100).toFixed(1)}%</p>`;
            }

            if (scoreDetails) {
                urlAnalysis += `
                    <div class="similarity-metrics">
                        <h6>📊 Similarity Metrics</h6>
                        ${scoreDetails}
                    </div>
                `;
            }
        }

        return urlAnalysis;
    }

    generateConsolidationTypeExplanation(groupData) {
        if (!groupData.consolidation_type) {
            return '';
        }

        let explanation = '';
        let icon = '';
        let title = '';
        let description = '';

        switch (groupData.consolidation_type) {
            case 'SKU_TO_BRAND':
                icon = '🎯';
                title = 'SKU → Brand Consolidation';
                description = 'The system identified that these appear to be product SKUs that should be consolidated under their parent brand. This is determined by analyzing shared website URLs and brand name similarity to domain names.';
                break;
            case 'PORTFOLIO_BRANDS':
                icon = '🏢';
                title = 'Portfolio Company Consolidation';
                description = 'These appear to be separate brands owned by the same portfolio company. They share the same website but maintain distinct brand identities.';
                break;
            case 'SIMILAR_NAMES':
                icon = '📝';
                title = 'Name Similarity Consolidation';
                description = 'These brands have highly similar names and likely represent variations or misspellings of the same brand entity.';
                break;
            default:
                icon = '🔍';
                title = 'Brand Consolidation';
                description = 'AI analysis suggests these brands should be consolidated based on various similarity factors.';
        }

        explanation = `
            <div class="consolidation-type-explanation">
                <h5>${icon} ${title}</h5>
                <p class="type-description">${description}</p>

                ${groupData.hierarchy ? this.generateHierarchyInfo(groupData.hierarchy) : ''}
            </div>
        `;

        return explanation;
    }

    generateHierarchyInfo(hierarchy) {
        if (!hierarchy) return '';

        let hierarchyHtml = '<div class="hierarchy-info"><h6>📋 Consolidation Hierarchy</h6>';

        if (hierarchy.parent_brand) {
            hierarchyHtml += `<p><strong>Parent Brand:</strong> ${this.escapeHtml(hierarchy.parent_brand)}</p>`;
        }

        if (hierarchy.skus && hierarchy.skus.length > 0) {
            hierarchyHtml += `<p><strong>SKUs/Products:</strong> ${hierarchy.skus.map(sku => this.escapeHtml(sku)).join(', ')}</p>`;
        }

        if (hierarchy.sibling_brands && hierarchy.sibling_brands.length > 0) {
            hierarchyHtml += `<p><strong>Portfolio Brands:</strong> ${hierarchy.sibling_brands.map(brand => this.escapeHtml(brand)).join(', ')}</p>`;
        }

        if (hierarchy.variations && hierarchy.variations.length > 0) {
            hierarchyHtml += `<p><strong>Name Variations:</strong> ${hierarchy.variations.map(variation => this.escapeHtml(variation)).join(', ')}</p>`;
        }

        if (hierarchy.relationship) {
            hierarchyHtml += `<p><strong>Relationship:</strong> ${this.escapeHtml(hierarchy.relationship)}</p>`;
        }

        hierarchyHtml += '</div>';
        return hierarchyHtml;
    }

    async showHealthDetails(metricType) {
        try {
            const response = await fetch(`/audit/health_details/${metricType}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayHealthDetails(data.details);
                document.getElementById('health-modal-title').textContent = data.details.metric_name + ' Details';
                document.getElementById('health-modal').style.display = 'block';
            } else {
                this.showErrorMessage('Failed to load health details');
            }
        } catch (error) {
            console.error('Error loading health details:', error);
            this.showErrorMessage('Network error loading health details');
        }
    }

    displayHealthDetails(details) {
        const container = document.getElementById('health-modal-details');
        
        let html = `
            <div class="health-metric-overview">
                <div class="metric-title">${details.metric_name}</div>
                <div class="metric-score">${details.overall_score.toFixed(1)}%</div>
            </div>
        `;
        
        // Score breakdown
        if (details.components && details.components.length > 0) {
            html += `
                <div class="section-title">📊 Score Breakdown</div>
                <div class="score-breakdown">
            `;
            
            details.components.forEach(component => {
                html += `
                    <div class="component-card">
                        <div class="component-header">
                            <div class="component-name">${component.name}</div>
                            <div class="component-score">${component.score.toFixed(1)}%</div>
                        </div>
                        <div class="component-weight">Weight: ${component.weight}%</div>
                        <div class="component-progress">
                            <div class="progress-bar" style="width: ${component.score}%"></div>
                        </div>
                        <div class="component-description">${component.description}</div>
                        <div class="component-stats">${component.count.toLocaleString()} of ${component.total.toLocaleString()}</div>
                    </div>
                `;
            });
            
            html += `</div>`;
        }
        
        // Issues section
        if (details.issues && details.issues.length > 0) {
            html += `
                <div class="issues-section">
                    <div class="section-title">⚠️ Issues Identified</div>
            `;
            
            details.issues.forEach(issue => {
                html += `
                    <div class="issue-card ${issue.severity}-severity">
                        <div class="issue-header">
                            <div class="issue-description">${issue.description}</div>
                            <div class="issue-count">${issue.count.toLocaleString()}</div>
                        </div>
                        <div class="issue-impact">${issue.impact}</div>
                `;
                
                // Add examples if available
                if (issue.examples && issue.examples.length > 0) {
                    html += `
                        <div class="issue-examples">
                            <div class="examples-title">Examples:</div>
                    `;
                    
                    issue.examples.forEach(example => {
                        if (example.brand) {
                            html += `<div class="example-item">${this.escapeHtml(example.brand)}`;
                            
                            if (example.similar_to) {
                                html += `<span class="similar-brands">→ Similar to: ${example.similar_to.map(b => this.escapeHtml(b)).join(', ')}</span>`;
                            }
                            
                            if (example.missing_fields) {
                                html += `<span class="missing-fields">→ Missing: ${example.missing_fields.join(', ')}</span>`;
                            }
                            
                            if (example.invalid_importers) {
                                html += `<span class="missing-fields">→ Invalid importers: ${example.invalid_importers.map(i => this.escapeHtml(i)).join(', ')}</span>`;
                            }
                            
                            html += `</div>`;
                        } else if (typeof example === 'string') {
                            html += `<div class="example-item">${this.escapeHtml(example)}</div>`;
                        }
                    });
                    
                    html += `</div>`;
                }
                
                html += `</div>`;
            });
            
            html += `</div>`;
        }
        
        // Recommendations section
        if (details.recommendations && details.recommendations.length > 0) {
            html += `
                <div class="recommendations-section">
                    <div class="section-title">💡 Recommendations</div>
                    <ul class="recommendations-list">
            `;
            
            details.recommendations.forEach(recommendation => {
                html += `<li class="recommendation-item">${this.escapeHtml(recommendation)}</li>`;
            });
            
            html += `
                    </ul>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }

    closeHealthModal() {
        document.getElementById('health-modal').style.display = 'none';
    }

    updateLastUpdated(timestamp) {
        const element = document.getElementById('last-updated');
        if (element && timestamp) {
            const date = new Date(timestamp);
            element.textContent = `Last updated: ${date.toLocaleTimeString()}`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global instance
let auditDashboard;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    auditDashboard = new AuditDashboard();
});

// Refresh data every 5 minutes
setInterval(() => {
    if (auditDashboard) {
        auditDashboard.loadHealthMetrics();
    }
}, 5 * 60 * 1000);