/**
 * ShortTheHack - Reactive JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const startBotBtn = document.getElementById('startBot');
    const stopBotBtn = document.getElementById('stopBot');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const testBinanceBtn = document.getElementById('testBinanceBtn');
    const testClaudeBtn = document.getElementById('testClaudeBtn');
    const noTweetMessage = document.getElementById('noTweetMessage');
    const tweetContent = document.getElementById('tweetContent');
    const tweetText = document.getElementById('tweetText');
    const tweetDate = document.getElementById('tweetDate');
    const shortsListContainer = document.getElementById('shortsListContainer');
    const shortsList = document.getElementById('shortsList');
    const noShortsMessage = document.getElementById('noShortsMessage');
    
    // Function to show toast notifications instead of alerts
    function showToast(message, type = 'info') {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        
        const toastElement = document.createElement('div');
        toastElement.className = `toast text-white bg-${type}`;
        toastElement.setAttribute('role', 'alert');
        toastElement.setAttribute('aria-live', 'assertive');
        toastElement.setAttribute('aria-atomic', 'true');
        
        const toastFlex = document.createElement('div');
        toastFlex.className = 'd-flex';
        
        const toastBody = document.createElement('div');
        toastBody.className = 'toast-body';
        toastBody.textContent = message;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close btn-close-white me-2 m-auto';
        closeButton.setAttribute('data-bs-dismiss', 'toast');
        closeButton.setAttribute('aria-label', 'Close');
        
        toastFlex.appendChild(toastBody);
        toastFlex.appendChild(closeButton);
        toastElement.appendChild(toastFlex);
        toastContainer.appendChild(toastElement);
        
        document.body.appendChild(toastContainer);
        
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 3000
        });
        
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', function() {
            document.body.removeChild(toastContainer);
        });
    }
    
    // Function to update bot status in the UI
    function updateBotStatus(running) {
        if (statusIndicator && statusText) {
            if (running) {
                statusIndicator.className = 'status-indicator bg-success me-2';
                statusText.textContent = 'Running';
                if (startBotBtn) startBotBtn.disabled = true;
                if (stopBotBtn) stopBotBtn.disabled = false;
            } else {
                statusIndicator.className = 'status-indicator bg-danger me-2';
                statusText.textContent = 'Stopped';
                if (startBotBtn) startBotBtn.disabled = false;
                if (stopBotBtn) stopBotBtn.disabled = true;
            }
        }
    }
    
    // Function to update tweet display
    function updateTweetDisplay(tweet) {
        if (noTweetMessage && tweetContent && tweetText && tweetDate) {
            if (tweet) {
                noTweetMessage.classList.add('d-none');
                tweetContent.classList.remove('d-none');
                tweetText.textContent = tweet.text;
                tweetDate.textContent = tweet.date;
            } else {
                noTweetMessage.classList.remove('d-none');
                tweetContent.classList.add('d-none');
            }
        }
    }
    
    // Function to update active shorts list
    function updateActiveShorts(shorts) {
        if (shortsListContainer && shortsList && noShortsMessage) {
            if (shorts && shorts.length > 0) {
                noShortsMessage.classList.add('d-none');
                shortsListContainer.classList.remove('d-none');
                shortsList.innerHTML = '';
                
                shorts.forEach(short => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${short.id}</td>
                        <td>${short.symbol}</td>
                        <td>${short.quantity}</td>
                        <td>${short.entry_price}</td>
                        <td>${short.leverage}x</td>
                        <td>${short.timestamp}</td>
                        <td>
                            <button class="btn btn-sm btn-danger cancel-short" data-id="${short.id}">
                                <i class="bi bi-x-circle"></i> Cancel
                            </button>
                        </td>
                    `;
                    shortsList.appendChild(row);
                });
                
                // Add event listeners to cancel buttons
                document.querySelectorAll('.cancel-short').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const shortId = this.getAttribute('data-id');
                        cancelShort(shortId);
                    });
                });
            } else {
                noShortsMessage.classList.remove('d-none');
                shortsListContainer.classList.add('d-none');
            }
        }
    }
    
    // Function to get current status (updated regularly)
    function updateStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateBotStatus(data.running);
                    updateTweetDisplay(data.latest_tweet);
                    updateActiveShorts(data.active_shorts);
                }
            })
            .catch(error => {
                console.error('Error updating status:', error);
            });
    }
    
    // Function to cancel a short
    function cancelShort(shortId) {
        fetch('/api/cancel_short', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ short_id: shortId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Short cancelled successfully', 'success');
                updateStatus(); // Refresh status to update shorts list
            } else {
                showToast('Error cancelling short: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Server communication error', 'danger');
        });
    }
    
    // Start Bot Button
    if (startBotBtn) {
        startBotBtn.addEventListener('click', function() {
            fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateBotStatus(true);
                    showToast('Bot started successfully', 'success');
                } else {
                    showToast('Error starting the bot: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Server communication error', 'danger');
            });
        });
    }
    
    // Stop Bot Button
    if (stopBotBtn) {
        stopBotBtn.addEventListener('click', function() {
            fetch('/api/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateBotStatus(false);
                    showToast('Bot stopped successfully', 'success');
                } else {
                    showToast('Error stopping the bot: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Server communication error', 'danger');
            });
        });
    }
    
    // Test Binance API Button
    if (testBinanceBtn) {
        testBinanceBtn.addEventListener('click', function() {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
            
            fetch('/api/test_binance')
            .then(response => response.json())
            .then(data => {
                const binanceApiStatus = document.getElementById('binanceApiStatus');
                const binanceApiStatusText = document.getElementById('binanceApiStatusText');
                
                if (data.success) {
                    binanceApiStatus.className = 'status-indicator bg-success me-2';
                    binanceApiStatusText.textContent = 'Connected';
                    showToast('Binance API connection successful', 'success');
                } else {
                    binanceApiStatus.className = 'status-indicator bg-danger me-2';
                    binanceApiStatusText.textContent = 'Error';
                    showToast('Binance API connection error: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Server communication error', 'danger');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = 'Test Connection';
            });
        });
    }
    
    // Initial status update
    updateStatus();
    
    // Set up periodic updates every 5 seconds
    setInterval(updateStatus, 5000);
});
