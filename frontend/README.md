# 🎨 NFT Factory & Vault Frontend

A React-based frontend for interacting with NFT Factory and Vault smart contracts.

## 🚀 Features

- **Wallet Connection** - MetaMask integration
- **Contract Information** - View factory, NFT, and vault details
- **NFT Minting** - Mint new NFTs with metadata
- **Vault Management** - Deposit, withdraw, and redeem ETH
- **Real-time Updates** - Live contract data and transaction status

## 📋 Prerequisites

- Node.js (version 16 or higher)
- MetaMask browser extension
- Deployed smart contracts (NFT Factory, NFT Collection, Vault)

## 🛠️ Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## 🔧 Configuration

### Contract Addresses

After deploying your contracts, update the contract addresses in the **Contract Info** tab:

1. **NFT Factory Address** - Your deployed factory contract
2. **NFT Collection Address** - The NFT collection you want to interact with
3. **Vault Address** - The vault associated with the NFT collection

### Network Configuration

Make sure your MetaMask is connected to the same network where your contracts are deployed:

- **Localhost** - For local testing
- **Sepolia** - Ethereum testnet
- **Base Sepolia** - Base testnet (Chain ID: 84532) - **Currently Deployed**
- **Mumbai** - Polygon testnet

#### Adding Base Sepolia to MetaMask

1. Open MetaMask → Network dropdown → "Add Network" → "Add a network manually"
2. Enter:
   - Network Name: `Base Sepolia`
   - RPC URL: `https://sepolia.base.org`
   - Chain ID: `84532`
   - Currency Symbol: `ETH`
   - Block Explorer: `https://sepolia-explorer.base.org`
3. Click "Save"

**See [CONNECTING_TO_BASE_SEPOLIA.md](./CONNECTING_TO_BASE_SEPOLIA.md) for detailed instructions.**

## 📱 Usage

### 1. Connect Wallet

- Click "Connect MetaMask" button
- Approve the connection in MetaMask
- Ensure you have some ETH for gas fees

### 2. View Contract Information

- Go to the **Contract Info** tab
- Enter your contract addresses
- View factory, NFT, and vault details

### 3. Mint NFTs

- Go to the **Mint NFT** tab
- Enter metadata URI (JSON file URL)
- Choose minting method:
  - **Public Mint** - Pay mint price
  - **Owner Mint** - Free (contract owner only)

### 4. Manage Vault

- Go to the **Vault Management** tab
- **Deposit ETH** - Get vault shares
- **Withdraw ETH** - Burn shares for ETH
- **Redeem Shares** - Convert shares to ETH

## 🎯 Contract Interaction Flow

```
1. Deploy Contracts (using Hardhat scripts)
   ↓
2. Get Contract Addresses
   ↓
3. Update Frontend Addresses
   ↓
4. Connect Wallet
   ↓
5. Interact with Contracts
```

## 🧪 Testing

### Local Development

1. Start local Hardhat node: `npx hardhat node`
2. Deploy contracts: `npx hardhat run scripts/deploy.js --network localhost`
3. Copy contract addresses to frontend
4. Connect MetaMask to localhost:8545
5. Import test accounts with private keys

### Testnet Testing

1. Deploy to testnet: `npx hardhat run scripts/deploy.js --network sepolia`
2. Get test ETH from faucets
3. Update frontend with deployed addresses
4. Test all functionality

## 🚨 Important Notes

- **Gas Fees** - All transactions require ETH for gas
- **Network Matching** - Frontend and wallet must be on same network
- **Contract Verification** - Verify contracts on block explorers for transparency
- **Security** - Never share private keys or seed phrases

## 🆘 Troubleshooting

### Common Issues

#### "Provider not initialized"

- Refresh the page
- Check if MetaMask is installed and unlocked

#### "Failed to connect wallet"

- Check MetaMask connection
- Ensure MetaMask is unlocked
- Try switching networks

#### "Contract not found"

- Verify contract addresses are correct
- Ensure contracts are deployed to the current network
- Check if contracts are verified on block explorer

#### "Insufficient funds"

- Get test ETH from faucets
- Check your wallet balance
- Ensure you have enough for mint price + gas

#### "Transaction failed"

- Check gas limit settings
- Ensure sufficient ETH balance
- Verify contract state (active/inactive)

## 🔮 Future Enhancements

- **Batch Operations** - Mint multiple NFTs at once
- **Metadata Management** - IPFS integration for metadata storage
- **Advanced Vault Features** - Yield farming, staking rewards
- **Mobile Optimization** - Responsive design improvements
- **Transaction History** - Track all user interactions
- **Social Features** - Share collections, follow creators

## 📄 License

This project is licensed under the MIT License.

---

**Happy Building! 🚀**
