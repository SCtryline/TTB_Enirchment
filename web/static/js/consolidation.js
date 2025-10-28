/**
 * Brand Consolidation Page JavaScript
 * Handles all consolidation analysis and UI interactions
 */

class ConsolidationManager {
    constructor() {
        this.init();
    }

    init() {
        this.loadSystemStatus();
        this.bindEvents();
    }

    bindEvents() {
        // Main action buttons
        document.getElementById('run-analysis')?.addEventListener('click', () => this.runConsolidationAnalysis());
        document.getElementById('generate-proposals')?.addEventListener('click', () => this.generateProposals());
        document.getElementById('test-extraction')?.addEventListener('click', () => this.testBrandExtraction());
        document.getElementById('analyze-white-labels')?.addEventListener('click', () => this.analyzeWhiteLabels());
        
        // Confidence checker
        document.getElementById('check-confidence')?.addEventListener('click', () => this.checkConfidence());
        
        // Proposal filter
        document.getElementById('proposal-filter')?.addEventListener('change', () => this.filterProposals());
        
        // Enter key support for confidence checker
        document.getElementById('brand1')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.checkConfidence();
        });
        document.getElementById('brand2')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.checkConfidence();
        });
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/consolidation/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateStatusDisplay(data.status);
            } else {
                this.showError('Failed to load system status');
            }
        } catch (error) {
            console.error('Error loading system status:', error);
            this.showError('Error loading system status');
        }
    }

    updateStatusDisplay(status) {
        // Update status indicators
        document.getElementById('system-status').textContent = status.consolidation_enabled ? 'Active' : 'Inactive';
        document.getElementById('producer-data').textContent = 
            `${status.producer_data_available.spirit_producers.toLocaleString()} spirits, ${status.producer_data_available.wine_producers.toLocaleString()} wine`;
        document.getElementById('white-label-status').textContent = status.white_label_detection ? 'Enabled' : 'Disabled';
        
        // Update status indicator colors
        document.getElementById('system-status').className = 'indicator-value ' + (status.consolidation_enabled ? 'status-active' : 'status-inactive');
        document.getElementById('white-label-status').className = 'indicator-value ' + (status.white_label_detection ? 'status-active' : 'status-inactive');
    }

    async runConsolidationAnalysis() {
        const button = document.getElementById('run-analysis');
        const limit = document.getElementById('analysis-limit').value;
        
        try {
            this.setButtonLoading(button, 'Analyzing...');
            this.hideAllResults();
            
            const response = await fetch(`/consolidation/find_groups?limit=${limit}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayConsolidationGroups(data);
            } else {
                this.showError('Failed to run consolidation analysis: ' + data.error);
            }
        } catch (error) {
            console.error('Error running consolidation analysis:', error);
            this.showError('Error running consolidation analysis');
        } finally {
            this.setButtonLoading(button, 'Find Consolidation Groups', false);
        }
    }

    async testBrandExtraction() {
        const button = document.getElementById('test-extraction');
        
        try {
            this.setButtonLoading(button, 'Testing...');
            this.hideAllResults();
            
            const response = await fetch('/consolidation/test_extraction');
            const data = await response.json();
            
            if (data.success) {
                this.displayExtractionResults(data);
            } else {
                this.showError('Failed to test brand extraction: ' + data.error);
            }
        } catch (error) {
            console.error('Error testing brand extraction:', error);
            this.showError('Error testing brand extraction');
        } finally {
            this.setButtonLoading(button, 'Test Brand Extraction', false);
        }
    }

    async analyzeWhiteLabels() {
        const button = document.getElementById('analyze-white-labels');
        
        try {
            this.setButtonLoading(button, 'Analyzing...');
            this.hideAllResults();
            
            const response = await fetch('/consolidation/white_label_analysis');
            const data = await response.json();
            
            if (data.success) {
                this.displayWhiteLabelResults(data);
            } else {
                this.showError('Failed to analyze white labels: ' + data.error);
            }
        } catch (error) {
            console.error('Error analyzing white labels:', error);
            this.showError('Error analyzing white labels');
        } finally {
            this.setButtonLoading(button, 'Analyze White Labels', false);
        }
    }

    async checkConfidence() {
        const brand1 = document.getElementById('brand1').value.trim();
        const brand2 = document.getElementById('brand2').value.trim();
        const resultDiv = document.getElementById('confidence-result');
        
        if (!brand1 || !brand2) {
            this.showError('Please enter both brand names');
            return;
        }
        
        try {
            const response = await fetch(`/consolidation/confidence?brand1=${encodeURIComponent(brand1)}&brand2=${encodeURIComponent(brand2)}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayConfidenceResult(data, resultDiv);
            } else {
                this.showError('Failed to check confidence: ' + data.error);
            }
        } catch (error) {
            console.error('Error checking confidence:', error);
            this.showError('Error checking confidence');
        }
    }

    displayConsolidationGroups(data) {
        const container = document.getElementById('consolidation-groups-container');
        const resultsCard = document.getElementById('consolidation-results');
        
        // Update summary stats
        document.getElementById('groups-count').textContent = `${data.total_groups} groups`;
        document.getElementById('brands-affected').textContent = `${data.total_brands_affected} brands affected`;
        
        // Clear and populate groups
        container.innerHTML = '';
        
        if (data.groups.length === 0) {
            container.innerHTML = '<p class="no-results">No consolidation groups found in the analyzed brands.</p>';
        } else {
            data.groups.forEach(group => {
                const groupElement = this.createGroupElement(group);
                container.appendChild(groupElement);
            });
        }
        
        resultsCard.style.display = 'block';
    }

    createGroupElement(group) {
        const div = document.createElement('div');
        div.className = 'consolidation-group';
        
        div.innerHTML = `
            <div class="group-header">
                <div class="canonical-name">${this.escapeHtml(group.canonical_name)}</div>
                <div class="group-stats">
                    <span class="stat-badge">${group.brand_count} brands</span>
                    <span class="stat-badge">${group.total_skus} SKUs</span>
                </div>
            </div>
            <div class="brand-list-group">
                <h4>Brands in Group:</h4>
                <div class="brand-items">
                    ${group.brands.map(brand => `<span class="brand-item">${this.escapeHtml(brand)}</span>`).join('')}
                </div>
            </div>
            <div class="metadata-row">
                <div class="metadata-item">
                    <strong>Countries:</strong> ${group.countries.join(', ')}
                </div>
                <div class="metadata-item">
                    <strong>Categories:</strong> ${group.class_types.slice(0, 3).join(', ')}${group.class_types.length > 3 ? '...' : ''}
                </div>
            </div>
        `;
        
        return div;
    }

    displayExtractionResults(data) {
        const tableBody = document.getElementById('extraction-table-body');
        const resultsCard = document.getElementById('extraction-results');
        
        // Update summary stats
        document.getElementById('extraction-count').textContent = `${data.sample_size} brands analyzed`;
        
        // Clear and populate table
        tableBody.innerHTML = '';
        
        data.results.forEach(result => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(result.original_name)}</td>
                <td><strong>${this.escapeHtml(result.core_brand)}</strong></td>
                <td>${this.escapeHtml(result.producer_name || 'N/A')}</td>
                <td>${this.escapeHtml(result.class_type)}</td>
                <td>${result.sku_count}</td>
            `;
            tableBody.appendChild(row);
        });
        
        resultsCard.style.display = 'block';
    }

    displayWhiteLabelResults(data) {
        const whiteLabelList = document.getElementById('white-label-list');
        const regularLabelList = document.getElementById('regular-label-list');
        const resultsCard = document.getElementById('white-label-results');
        
        // Update summary stats
        document.getElementById('white-label-count').textContent = `${data.white_label_count} white label brands`;
        document.getElementById('white-label-percentage').textContent = `${data.white_label_percentage}%`;
        
        // Clear and populate white label brands
        whiteLabelList.innerHTML = '';
        data.white_label_brands.forEach(brand => {
            const item = this.createBrandListItem(brand);
            whiteLabelList.appendChild(item);
        });
        
        // Clear and populate regular brands
        regularLabelList.innerHTML = '';
        data.regular_brands.forEach(brand => {
            const item = this.createBrandListItem(brand);
            regularLabelList.appendChild(item);
        });
        
        resultsCard.style.display = 'block';
    }

    createBrandListItem(brand) {
        const div = document.createElement('div');
        div.className = 'brand-list-item';
        
        div.innerHTML = `
            <h5>${this.escapeHtml(brand.brand_name)}</h5>
            <div class="brand-meta">
                ${brand.sku_count} SKUs | 
                ${brand.countries.join(', ') || 'No country data'} | 
                ${brand.class_types.slice(0, 2).join(', ') || 'No category data'}
            </div>
        `;
        
        return div;
    }

    displayConfidenceResult(data, container) {
        const confidenceLevel = data.confidence >= 0.8 ? 'high' : data.confidence >= 0.5 ? 'medium' : 'low';
        const recommendation = data.should_consolidate ? 'recommend-consolidate' : 'recommend-no-consolidate';
        
        container.innerHTML = `
            <div class="confidence-score confidence-${confidenceLevel}">
                ${Math.round(data.confidence * 100)}% Confidence
            </div>
            <div class="confidence-reason">
                ${this.escapeHtml(data.reason)}
            </div>
            <div class="confidence-recommendation ${recommendation}">
                ${data.should_consolidate ? '✅ Recommend Consolidation' : '❌ Do Not Consolidate'}
            </div>
        `;
        
        container.style.display = 'block';
    }

    async generateProposals() {
        const button = document.getElementById('generate-proposals');
        const limit = document.getElementById('analysis-limit').value;
        
        try {
            this.setButtonLoading(button, 'Generating...');
            this.hideAllResults();
            
            const response = await fetch(`/consolidation/generate_proposals?limit=${Math.min(limit, 200)}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayProposals(data.proposals);
            } else {
                this.showError('Failed to generate proposals: ' + data.error);
            }
        } catch (error) {
            console.error('Error generating proposals:', error);
            this.showError('Error generating proposals');
        } finally {
            this.setButtonLoading(button, 'Generate Proposals', false);
        }
    }

    displayProposals(proposalsData) {
        const container = document.getElementById('proposals-container');
        const resultsCard = document.getElementById('proposals-results');
        
        // Store proposals data for filtering
        this.currentProposals = proposalsData.proposals || [];
        
        // Update summary stats
        const totalProposals = this.currentProposals.length;
        const autoApproveCount = this.currentProposals.filter(p => p.recommendation === 'auto_approve').length;
        const manualReviewCount = this.currentProposals.filter(p => p.recommendation === 'manual_review').length;
        
        document.getElementById('proposals-count').textContent = `${totalProposals} proposals`;
        document.getElementById('auto-approve-count').textContent = `${autoApproveCount} auto-approve`;
        document.getElementById('manual-review-count').textContent = `${manualReviewCount} manual review`;
        
        // Clear and populate proposals
        container.innerHTML = '';
        
        if (this.currentProposals.length === 0) {
            container.innerHTML = '<p class="no-results">No consolidation proposals found.</p>';
        } else {
            this.renderProposals(this.currentProposals);
        }
        
        resultsCard.style.display = 'block';
    }

    renderProposals(proposals) {
        const container = document.getElementById('proposals-container');
        container.innerHTML = '';
        
        proposals.forEach(proposal => {
            const proposalElement = this.createProposalElement(proposal);
            container.appendChild(proposalElement);
        });
    }

    createProposalElement(proposal) {
        const div = document.createElement('div');
        div.className = `proposal-card ${proposal.proposal_type.replace('_', '-')}`;
        
        const confidencePercent = Math.round(proposal.confidence_score * 100);
        const riskClass = `risk-${proposal.risk_assessment.level}`;
        
        div.innerHTML = `
            <div class="risk-indicator ${riskClass}">
                ${proposal.risk_assessment.level.toUpperCase()} RISK
            </div>
            
            <div class="proposal-header">
                <div>
                    <div class="proposal-title">${this.escapeHtml(proposal.canonical_name)}</div>
                    <div class="proposal-meta">
                        <span>ID: ${proposal.id}</span>
                        <span>Created: ${new Date(proposal.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <div class="proposal-badges">
                    <span class="proposal-badge badge-confidence">${confidencePercent}% Confidence</span>
                    <span class="proposal-badge badge-type">${proposal.proposal_type.replace('_', ' ')}</span>
                    <span class="proposal-badge badge-recommendation ${proposal.recommendation}">${proposal.recommendation.replace('_', ' ')}</span>
                </div>
            </div>
            
            <div class="proposal-content">
                <div class="proposal-brands">
                    <h4>Brands to Consolidate (${proposal.brand_count})</h4>
                    ${proposal.brand_details.map(brand => `
                        <div class="brand-consolidation-item ${brand.is_canonical ? 'canonical' : ''}">
                            <div class="brand-name">${this.escapeHtml(brand.brand_name)}</div>
                            <div class="brand-sku-count">${brand.sku_count} SKUs</div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="proposal-details">
                    <div class="detail-row">
                        <span class="detail-label">Total SKUs:</span>
                        <span class="detail-value">${proposal.total_skus}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Countries:</span>
                        <span class="detail-value">${proposal.summary.countries.join(', ')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Categories:</span>
                        <span class="detail-value">${proposal.summary.class_types.slice(0, 3).join(', ')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Producers:</span>
                        <span class="detail-value">${proposal.summary.producers.slice(0, 2).join(', ')}</span>
                    </div>
                    
                    <div class="confidence-factors">
                        <h5>Confidence Factors</h5>
                        ${Object.entries(proposal.confidence_factors)
                            .filter(([key, value]) => Math.abs(value) > 0.05)
                            .map(([key, value]) => {
                                const className = value > 0 ? 'factor-positive' : value < 0 ? 'factor-negative' : 'factor-neutral';
                                return `
                                    <div class="factor-item ${className}">
                                        <span>${key.replace(/_/g, ' ')}</span>
                                        <span>${value > 0 ? '+' : ''}${value.toFixed(2)}</span>
                                    </div>
                                `;
                            }).join('')}
                    </div>
                </div>
            </div>
            
            <div class="proposal-actions">
                <button class="btn-details" onclick="consolidationManager.showProposalDetails('${proposal.id}')">
                    View Details
                </button>
                <button class="btn-reject" onclick="consolidationManager.rejectProposal('${proposal.id}')">
                    Reject
                </button>
                <button class="btn-approve" onclick="consolidationManager.approveProposal('${proposal.id}')">
                    Approve
                </button>
            </div>
        `;
        
        return div;
    }

    filterProposals() {
        const filter = document.getElementById('proposal-filter').value;
        
        if (!this.currentProposals) {
            return;
        }
        
        let filteredProposals = this.currentProposals;
        
        switch (filter) {
            case 'manual_review':
                filteredProposals = this.currentProposals.filter(p => p.recommendation === 'manual_review');
                break;
            case 'auto_approve':
                filteredProposals = this.currentProposals.filter(p => p.recommendation === 'auto_approve');
                break;
            case 'high_confidence':
                filteredProposals = this.currentProposals.filter(p => p.proposal_type === 'high_confidence');
                break;
            case 'low_confidence':
                filteredProposals = this.currentProposals.filter(p => p.proposal_type === 'low_confidence');
                break;
            default:
                // 'all' - no filtering
                break;
        }
        
        this.renderProposals(filteredProposals);
    }

    async approveProposal(proposalId) {
        if (!confirm('Are you sure you want to approve this consolidation proposal?')) {
            return;
        }
        
        try {
            const response = await fetch(`/consolidation/approve_proposal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ proposal_id: proposalId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Proposal approved successfully!');
                // Remove the proposal from the UI
                document.querySelector(`[onclick*="${proposalId}"]`).closest('.proposal-card').remove();
            } else {
                this.showError('Failed to approve proposal: ' + data.error);
            }
        } catch (error) {
            console.error('Error approving proposal:', error);
            this.showError('Error approving proposal');
        }
    }

    async rejectProposal(proposalId) {
        const reason = prompt('Please provide a reason for rejection (optional):');
        
        if (reason === null) { // User cancelled
            return;
        }
        
        try {
            const response = await fetch(`/consolidation/reject_proposal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ proposal_id: proposalId, reason: reason })
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Proposal rejected successfully!');
                // Remove the proposal from the UI
                document.querySelector(`[onclick*="${proposalId}"]`).closest('.proposal-card').remove();
            } else {
                this.showError('Failed to reject proposal: ' + data.error);
            }
        } catch (error) {
            console.error('Error rejecting proposal:', error);
            this.showError('Error rejecting proposal');
        }
    }

    showProposalDetails(proposalId) {
        const proposal = this.currentProposals.find(p => p.id === proposalId);
        if (!proposal) {
            this.showError('Proposal not found');
            return;
        }
        
        // Create detailed modal/popup (simplified for now)
        alert(`Detailed view for proposal ${proposalId} would open here.\n\nBenefits:\n${proposal.benefits.primary_benefits.join('\n')}\n\nRisks:\n${proposal.risk_assessment.risks.join('\n')}`);
    }

    hideAllResults() {
        document.getElementById('consolidation-results').style.display = 'none';
        document.getElementById('extraction-results').style.display = 'none';
        document.getElementById('white-label-results').style.display = 'none';
        document.getElementById('proposals-results').style.display = 'none';
        document.getElementById('confidence-result').style.display = 'none';
    }

    setButtonLoading(button, text, loading = true) {
        if (loading) {
            button.disabled = true;
            button.textContent = text;
        } else {
            button.disabled = false;
            button.textContent = text;
        }
    }

    showError(message) {
        console.error(message);
        // You could implement a toast notification or modal here
        alert(message);
    }

    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }
}

// Initialize when DOM is loaded
let consolidationManager;
document.addEventListener('DOMContentLoaded', function() {
    consolidationManager = new ConsolidationManager();
});

// Add some CSS for status colors
const style = document.createElement('style');
style.textContent = `
    .status-active {
        background: #10b981 !important;
    }
    .status-inactive {
        background: #ef4444 !important;
    }
    .no-results {
        text-align: center;
        color: var(--text-secondary);
        font-style: italic;
        padding: 2rem;
    }
`;
document.head.appendChild(style);