import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('wallet.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            address TEXT PRIMARY KEY,
            private_key TEXT NOT NULL,
            balance REAL DEFAULT 5.0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_address TEXT NOT NULL,
            to_address TEXT NOT NULL,
            amount REAL NOT NULL,
            signature TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_address) REFERENCES wallets(address),
            FOREIGN KEY (to_address) REFERENCES wallets(address)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('wallet.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_wallet(address, private_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO wallets (address, private_key, balance) VALUES (?, ?, 5.0)',
        (address, private_key)
    )
    conn.commit()
    conn.close()

def get_wallet(address):
    conn = get_db_connection()
    wallet = conn.execute('SELECT * FROM wallets WHERE address = ?', (address,)).fetchone()
    conn.close()
    return wallet

def update_balance(address, new_balance):
    conn = get_db_connection()
    conn.execute('UPDATE wallets SET balance = ? WHERE address = ?', (new_balance, address))
    conn.commit()
    conn.close()

def add_transaction(from_address, to_address, amount, signature):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO transactions (from_address, to_address, amount, signature) VALUES (?, ?, ?, ?)',
        (from_address, to_address, amount, signature)
    )
    conn.commit()
    conn.close()

def get_transactions(address):
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT * FROM transactions WHERE from_address = ? OR to_address = ? ORDER BY timestamp DESC',
        (address, address)
    ).fetchall()
    conn.close()
    return transactions
