# Web3 Wallet Application

## Overview

This is a Web3 wallet demo application (CypherD Hackathon). It provides a simple local environment to create Ethereum wallets, view balances, prepare transfers (USD → ETH quoting), sign transfer messages and execute transfers in a mock ledger backed by SQLite.

The project is intentionally simplified for demonstration and learning purposes: private keys are stored plaintext in the local database and balances are mocked. Do not use this code as-is in production.

---

## Quickstart — run locally

1. Create and activate a virtual environment (Windows PowerShell):

    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

2. Install dependencies:

    ```powershell
    # If you have a requirements.txt
    pip install -r requirements.txt

    # Or install the minimal runtime deps quickly
    pip install flask flask-cors requests web3 eth-account
    ```

3. Start the server:

    ```powershell
    python app.py
    ```

The API will be available at http://localhost:5000

---

## How the project works (high level)

- Backend: a Flask app in `app.py` exposing REST endpoints for wallet creation, balance lookup, preparing transfers, signing messages, executing transfers and viewing transactions.
- Wallets are generated using `eth_account.Account.create()`; the private key and address are stored in a local SQLite database for demo use.
- Each new wallet starts with a default mock balance (5.0 ETH) and transfers update balances inside the SQLite database.
- Transfer preparation attempts to obtain USD→ETH quotes from `https://api.cypherd.io/v2/quote/`. If the quote call fails, the app falls back to a simple fixed conversion.
- Transfers are authorized by signing a human-readable message with the sender's private key. The server verifies the signature (using `Account.recover_message`) before applying balance updates.

---

## API Reference (short)

Base URL: http://localhost:5000

1) POST /api/wallet/create
- Creates a new wallet.
- Response JSON: `{ "address": "0x..", "private_key": "0x..", "balance": 5.0 }`

2) GET /api/wallet/<address>/balance
- Returns wallet balance.
- Response JSON: `{ "address": "0x..", "balance": <number> }`

3) POST /api/transfer/prepare
- Request body: `{ "from_address": "0x..", "to_address": "0x..", "amount_usd": 10 }`
- Response JSON: `{ "message": "Transfer X.XXXX ETH ($10 USD) to 0x.. from 0x..", "amount_eth": <number>, "amount_usd": 10 }`
- `message` is the text you should sign with the `from_address` private key.

4) POST /api/transfer/sign
- Request body: `{ "address": "0x..", "private_key": "0x..", "message": "..." }`
- Response JSON: `{ "signature": "0x..." }`
- This endpoint uses `eth-account` to produce an ECDSA signature for the message (demo helper; in production sign client-side).

5) POST /api/transfer/execute
- Request body: `{ "from_address":"0x..", "to_address":"0x..", "amount_eth": <number>, "message": "...", "signature": "0x..." }`
- Server verifies that the signature recovers to the `from_address`, that the message contents match the payload, then updates balances and records the transaction.
- On success: `{ "success": true, "message": "Transfer successful", "new_balance": <number> }`

6) GET /api/wallet/<address>/transactions
- Returns a JSON list of transactions where the address participated.
- Response JSON: `{ "transactions": [ { .. }, ... ] }`

---

## Testing with Postman (local)

Notes:
- If you use Postman in a browser, you must install and run the Postman Desktop Agent so Postman can send requests to `localhost`.
- Prefer the Postman Desktop app (or Desktop Agent) to avoid localhost/networking restrictions.

Suggested environment variables for Postman:
- base_url = http://localhost:5000
- walletA_address, walletA_private_key
- walletB_address, walletB_private_key
- amount_eth, signed_message, signature

Recommended test flow (happy path):
1. POST {{base_url}}/api/wallet/create — create wallet A. Save `address` and `private_key`.
2. POST {{base_url}}/api/wallet/create — create wallet B.
3. POST {{base_url}}/api/transfer/prepare with `{ from_address: walletA, to_address: walletB, amount_usd: 10 }` — save `message` and `amount_eth`.
4. POST {{base_url}}/api/transfer/sign with `{ address: walletA, private_key: walletA_private_key, message: message }` — save `signature`.
5. POST {{base_url}}/api/transfer/execute with `{ from_address: walletA, to_address: walletB, amount_eth: amount_eth, message: message, signature: signature }` — expect success and updated balance.
6. GET {{base_url}}/api/wallet/{{walletA_address}}/transactions — verify recorded transaction.

Negative tests:
- Missing fields → endpoints should return 400 with `{"error":"Missing required fields"}`.
- Insufficient balance → prepare or execute should return 400 `{"error":"Insufficient balance"}`.
- Invalid signature → execute should return 400 `{"error":"Invalid signature"}`.

---

## Security & Production notes

- Private keys are stored in cleartext in the SQLite database for demo/hackathon purposes. This is insecure. In production we do NOT store private keys on the server.
- For production, perform signing client-side or use secure key management (HSMs, KMS). Use encrypted secrets storage and strict access controls.
- Validate and sanitize all external API responses (the project currently calls a remote quote API).
