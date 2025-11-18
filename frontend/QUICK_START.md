# ⚡ Quick Start Guide - Frontend to Base Sepolia

## 🎯 Quick Setup (5 Minutes)

### 1. Install & Start Frontend
```bash
cd frontend
npm install
npm start
```

### 2. Add Base Sepolia to MetaMask
- Network Name: `Base Sepolia`
- RPC URL: `https://sepolia.base.org`
- Chain ID: `84532`
- Currency: `ETH`
- Explorer: `https://sepolia-explorer.base.org`

### 3. Get Test ETH
Visit: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet

### 4. Connect & Configure
1. Open http://localhost:3000
2. Click "Connect Wallet"
3. Go to "Contract Info" tab
4. Enter addresses:
   - **NFT Factory**: `0x202bF02756feE008ddC081163A0a2a910e85c83F`
   - **NFT Collection**: (from deployment)
   - **Vault**: (from deployment)
5. Click "Update Addresses" → "Refresh Info"

## 📋 Your Deployed Contract Addresses

**NFT Factory (Deployed)**: `0x202bF02756feE008ddC081163A0a2a910e85c83F`

**NFT Collection & Vault**: 
- Complete your deployment to get these addresses
- Run: `npm run deploy:base-sepolia` (after getting more test ETH)

## 🔗 View on Explorer

- Factory: https://sepolia-explorer.base.org/address/0x202bF02756feE008ddC081163A0a2a910e85c83F

## ✅ Checklist

- [ ] Frontend running on localhost:3000
- [ ] MetaMask installed and unlocked
- [ ] Base Sepolia network added to MetaMask
- [ ] Connected to Base Sepolia in MetaMask
- [ ] Have test ETH in wallet
- [ ] Contract addresses entered in frontend
- [ ] Can see contract info after refresh

## 🎮 What You Can Do

1. **View Contracts** - See factory, NFT, and vault details
2. **Mint NFTs** - Create new NFTs with metadata
3. **Manage Vault** - Deposit/withdraw ETH
4. **Track Indexes** - View carbon and nature indexes
5. **Check Rewards** - See reward token balances

## 🆘 Need Help?

See [CONNECTING_TO_BASE_SEPOLIA.md](./CONNECTING_TO_BASE_SEPOLIA.md) for detailed instructions.
