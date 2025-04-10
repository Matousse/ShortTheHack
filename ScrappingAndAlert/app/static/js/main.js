/**
 * GentleMate - Script principal
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const startBotBtn = document.getElementById('startBot');
    const stopBotBtn = document.getElementById('stopBot');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const settingsForm = document.getElementById('settingsForm');
    const leverageInput = document.getElementById('leverageInput');
    const leverageValue = document.getElementById('leverageValue');
    const testBinanceBtn = document.getElementById('testBinanceBtn');
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('main > section');
    const noTweetMessage = document.getElementById('noTweetMessage');
    const tweetContent = document.getElementById('tweetContent');
    const tweetText = document.getElementById('tweetText');
    const tweetDate = document.getElementById('tweetDate');

    // Initialisation
    updateStatus();
    setInterval(updateStatus, 5000); // Mettre à jour le statut toutes les 5 secondes

    // Navigation
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Mettre à jour les classes actives
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Afficher la section correspondante
            const targetId = this.getAttribute('href').substring(1);
            sections.forEach(section => {
                if (section.id === targetId) {
                    section.classList.remove('d-none');
                } else {
                    section.classList.add('d-none');
                }
            });
        });
    });

    // Mise à jour du levier
    leverageInput.addEventListener('input', function() {
        leverageValue.textContent = this.value + 'x';
    });

    // Démarrer le bot
    startBotBtn.addEventListener('click', function() {
        fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateBotStatus(true);
                showToast('Bot démarré avec succès', 'success');
            } else {
                showToast('Erreur lors du démarrage du bot', 'danger');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showToast('Erreur de communication avec le serveur', 'danger');
        });
    });

    // Arrêter le bot
    stopBotBtn.addEventListener('click', function() {
        fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateBotStatus(false);
                showToast('Bot arrêté avec succès', 'success');
            } else {
                showToast('Erreur lors de l\'arrêt du bot', 'danger');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showToast('Erreur de communication avec le serveur', 'danger');
        });
    });

    // Enregistrer les paramètres
    settingsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const newSettings = {
            trading_enabled: document.getElementById('tradingEnabledSwitch').checked,
            target_account: document.getElementById('targetAccountInput').value,
            target_coin: document.getElementById('targetCoinInput').value,
            leverage: parseInt(document.getElementById('leverageInput').value),
            check_interval: parseInt(document.getElementById('checkIntervalInput').value)
        };
        
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newSettings)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Paramètres enregistrés avec succès', 'success');
                updateUIWithSettings(data.settings);
            } else {
                showToast('Erreur lors de l\'enregistrement des paramètres', 'danger');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showToast('Erreur de communication avec le serveur', 'danger');
        });
    });

    // Tester la connexion Binance
    testBinanceBtn.addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Test en cours...';
        
        fetch('/api/test_binance')
        .then(response => response.json())
        .then(data => {
            const binanceApiStatus = document.getElementById('binanceApiStatus');
            const binanceApiStatusText = document.getElementById('binanceApiStatusText');
            
            if (data.success) {
                binanceApiStatus.className = 'status-indicator bg-success me-2';
                binanceApiStatusText.textContent = 'Connecté';
                showToast('Connexion à Binance réussie', 'success');
            } else {
                binanceApiStatus.className = 'status-indicator bg-danger me-2';
                binanceApiStatusText.textContent = 'Erreur';
                showToast('Erreur de connexion à Binance: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showToast('Erreur de communication avec le serveur', 'danger');
        })
        .finally(() => {
            this.disabled = false;
            this.innerHTML = 'Tester la connexion';
        });
    });

    // Fonction pour mettre à jour l'état du bot dans l'UI
    function updateBotStatus(running) {
        if (running) {
            startBotBtn.disabled = true;
            stopBotBtn.disabled = false;
            statusIndicator.className = 'status-indicator bg-success me-2';
            statusText.textContent = 'En cours d\'exécution';
        } else {
            startBotBtn.disabled = false;
            stopBotBtn.disabled = true;
            statusIndicator.className = 'status-indicator bg-danger me-2';
            statusText.textContent = 'Arrêté';
        }
    }

    // Fonction pour mettre à jour l'UI avec les paramètres
    function updateUIWithSettings(settings) {
        document.getElementById('targetAccount').textContent = '@' + settings.target_account;
        document.getElementById('targetCoin').textContent = settings.target_coin;
        document.getElementById('leverage').textContent = settings.leverage + 'x';
        document.getElementById('tradingEnabled').textContent = settings.trading_enabled ? 'Oui' : 'Non';
    }

    // Fonction pour mettre à jour l'UI avec le dernier tweet
    function updateLastTweet(tweet) {
        if (tweet) {
            noTweetMessage.classList.add('d-none');
            tweetContent.classList.remove('d-none');
            tweetText.textContent = tweet.text;
            
            // Formater la date
            const tweetDate = new Date(tweet.created_at);
            const formattedDate = tweetDate.toLocaleString();
            document.getElementById('tweetDate').textContent = formattedDate;
        } else {
            noTweetMessage.classList.remove('d-none');
            tweetContent.classList.add('d-none');
        }
    }

    // Fonction pour mettre à jour le statut du bot
    function updateStatus() {
        fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateBotStatus(data.running);
            updateUIWithSettings(data.settings);
            
            if (data.last_tweet) {
                updateLastTweet(data.last_tweet);
            }
        })
        .catch(error => {
            console.error('Erreur lors de la mise à jour du statut:', error);
        });
    }

    // Fonction pour afficher un toast
    function showToast(message, type = 'info') {
        // Créer un élément toast
        const toastContainer = document.createElement('div');
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '5';
        
        const toastElement = document.createElement('div');
        toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
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
        
        // Initialiser le toast avec Bootstrap
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 3000
        });
        
        toast.show();
        
        // Supprimer le toast du DOM après qu'il soit caché
        toastElement.addEventListener('hidden.bs.toast', function() {
            document.body.removeChild(toastContainer);
        });
    }

    // Fonction pour charger les logs
    function loadLogs() {
        const logsContent = document.getElementById('logsContent');
        
        // Cette fonction serait implémentée côté serveur pour récupérer les logs
        // Pour l'instant, on affiche un message d'exemple
        logsContent.textContent = '[2025-04-10 11:08:10] | INFO | Bot initialisé\n[2025-04-10 11:08:12] | INFO | En attente de nouveaux tweets...';
    }

    // Charger les logs lors du clic sur l'onglet Logs
    document.querySelector('a[href="#logs"]').addEventListener('click', loadLogs);
});
