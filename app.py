from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import requests
import database
import os

app = Flask(__name__, static_folder='static')
CORS(app)

database.init_db()

w3 = Web3()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    account = Account.create()
    address = account.address
    private_key = account.key.hex()
    
    database.create_wallet(address, private_key)
    
    return jsonify({
        'address': address,
        'private_key': private_key,
        'balance': 5.0
    })

@app.route('/api/wallet/<address>/balance', methods=['GET'])
def get_balance(address):
    wallet = database.get_wallet(address)
    
    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404
    
    return jsonify({
        'address': address,
        'balance': wallet['balance']
    })

@app.route('/api/transfer/prepare', methods=['POST'])
def prepare_transfer():
    data = request.json
    from_address = data.get('from_address')
    to_address = data.get('to_address')
    amount_usd = data.get('amount_usd')
    
    if not all([from_address, to_address, amount_usd]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    from_wallet = database.get_wallet(from_address)
    to_wallet = database.get_wallet(to_address)
    
    if not from_wallet:
        return jsonify({'error': 'Sender wallet not found'}), 404
    
    if not to_wallet:
        return jsonify({'error': 'Recipient wallet not found'}), 404
    
    amount_eth = float(amount_usd)
    
    try:
        response = requests.post(
            'https://api.cypherd.io/v2/quote/',
            json={
                "source_asset_denom": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "source_asset_chain_id": "1",
                "dest_asset_denom": "ethereum-native",
                "dest_asset_chain_id": "1",
                "amount_in": str(int(float(amount_usd) * 1000000)),
                "chain_ids_to_addresses": {
                    "1": from_address
                },
                "slippage_tolerance_percent": "1",
                "smart_swap_options": {
                    "evm_swaps": True
                },
                "allow_unsafe": False
            },
            timeout=10
        )
        
        if response.status_code == 200:
            quote_data = response.json()
            if 'amount_out' in quote_data:
                amount_eth = float(quote_data['amount_out']) / 1e18
    except Exception as e:
        print(f"CypherD API error: {e}")
        amount_eth = float(amount_usd) / 2000
    
    if from_wallet['balance'] < amount_eth:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    message = f"Transfer {amount_eth:.6f} ETH (${amount_usd} USD) to {to_address} from {from_address}"
    
    return jsonify({
        'message': message,
        'amount_eth': amount_eth,
        'amount_usd': amount_usd
    })

@app.route('/api/transfer/sign', methods=['POST'])
def sign_message():
    data = request.json
    address = data.get('address')
    private_key = data.get('private_key')
    message = data.get('message')
    
    if not all([address, private_key, message]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        account = Account.from_key(private_key)
        
        if account.address.lower() != address.lower():
            return jsonify({'error': 'Invalid private key for this address'}), 400
        
        message_hash = encode_defunct(text=message)
        signed_message = account.sign_message(message_hash)
        
        return jsonify({
            'signature': signed_message.signature.hex()
        })
    except Exception as e:
        return jsonify({'error': f'Signing failed: {str(e)}'}), 500

@app.route('/api/transfer/execute', methods=['POST'])
def execute_transfer():
    data = request.json
    from_address = data.get('from_address')
    to_address = data.get('to_address')
    amount_eth = data.get('amount_eth')
    message = data.get('message')
    signature = data.get('signature')
    
    if not all([from_address, to_address, amount_eth, message, signature]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    from_wallet = database.get_wallet(from_address)
    to_wallet = database.get_wallet(to_address)
    
    if not from_wallet or not to_wallet:
        return jsonify({'error': 'Wallet not found'}), 404
    
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        if recovered_address.lower() != from_address.lower():
            return jsonify({'error': 'Invalid signature'}), 400
        
        import re
        match = re.search(r'Transfer ([\d.]+) ETH .* to (0x[a-fA-F0-9]{40}) from (0x[a-fA-F0-9]{40})', message)
        
        if not match:
            return jsonify({'error': 'Invalid message format'}), 400
        
        signed_amount = float(match.group(1))
        signed_to_address = match.group(2)
        signed_from_address = match.group(3)
        
        if abs(signed_amount - amount_eth) > 0.000001:
            return jsonify({'error': 'Amount does not match signed message'}), 400
        
        if signed_to_address.lower() != to_address.lower():
            return jsonify({'error': 'Recipient address does not match signed message'}), 400
        
        if signed_from_address.lower() != from_address.lower():
            return jsonify({'error': 'Sender address does not match signed message'}), 400
        
        if from_wallet['balance'] < amount_eth:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        new_from_balance = from_wallet['balance'] - amount_eth
        new_to_balance = to_wallet['balance'] + amount_eth
        
        database.update_balance(from_address, new_from_balance)
        database.update_balance(to_address, new_to_balance)
        database.add_transaction(from_address, to_address, amount_eth, signature)
        
        print(f"✅ TRANSFER SUCCESSFUL: {amount_eth:.6f} ETH from {from_address} to {to_address}")
        print(f"   Sender new balance: {new_from_balance:.6f} ETH")
        print(f"   Recipient new balance: {new_to_balance:.6f} ETH")
        
        return jsonify({
            'success': True,
            'message': 'Transfer successful',
            'new_balance': new_from_balance
        })
    except Exception as e:
        return jsonify({'error': f'Transfer failed: {str(e)}'}), 500

@app.route('/api/wallet/<address>/transactions', methods=['GET'])
def get_wallet_transactions(address):
    wallet = database.get_wallet(address)
    
    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404
    
    transactions = database.get_transactions(address)
    
    return jsonify({
        'transactions': [dict(tx) for tx in transactions]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
