let currentWallet = null;
let transferData = null;

const API_BASE = '';

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showWalletSection() {
    document.getElementById('create-wallet-section').classList.add('hidden');
    document.getElementById('wallet-section').classList.remove('hidden');
}

function showCreateSection() {
    document.getElementById('wallet-section').classList.add('hidden');
    document.getElementById('create-wallet-section').classList.remove('hidden');
}

async function createWallet() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/api/wallet/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        currentWallet = data;
        
        displayWallet(data);
        loadTransactions();
        showWalletSection();
    } catch (error) {
        alert('Error creating wallet: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function accessWallet(address) {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/api/wallet/${address}/balance`);
        
        if (!response.ok) {
            throw new Error('Wallet not found');
        }
        
        const data = await response.json();
        currentWallet = {
            address: data.address,
            balance: data.balance,
            private_key: prompt('Enter your private key to access this wallet:')
        };
        
        displayWallet(currentWallet);
        loadTransactions();
        showWalletSection();
    } catch (error) {
        alert('Error accessing wallet: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayWallet(wallet) {
    document.getElementById('wallet-address').textContent = wallet.address;
    document.getElementById('wallet-balance').textContent = `${wallet.balance.toFixed(4)} ETH`;
    document.getElementById('wallet-private-key').textContent = wallet.private_key || '••••••••';
}

async function loadTransactions() {
    if (!currentWallet) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/wallet/${currentWallet.address}/transactions`);
        const data = await response.json();
        
        const transactionsList = document.getElementById('transactions-list');
        
        if (data.transactions.length === 0) {
            transactionsList.innerHTML = '<p style="color: #999;">No transactions yet</p>';
            return;
        }
        
        transactionsList.innerHTML = data.transactions.map(tx => {
            const isSent = tx.from_address.toLowerCase() === currentWallet.address.toLowerCase();
            const type = isSent ? 'sent' : 'received';
            const otherAddress = isSent ? tx.to_address : tx.from_address;
            
            return `
                <div class="transaction-item ${type}">
                    <div class="tx-type">${isSent ? '📤 Sent' : '📥 Received'}</div>
                    <div class="tx-amount">${tx.amount.toFixed(6)} ETH</div>
                    <div class="tx-address">${isSent ? 'To' : 'From'}: ${otherAddress}</div>
                    <div class="tx-time">${new Date(tx.timestamp).toLocaleString()}</div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

async function prepareTransfer(event) {
    event.preventDefault();
    
    const toAddress = document.getElementById('recipient-address').value;
    const amountUsd = document.getElementById('amount-usd').value;
    
    if (!currentWallet || !currentWallet.private_key) {
        alert('Please enter your private key to make transfers');
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/api/transfer/prepare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_address: currentWallet.address,
                to_address: toAddress,
                amount_usd: amountUsd
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error);
        }
        
        const data = await response.json();
        transferData = {
            ...data,
            to_address: toAddress
        };
        
        showApprovalModal(data.message);
    } catch (error) {
        alert('Error preparing transfer: ' + error.message);
    } finally {
        hideLoading();
    }
}

function showApprovalModal(message) {
    document.getElementById('approval-message').textContent = message;
    document.getElementById('approval-modal').classList.remove('hidden');
}

function hideApprovalModal() {
    document.getElementById('approval-modal').classList.add('hidden');
}

async function confirmTransfer() {
    hideApprovalModal();
    showLoading();
    
    try {
        const signResponse = await fetch(`${API_BASE}/api/transfer/sign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                address: currentWallet.address,
                private_key: currentWallet.private_key,
                message: transferData.message
            })
        });
        
        if (!signResponse.ok) {
            const error = await signResponse.json();
            throw new Error(error.error);
        }
        
        const signData = await signResponse.json();
        
        const executeResponse = await fetch(`${API_BASE}/api/transfer/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_address: currentWallet.address,
                to_address: transferData.to_address,
                amount_eth: transferData.amount_eth,
                message: transferData.message,
                signature: signData.signature
            })
        });
        
        if (!executeResponse.ok) {
            const error = await executeResponse.json();
            throw new Error(error.error);
        }
        
        const executeData = await executeResponse.json();
        
        currentWallet.balance = executeData.new_balance;
        displayWallet(currentWallet);
        loadTransactions();
        
        document.getElementById('transfer-form').reset();
        
        alert('Transfer successful! ✅');
    } catch (error) {
        alert('Transfer failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

document.getElementById('create-wallet-btn').addEventListener('click', createWallet);
document.getElementById('access-wallet-btn').addEventListener('click', () => {
    const address = document.getElementById('existing-address').value;
    if (address) {
        accessWallet(address);
    } else {
        alert('Please enter a wallet address');
    }
});
document.getElementById('transfer-form').addEventListener('submit', prepareTransfer);
document.getElementById('confirm-btn').addEventListener('click', confirmTransfer);
document.getElementById('cancel-btn').addEventListener('click', hideApprovalModal);
