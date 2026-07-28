# Crypto Wallet OSINT Reference

## Tools & Techniques

### 1. Ethereum Wallet
```bash
# Balance
curl "https://api.etherscan.io/api?module=account&action=balance&address={wallet}&tag=latest"

# Transactions
curl "https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&startblock=0&endblock=99999999"

# Token transfers
curl "https://api.etherscan.io/api?module=account&action=tokentx&address={wallet}"
```

### 2. Bitcoin Wallet
```bash
# Balance and transactions
curl "https://blockchain.info/rawaddr/{wallet}"

# Transaction details
curl "https://blockchain.info/rawtx/{txid}"
```

### 3. Multi-Chain Lookup
```bash
# DeBank
curl "https://api.debank.com/user/addr/{wallet}"

# Etherscan (supports multiple chains)
curl "https://api.etherscan.io/api?module=account&action=balance&address={wallet}&chainid=1"
```

### 4. Web Mentions
```bash
# Search for wallet address
"{wallet}" site:etherscan.io OR site:blockchain.info

# Check if linked to identity
"{wallet}" "email" OR "name" OR "profile"
```

### 5. Exchange Deposits
- Check if wallet sent to known exchange addresses
- Binance, Coinbase, Kraken deposit addresses are public

### 6. NFT Analysis
```bash
# OpenSea
curl "https://api.opensea.io/api/v2/chain/ethereum/account/{wallet}/nfts"

# Check NFT ownership history
```

## Red Flags
- Large movements to mixing services
- Connections to known scam addresses
- Multiple wallets controlled by same entity
- Rapid token swaps (MEV bot activity)
