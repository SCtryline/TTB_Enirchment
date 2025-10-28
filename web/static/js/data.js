// Load producer stats
async function loadProducerStats() {
    try {
        const response = await fetch('/get_producer_stats');
        const data = await response.json();
        
        if (data.spirit_producers !== undefined) {
            document.getElementById('spirit-producers-count').textContent = 
                `${data.spirit_producers} spirit producers loaded`;
        }
        
        if (data.wine_producers !== undefined) {
            document.getElementById('wine-producers-count').textContent = 
                `${data.wine_producers} wine producers loaded`;
        }
    } catch (error) {
        console.error('Error loading producer stats:', error);
        document.getElementById('spirit-producers-count').textContent = 'Error loading count';
        document.getElementById('wine-producers-count').textContent = 'Error loading count';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize data management page
    loadSystemStatus();
    loadMatchedFiles();
    setupFileInputs();
    
    // Setup form submissions
    setupUploadForms();
    
    // Load producer stats
    loadProducerStats();
    
    // Apollo.io integration
    loadApolloStatus();
    setupApolloImportHandler();
});

// Load current system status
async function loadSystemStatus() {
    try {
        const response = await fetch('/get_database_stats');
        const stats = await response.json();
        
        // Update status displays
        document.getElementById('importers-count').textContent = 
            `${stats.total_importers || 0} importers loaded`;
        document.getElementById('brands-count').textContent = 
            `${stats.total_brands || 0} brands processed`;
            
        // Update database status section
        document.getElementById('status-brands').textContent = stats.total_brands || 0;
        document.getElementById('status-skus').textContent = stats.total_skus || 0;
        document.getElementById('status-importers').textContent = stats.total_importers || 0;
        
        // Get last upload info
        const uploadResponse = await fetch('/get_matched_files');
        const uploadData = await uploadResponse.json();
        
        if (uploadData.files && uploadData.files.length > 0) {
            const lastFile = uploadData.files[uploadData.files.length - 1];
            document.getElementById('status-last-upload').textContent = lastFile.created || 'Never';
        } else {
            document.getElementById('status-last-upload').textContent = 'Never';
        }
        
    } catch (error) {
        console.error('Failed to load system status:', error);
        document.getElementById('importers-count').textContent = 'Error loading';
        document.getElementById('brands-count').textContent = 'Error loading';
    }
}

// Load matched files for export section
async function loadMatchedFiles() {
    try {
        const response = await fetch('/get_matched_files');
        const data = await response.json();
        
        const container = document.getElementById('matched-files-list');
        
        if (!data.files || data.files.length === 0) {
            container.innerHTML = `
                <div class="loading-export">
                    No upload history available.
                    Upload COLA data to see processing history.
                </div>
            `;
            return;
        }
        
        // Display upload history with better formatting
        container.innerHTML = `
            <div style="max-height: 300px; overflow-y: auto;">
                ${data.files.map(file => `
                    <div style="margin-bottom: 15px; padding: 10px; border: 1px solid #e1e5e9; border-radius: 8px; background: #f8f9fa;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="font-weight: 600; color: #2c3e50;">📊 ${file.filename}</span>
                            <span style="font-size: 0.85rem; color: #6c757d;">${file.created ? new Date(file.created).toLocaleDateString() : ''}</span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 0.85rem; color: #495057;">
                            <span>📝 Total: ${file.rows} records</span>
                            <span>🔗 Matched: ${file.matched || 0}</span>
                            <span>🏷️ New Brands: ${file.new_brands || 0}</span>
                            <span>📦 New SKUs: ${file.new_skus || 0}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                <button class="export-btn" onclick="window.location.href='/dashboard'" style="width: 100%; background: #2563eb; color: white; font-weight: 600;">
                    <span class="btn-icon">📊</span>
                    Go to Dashboard for Advanced Exports
                </button>
            </div>
        `;
        
    } catch (error) {
        console.error('Failed to load upload history:', error);
        document.getElementById('matched-files-list').innerHTML = `
            <div class="loading-export">Error loading upload history</div>
        `;
    }
}

// Setup file input visual feedback
function setupFileInputs() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const label = this.nextElementSibling;
            if (this.files.length > 0) {
                label.textContent = `📁 Selected: ${this.files[0].name}`;
                label.style.borderColor = '#667eea';
                label.style.backgroundColor = '#f0f4ff';
            } else {
                label.textContent = label.getAttribute('data-original') || '📁 Choose File';
                label.style.borderColor = '#dee2e6';
                label.style.backgroundColor = '#f8f9fa';
            }
        });
        
        // Store original text
        const label = input.nextElementSibling;
        label.setAttribute('data-original', label.textContent);
    });
}

// Setup upload forms
function setupUploadForms() {
    // Importers form
    document.getElementById('importers-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleUpload('importersFile', 'importers-results', '/upload_importers');
    });
    
    // COLA form
    document.getElementById('cola-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleUpload('colaFile', 'cola-results', '/upload_cola');
    });
    
    // Spirit Producers form
    document.getElementById('spirit-producers-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleUpload('spiritProducersFile', 'spirit-producers-results', '/upload_spirit_producers');
    });
    
    // Wine Producers form
    document.getElementById('wine-producers-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleUpload('wineProducersFile', 'wine-producers-results', '/upload_wine_producers');
    });
}

// Handle file uploads
async function handleUpload(fileInputId, resultsId, endpoint) {
    const fileInput = document.getElementById(fileInputId);
    const resultsDiv = document.getElementById(resultsId);
    const submitBtn = fileInput.closest('form').querySelector('button[type="submit"]');
    
    // Validate file selection
    if (!fileInput.files || fileInput.files.length === 0) {
        showResult(resultsDiv, 'error', 'Please select a file to upload');
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';
    showResult(resultsDiv, 'info', 'Uploading file, please wait...');
    
    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult(resultsDiv, 'success', result.message);
            // Refresh system status after successful upload
            setTimeout(() => {
                loadSystemStatus();
                loadMatchedFiles();
            }, 1000);
        } else {
            showResult(resultsDiv, 'error', result.error || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showResult(resultsDiv, 'error', `Upload failed: ${error.message}`);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.textContent = submitBtn.textContent.replace('Uploading...', 
            submitBtn.id === 'importers-submit' ? 'Upload Importers' : 'Process COLA Data');
    }
}

// Show result message
function showResult(container, type, message) {
    container.innerHTML = `
        <div class="status-box ${type}">
            ${message}
        </div>
    `;
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    }
}

// Export data functions
async function exportData(exportType) {
    const exportBtn = event.target;
    const originalText = exportBtn.textContent;
    
    exportBtn.disabled = true;
    exportBtn.innerHTML = '<span class="btn-icon">⏳</span> Generating...';
    
    try {
        let endpoint;
        let filename;
        
        switch (exportType) {
            case 'brands-csv':
                endpoint = '/export_brands_csv';
                filename = 'brands_with_importers.csv';
                break;
            case 'brands-no-importers':
                endpoint = '/export_brands_no_importers';
                filename = 'brands_no_importers.csv';
                break;
            case 'brands-with-skus':
                endpoint = '/export_brands_with_skus';
                filename = 'brands_with_skus.csv';
                break;
            case 'unmatched-brands':
                endpoint = '/export_unmatched_brands';
                filename = 'unmatched_brands.csv';
                break;
            case 'importers-csv':
                endpoint = '/export_importers_csv';
                filename = 'importers_export.csv';
                break;
            case 'importers-with-brands':
                endpoint = '/export_active_importers';
                filename = 'active_importers.csv';
                break;
            case 'importer-rankings':
                endpoint = '/export_importer_rankings';
                filename = 'importer_leaderboard.csv';
                break;
            case 'system-summary':
                endpoint = '/export_system_summary';
                filename = 'system_summary.pdf';
                break;
            case 'analytics-report':
                endpoint = '/export_analytics_report';
                filename = 'analytics_report.csv';
                break;
            case 'all-data-package':
                endpoint = '/export_complete_package';
                filename = 'ttb_data_package.zip';
                break;
            default:
                throw new Error('Unknown export type');
        }
        
        const response = await fetch(endpoint);
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Show success message
        showTemporaryMessage('Export completed successfully!', 'success');
        
    } catch (error) {
        console.error('Export error:', error);
        showTemporaryMessage(`Export failed: ${error.message}`, 'error');
    } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = originalText;
    }
}

// Download matched file
async function downloadMatchedFile(filename) {
    try {
        const response = await fetch(`/download_matched_file/${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            throw new Error(`Download failed: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showTemporaryMessage('Download started!', 'success');
        
    } catch (error) {
        console.error('Download error:', error);
        showTemporaryMessage(`Download failed: ${error.message}`, 'error');
    }
}

// Refresh system status
async function refreshStatus() {
    const refreshBtn = event.target;
    const originalIcon = refreshBtn.querySelector('.action-icon').textContent;
    
    refreshBtn.querySelector('.action-icon').textContent = '⏳';
    refreshBtn.disabled = true;
    
    try {
        await loadSystemStatus();
        await loadMatchedFiles();
        showTemporaryMessage('Status refreshed successfully!', 'success');
    } catch (error) {
        showTemporaryMessage('Failed to refresh status', 'error');
    } finally {
        refreshBtn.querySelector('.action-icon').textContent = originalIcon;
        refreshBtn.disabled = false;
    }
}

// View upload history
async function viewUploadHistory() {
    try {
        const response = await fetch('/get_matched_files');
        const data = await response.json();
        
        if (!data.files || data.files.length === 0) {
            alert('No upload history available.');
            return;
        }
        
        const historyText = data.files.map(file => 
            `${file.created}: ${file.filename} (${file.rows} records)`
        ).join('\n');
        
        alert(`Upload History:\n\n${historyText}`);
        
    } catch (error) {
        console.error('Failed to load upload history:', error);
        alert('Failed to load upload history.');
    }
}

// Reset database
async function resetDatabase() {
    const confirmReset = confirm(
        'Are you SURE you want to reset the database?\n\n' +
        'This will:\n' +
        '✓ Clear all brands and SKUs\n' +
        '✓ Clear upload history\n' +
        '✓ Keep importer data\n\n' +
        'You will need to re-upload your COLA CSV files.\n\n' +
        'This cannot be undone!'
    );
    
    if (!confirmReset) return;
    
    const resetBtn = event.target;
    const originalText = resetBtn.textContent;
    
    resetBtn.disabled = true;
    resetBtn.innerHTML = '<span class="action-icon">⏳</span> Resetting...';
    
    try {
        const response = await fetch('/reset_database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Database reset successful!\n\n${result.message}\n\nRemaining importers: ${result.remaining.master_importers}`);
            // Refresh page after successful reset
            window.location.reload();
        } else {
            alert(`Reset failed: ${result.error}`);
        }
        
    } catch (error) {
        console.error('Reset error:', error);
        alert(`Reset failed: ${error.message}`);
    } finally {
        resetBtn.disabled = false;
        resetBtn.innerHTML = originalText;
    }
}

// Show temporary message
function showTemporaryMessage(message, type) {
    // Create temporary message element
    const messageEl = document.createElement('div');
    messageEl.className = `status-box ${type}`;
    messageEl.style.position = 'fixed';
    messageEl.style.top = '20px';
    messageEl.style.right = '20px';
    messageEl.style.zIndex = '9999';
    messageEl.style.maxWidth = '300px';
    messageEl.textContent = message;
    
    document.body.appendChild(messageEl);
    
    // Remove after 3 seconds
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.parentNode.removeChild(messageEl);
        }
    }, 3000);
}

// Initialize file drag and drop
function initializeDragDrop() {
    const fileLabels = document.querySelectorAll('.file-label');
    
    fileLabels.forEach(label => {
        const input = label.previousElementSibling;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            label.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            label.addEventListener(eventName, () => {
                label.style.borderColor = '#667eea';
                label.style.backgroundColor = '#f0f4ff';
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            label.addEventListener(eventName, () => {
                label.style.borderColor = '#dee2e6';
                label.style.backgroundColor = '#f8f9fa';
            }, false);
        });
        
        label.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                label.textContent = `📁 Selected: ${files[0].name}`;
                label.style.borderColor = '#667eea';
                label.style.backgroundColor = '#f0f4ff';
            }
        }, false);
    });
}

// Call drag drop initialization after DOM is loaded
document.addEventListener('DOMContentLoaded', initializeDragDrop);

// Apollo.io Integration Functions
async function loadApolloStatus() {
    try {
        const response = await fetch('/get_apollo_status');
        const data = await response.json();
        
        const statusEl = document.getElementById('apollo-status');
        if (statusEl) {
            statusEl.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 0.875rem;">
                    <div>
                        <span style="color: #6b7280;">Total Brands:</span>
                        <strong style="color: #111827;">${data.total_brands}</strong>
                    </div>
                    <div>
                        <span style="color: #6b7280;">Enriched:</span>
                        <strong style="color: #10b981;">${data.enriched_brands}</strong>
                    </div>
                    <div>
                        <span style="color: #6b7280;">With Websites:</span>
                        <strong style="color: #2563eb;">${data.brands_with_websites}</strong>
                    </div>
                    <div>
                        <span style="color: #6b7280;">Progress:</span>
                        <strong style="color: ${data.enrichment_percentage > 50 ? '#10b981' : '#f59e0b'};">
                            ${data.enrichment_percentage}%
                        </strong>
                    </div>
                </div>
                ${data.brands_with_websites > 0 ? `
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5e7eb;">
                        <span style="color: #10b981; font-size: 0.875rem;">
                            ✅ ${data.brands_with_websites} brands ready for Apollo campaigns
                        </span>
                    </div>
                ` : `
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5e7eb;">
                        <span style="color: #f59e0b; font-size: 0.875rem;">
                            ⚠️ No enriched brands yet. Follow steps 1-3 to enrich your data.
                        </span>
                    </div>
                `}
            `;
            
            // Enable/disable final export button based on status
            const finalBtn = document.getElementById('apollo-final-btn');
            if (finalBtn) {
                finalBtn.disabled = data.brands_with_websites === 0;
                if (data.brands_with_websites === 0) {
                    finalBtn.style.opacity = '0.5';
                    finalBtn.style.cursor = 'not-allowed';
                }
            }
        }
    } catch (error) {
        console.error('Failed to load Apollo status:', error);
    }
}

// Export for Apollo bulk enrichment
async function exportApollo() {
    try {
        const response = await fetch('/export_apollo_bulk');
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Export failed');
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `apollo_bulk_enrichment_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Show instructions
        alert(
            '✅ Apollo export completed!\n\n' +
            'Next steps:\n' +
            '1. Go to Apollo.io → Data Enrichment\n' +
            '2. Upload this CSV file\n' +
            '3. Apollo will find company websites and contact info\n' +
            '4. Download the enriched CSV from Apollo\n' +
            '5. Import it back here using Step 2'
        );
        
    } catch (error) {
        console.error('Apollo export error:', error);
        alert(`Export failed: ${error.message}`);
    }
}

// Export final Apollo-ready file with websites
async function exportApolloFinal() {
    try {
        const response = await fetch('/export_apollo_final');
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'No brands with websites found');
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Extract filename from response headers or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        const filename = contentDisposition ? 
            contentDisposition.split('filename=')[1].replace(/"/g, '') : 
            `apollo_final_${new Date().toISOString().split('T')[0]}.csv`;
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showTemporaryMessage('✅ Apollo-ready file exported successfully!', 'success');
        
    } catch (error) {
        console.error('Apollo final export error:', error);
        alert(`Export failed: ${error.message}\n\nMake sure you have imported enriched data from Apollo first.`);
    }
}

// Setup Apollo import handler
function setupApolloImportHandler() {
    const form = document.getElementById('apollo-import-form');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('apolloFile');
        const file = fileInput.files[0];
        
        if (!file) {
            alert('Please select an Apollo enriched CSV file');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Importing...';
        
        try {
            const response = await fetch('/import_apollo_enriched', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert(
                    `✅ Apollo data imported successfully!\n\n` +
                    `Processed: ${result.total_processed} records\n` +
                    `Updated brands: ${result.updated_brands}\n` +
                    `Websites added: ${result.websites_added}\n` +
                    `Not found: ${result.not_found}\n\n` +
                    `You can now export the final Apollo-ready file with websites.`
                );
                
                // Reset form and reload status
                form.reset();
                document.querySelector('label[for="apolloFile"]').textContent = '📁 Choose Apollo Enriched CSV';
                await loadApolloStatus();
                
            } else {
                alert(`Import failed: ${result.error}`);
            }
            
        } catch (error) {
            console.error('Apollo import error:', error);
            alert(`Import failed: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
    
    // Update label when file is selected
    const fileInput = document.getElementById('apolloFile');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const label = document.querySelector('label[for="apolloFile"]');
            if (this.files.length > 0) {
                label.textContent = `📁 Selected: ${this.files[0].name}`;
            }
        });
    }
}

// Apollo Filter Modal Functions
let apolloFilterOptions = null;

// Make function globally accessible
window.openApolloFilterModal = async function openApolloFilterModal() {
    console.log('Opening Apollo filter modal...');
    const modal = document.getElementById('apollo-filter-modal');
    if (!modal) {
        console.error('Apollo filter modal not found!');
        return;
    }
    
    modal.style.display = 'block';
    
    // Load filter options if not already loaded
    if (!apolloFilterOptions) {
        await loadApolloFilterOptions();
    }
    
    // Update stats
    updateFilterStats();
}

window.closeApolloFilterModal = function closeApolloFilterModal() {
    const modal = document.getElementById('apollo-filter-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadApolloFilterOptions() {
    try {
        const response = await fetch('/get_filter_options');
        apolloFilterOptions = await response.json();
        
        // Update stats
        document.getElementById('stats-total').textContent = apolloFilterOptions.stats.total_brands;
        document.getElementById('stats-enriched').textContent = apolloFilterOptions.stats.enriched_brands;
        document.getElementById('stats-not-enriched').textContent = apolloFilterOptions.stats.not_enriched;
        
        // Populate countries
        const countriesDiv = document.getElementById('countries-filter');
        if (apolloFilterOptions.countries.length > 0) {
            countriesDiv.innerHTML = apolloFilterOptions.countries.map(country => `
                <label style="display: block; padding: 4px; cursor: pointer;">
                    <input type="checkbox" value="${country}" class="country-filter" onchange="updateFilterStats()">
                    <span style="margin-left: 5px;">${country}</span>
                </label>
            `).join('');
        } else {
            countriesDiv.innerHTML = '<div style="color: #6b7280;">No countries available</div>';
        }
        
        // Populate class types
        const classTypesDiv = document.getElementById('class-types-filter');
        if (apolloFilterOptions.class_types.length > 0) {
            // Show first 20 class types with a show more option
            const displayTypes = apolloFilterOptions.class_types.slice(0, 20);
            classTypesDiv.innerHTML = displayTypes.map(type => `
                <label style="display: block; padding: 4px; cursor: pointer;">
                    <input type="checkbox" value="${type}" class="class-type-filter" onchange="updateFilterStats()">
                    <span style="margin-left: 5px; font-size: 0.875rem;">${type}</span>
                </label>
            `).join('');
            
            if (apolloFilterOptions.class_types.length > 20) {
                classTypesDiv.innerHTML += `
                    <div style="padding: 8px; text-align: center;">
                        <button onclick="showAllClassTypes()" style="color: #2563eb; text-decoration: underline; border: none; background: none; cursor: pointer;">
                            Show all ${apolloFilterOptions.class_types.length} types
                        </button>
                    </div>
                `;
            }
        } else {
            classTypesDiv.innerHTML = '<div style="color: #6b7280;">No class types available</div>';
        }
        
        // Populate importers
        const importersDiv = document.getElementById('importers-filter');
        if (apolloFilterOptions.importers.length > 0) {
            importersDiv.innerHTML = apolloFilterOptions.importers.map(importer => `
                <label style="display: block; padding: 4px; cursor: pointer;">
                    <input type="checkbox" value="${importer}" class="importer-filter" onchange="updateFilterStats()">
                    <span style="margin-left: 5px; font-size: 0.875rem;">${importer}</span>
                </label>
            `).join('');
        } else {
            importersDiv.innerHTML = '<div style="color: #6b7280;">No importers with brands available</div>';
        }
        
    } catch (error) {
        console.error('Failed to load filter options:', error);
        alert('Failed to load filter options. Please try again.');
    }
}

window.showAllClassTypes = function showAllClassTypes() {
    const classTypesDiv = document.getElementById('class-types-filter');
    classTypesDiv.innerHTML = apolloFilterOptions.class_types.map(type => `
        <label style="display: block; padding: 4px; cursor: pointer;">
            <input type="checkbox" value="${type}" class="class-type-filter" onchange="updateFilterStats()">
            <span style="margin-left: 5px; font-size: 0.875rem;">${type}</span>
        </label>
    `).join('');
}

function updateFilterStats() {
    // This would ideally make a request to get accurate counts based on filters
    // For now, just update the selected count based on visible changes
    const selectedCount = document.getElementById('stats-selected');
    
    // Count how many filters are active
    let filterCount = 0;
    if (document.getElementById('apollo-search').value) filterCount++;
    if (document.querySelectorAll('.country-filter:checked').length > 0) filterCount++;
    if (document.querySelectorAll('.class-type-filter:checked').length > 0) filterCount++;
    if (document.querySelectorAll('.importer-filter:checked').length > 0) filterCount++;
    
    // Update UI to show filters are active
    if (filterCount > 0) {
        selectedCount.textContent = 'Filtered';
        selectedCount.style.color = '#7c3aed';
    } else {
        selectedCount.textContent = apolloFilterOptions ? apolloFilterOptions.stats.total_brands : '0';
        selectedCount.style.color = '#2563eb';
    }
}

window.resetApolloFilters = function resetApolloFilters() {
    // Reset all form inputs
    document.getElementById('apollo-search').value = '';
    document.getElementById('min-skus').value = '0';
    document.getElementById('max-skus').value = '9999';
    
    // Reset radio buttons
    document.querySelector('input[name="enrichment-status"][value="all"]').checked = true;
    document.querySelector('input[name="match-status"][value="all"]').checked = true;
    
    // Uncheck all checkboxes
    document.getElementById('exclude-enriched').checked = false;
    document.querySelectorAll('.country-filter:checked').forEach(cb => cb.checked = false);
    document.querySelectorAll('.class-type-filter:checked').forEach(cb => cb.checked = false);
    document.querySelectorAll('.importer-filter:checked').forEach(cb => cb.checked = false);
    
    updateFilterStats();
}

window.previewFilteredBrands = async function previewFilteredBrands() {
    const filters = getApolloFilters();
    
    // Build query string
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.countries.length) params.append('countries', filters.countries.join(','));
    if (filters.classTypes.length) params.append('classTypes', filters.classTypes.join(','));
    if (filters.importers.length) params.append('importers', filters.importers.join(','));
    params.append('minSkus', filters.minSkus);
    params.append('maxSkus', filters.maxSkus);
    params.append('matchStatus', filters.matchStatus);
    params.append('enrichmentStatus', filters.enrichmentStatus);
    params.append('excludeEnriched', filters.excludeEnriched);
    
    // For preview, we'd ideally show a list of brands that match
    // For now, just alert the filter summary
    let summary = 'Filter Preview:\n\n';
    if (filters.search) summary += `Search: "${filters.search}"\n`;
    if (filters.countries.length) summary += `Countries: ${filters.countries.length} selected\n`;
    if (filters.classTypes.length) summary += `Class Types: ${filters.classTypes.length} selected\n`;
    if (filters.importers.length) summary += `Importers: ${filters.importers.length} selected\n`;
    summary += `SKU Range: ${filters.minSkus} - ${filters.maxSkus}\n`;
    summary += `Match Status: ${filters.matchStatus}\n`;
    summary += `Enrichment: ${filters.enrichmentStatus}\n`;
    if (filters.excludeEnriched) summary += `Excluding already enriched brands\n`;
    
    alert(summary);
}

function getApolloFilters() {
    return {
        search: document.getElementById('apollo-search').value.trim(),
        countries: Array.from(document.querySelectorAll('.country-filter:checked')).map(cb => cb.value),
        classTypes: Array.from(document.querySelectorAll('.class-type-filter:checked')).map(cb => cb.value),
        importers: Array.from(document.querySelectorAll('.importer-filter:checked')).map(cb => cb.value),
        minSkus: document.getElementById('min-skus').value || '0',
        maxSkus: document.getElementById('max-skus').value || '9999',
        matchStatus: document.querySelector('input[name="match-status"]:checked').value,
        enrichmentStatus: document.querySelector('input[name="enrichment-status"]:checked').value,
        excludeEnriched: document.getElementById('exclude-enriched').checked
    };
}

window.exportFilteredApollo = async function exportFilteredApollo() {
    try {
        const filters = getApolloFilters();
        
        // Build query string
        const params = new URLSearchParams();
        if (filters.search) params.append('search', filters.search);
        if (filters.countries.length) params.append('countries', filters.countries.join(','));
        if (filters.classTypes.length) params.append('classTypes', filters.classTypes.join(','));
        if (filters.importers.length) params.append('importers', filters.importers.join(','));
        params.append('minSkus', filters.minSkus);
        params.append('maxSkus', filters.maxSkus);
        params.append('matchStatus', filters.matchStatus);
        params.append('enrichmentStatus', filters.enrichmentStatus);
        params.append('excludeEnriched', filters.excludeEnriched);
        
        const response = await fetch(`/export_apollo_filtered?${params.toString()}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Export failed');
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Extract filename from response headers or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        const filename = contentDisposition ? 
            contentDisposition.split('filename=')[1].replace(/"/g, '') : 
            `apollo_filtered_${new Date().toISOString().split('T')[0]}.csv`;
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Close modal
        closeApolloFilterModal();
        
        // Show success message
        showTemporaryMessage('✅ Filtered Apollo export completed!', 'success');
        
        // Show instructions
        setTimeout(() => {
            alert(
                '✅ Filtered Apollo export completed!\n\n' +
                'Next steps:\n' +
                '1. Go to Apollo.io → Data Enrichment\n' +
                '2. Upload this CSV file\n' +
                '3. Apollo will find company websites and contact info\n' +
                '4. Download the enriched CSV from Apollo\n' +
                '5. Import it back here using Step 2'
            );
        }, 500);
        
    } catch (error) {
        console.error('Apollo filtered export error:', error);
        alert(`Export failed: ${error.message}`);
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('apollo-filter-modal');
    if (event.target === modal) {
        closeApolloFilterModal();
    }
}