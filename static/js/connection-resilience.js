/**
 * Client-side connection resilience and retry functionality.
 * Handles graceful reconnects, form data preservation, and user notifications.
 */

class ConnectionResilience {
    constructor() {
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        this.exponentialBackoff = true;
        this.connectionStatus = 'connected';
        this.pendingRequests = new Map();
        this.formDataCache = new Map();
        
        this.init();
    }
    
    init() {
        this.setupConnectionMonitoring();
        this.setupFormDataPreservation();
        this.setupRetryMechanisms();
        this.setupUserNotifications();
    }
    
    /**
     * Monitor connection status and handle reconnects
     */
    setupConnectionMonitoring() {
        // Monitor online/offline events
        window.addEventListener('online', () => {
            this.connectionStatus = 'connected';
            this.showNotification('Connection restored', 'success');
            this.retryPendingRequests();
        });
        
        window.addEventListener('offline', () => {
            this.connectionStatus = 'disconnected';
            this.showNotification('Connection lost', 'warning');
        });
        
        // Monitor AJAX requests for connection issues
        this.interceptAjaxRequests();
        
        // Periodic connection health check
        setInterval(() => {
            this.checkConnectionHealth();
        }, 30000); // Check every 30 seconds
    }
    
    /**
     * Intercept AJAX requests to handle connection failures
     */
    interceptAjaxRequests() {
        const originalFetch = window.fetch;
        const self = this;
        
        window.fetch = async function(...args) {
            const requestId = self.generateRequestId();
            const startTime = Date.now();
            
            try {
                const response = await originalFetch(...args);
                
                // Check for connection status in response headers
                const connectionStatus = response.headers.get('X-Connection-Status');
                if (connectionStatus === 'disconnected') {
                    self.connectionStatus = 'disconnected';
                    self.showNotification('Database connection lost', 'error');
                }
                
                return response;
            } catch (error) {
                if (self.isConnectionError(error)) {
                    self.handleConnectionError(requestId, args, error);
                }
                throw error;
            }
        };
    }
    
    /**
     * Setup form data preservation for POST requests
     */
    setupFormDataPreservation() {
        // Save form data before submission
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.method.toLowerCase() === 'post') {
                this.saveFormData(form);
            }
        });
        
        // Restore form data on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.restoreFormData();
        });
    }
    
    /**
     * Setup retry mechanisms for failed requests
     */
    setupRetryMechanisms() {
        // Add retry buttons to error messages
        this.addRetryButtons();
    }
    
    /**
     * Setup user notifications for connection issues
     */
    setupUserNotifications() {
        // Create notification container
        const notificationContainer = document.createElement('div');
        notificationContainer.id = 'connection-notifications';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(notificationContainer);
    }
    
    /**
     * Check connection health
     */
    async checkConnectionHealth() {
        try {
            const response = await fetch('/health/simple/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                this.connectionStatus = 'connected';
            } else {
                this.connectionStatus = 'disconnected';
            }
        } catch (error) {
            this.connectionStatus = 'disconnected';
        }
        
        this.updateConnectionIndicator();
    }
    
    /**
     * Update connection status indicator
     */
    updateConnectionIndicator() {
        let indicator = document.getElementById('connection-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'connection-indicator';
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                left: 10px;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 12px;
                z-index: 9999;
                font-family: monospace;
            `;
            document.body.appendChild(indicator);
        }
        
        const status = this.connectionStatus;
        indicator.textContent = `DB: ${status}`;
        indicator.style.backgroundColor = status === 'connected' ? '#d4edda' : '#f8d7da';
        indicator.style.color = status === 'connected' ? '#155724' : '#721c24';
    }
    
    /**
     * Handle connection errors
     */
    handleConnectionError(requestId, requestArgs, error) {
        this.connectionStatus = 'disconnected';
        
        // Store request for retry
        this.pendingRequests.set(requestId, {
            args: requestArgs,
            timestamp: Date.now(),
            retryCount: 0
        });
        
        this.showNotification('Connection lost. Retrying...', 'warning');
    }
    
    /**
     * Retry pending requests
     */
    async retryPendingRequests() {
        for (const [requestId, requestData] of this.pendingRequests) {
            if (requestData.retryCount < this.maxRetries) {
                try {
                    await this.retryRequest(requestId, requestData);
                } catch (error) {
                    console.error('Retry failed:', error);
                }
            }
        }
    }
    
    /**
     * Retry a specific request
     */
    async retryRequest(requestId, requestData) {
        const delay = this.calculateRetryDelay(requestData.retryCount);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
            const response = await fetch(...requestData.args);
            this.pendingRequests.delete(requestId);
            this.showNotification('Request retried successfully', 'success');
            return response;
        } catch (error) {
            requestData.retryCount++;
            if (requestData.retryCount >= this.maxRetries) {
                this.pendingRequests.delete(requestId);
                this.showNotification('Request failed after retries', 'error');
            }
            throw error;
        }
    }
    
    /**
     * Calculate retry delay with exponential backoff
     */
    calculateRetryDelay(retryCount) {
        if (this.exponentialBackoff) {
            return this.retryDelay * Math.pow(2, retryCount);
        }
        return this.retryDelay;
    }
    
    /**
     * Check if error is connection-related
     */
    isConnectionError(error) {
        const connectionErrors = [
            'NetworkError',
            'TypeError',
            'Failed to fetch',
            'Connection refused',
            'timeout'
        ];
        
        return connectionErrors.some(errorType => 
            error.message.includes(errorType) || error.name === errorType
        );
    }
    
    /**
     * Save form data for potential restoration
     */
    saveFormData(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        const formId = form.id || form.action || 'default';
        this.formDataCache.set(formId, data);
        
        // Store in localStorage as backup
        try {
            localStorage.setItem(`form_draft_${formId}`, JSON.stringify(data));
        } catch (e) {
            console.warn('Could not save form data to localStorage:', e);
        }
    }
    
    /**
     * Restore form data from cache
     */
    restoreFormData() {
        // Check for draft data in localStorage
        const forms = document.querySelectorAll('form[method="post"]');
        
        forms.forEach(form => {
            const formId = form.id || form.action || 'default';
            
            try {
                const draftData = localStorage.getItem(`form_draft_${formId}`);
                if (draftData) {
                    const data = JSON.parse(draftData);
                    this.populateForm(form, data);
                    this.showNotification('Draft data restored', 'info');
                }
            } catch (e) {
                console.warn('Could not restore form data:', e);
            }
        });
    }
    
    /**
     * Populate form with saved data
     */
    populateForm(form, data) {
        for (const [name, value] of Object.entries(data)) {
            const field = form.querySelector(`[name="${name}"]`);
            if (field) {
                if (field.type === 'checkbox' || field.type === 'radio') {
                    field.checked = value === 'on' || value === field.value;
                } else {
                    field.value = value;
                }
            }
        }
    }
    
    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        const container = document.getElementById('connection-notifications');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            padding: 10px 15px;
            margin-bottom: 10px;
            border-radius: 4px;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
        `;
        
        // Set colors based on type
        const colors = {
            success: { bg: '#d4edda', color: '#155724' },
            warning: { bg: '#fff3cd', color: '#856404' },
            error: { bg: '#f8d7da', color: '#721c24' },
            info: { bg: '#d1ecf1', color: '#0c5460' }
        };
        
        const colorScheme = colors[type] || colors.info;
        notification.style.backgroundColor = colorScheme.bg;
        notification.style.color = colorScheme.color;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    /**
     * Add retry buttons to error messages
     */
    addRetryButtons() {
        // Look for error messages and add retry buttons
        const errorMessages = document.querySelectorAll('.error, .alert-danger');
        errorMessages.forEach(message => {
            if (!message.querySelector('.retry-button')) {
                const retryButton = document.createElement('button');
                retryButton.className = 'retry-button btn btn-sm btn-outline-primary';
                retryButton.textContent = 'Retry';
                retryButton.style.marginLeft = '10px';
                
                retryButton.addEventListener('click', () => {
                    this.retryLastAction();
                });
                
                message.appendChild(retryButton);
            }
        });
    }
    
    /**
     * Retry last action
     */
    retryLastAction() {
        // This would be implemented based on the specific action that failed
        window.location.reload();
    }
    
    /**
     * Generate unique request ID
     */
    generateRequestId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// Initialize connection resilience when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.connectionResilience = new ConnectionResilience();
});

// Add CSS for notifications
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
    
    .notification {
        transition: all 0.3s ease;
    }
    
    .retry-button {
        cursor: pointer;
    }
`;
document.head.appendChild(style);
