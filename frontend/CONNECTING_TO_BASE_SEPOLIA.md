# 🔗 Connecting Frontend to Base Sepolia Contracts

This guide explains how to connect your React frontend to the contracts deployed on Base Sepolia.

## 📋 Prerequisites

1. ✅ Contracts deployed on Base Sepolia
2. ✅ MetaMask installed in your browser
3. ✅ Frontend dependencies installed (`npm install` in frontend directory)

## 🔧 Step 1: Add Base Sepolia Network to MetaMask

### Manual Network Addition

1. Open MetaMask extension
2. Click the network dropdown (top of MetaMask)
3. Click "Add Network" → "Add a network manually"
4. Enter the following details:

```
Network Name: Base Sepolia
RPC URL: https://sepolia.base.org
Chain ID: 84532
Currency Symbol: ETH
Block Explorer URL: https://sepolia-explorer.base.org
```

5. Click "Save"

### Quick Add (Alternative)

You can also use the Base network switcher:

- Visit: https://base.org/network-switcher
- Click "Add Base Sepolia to MetaMask"

## 💰 Step 2: Get Base Sepolia Test ETH

You'll need test ETH for gas fees. Get it from:

1. **Coinbase Faucet**: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
2. **QuickNode Faucet**: https://faucet.quicknode.com/base/sepolia

Send test ETH to your MetaMask wallet address.

## 🚀 Step 3: Start the Frontend

```bash
cd frontend
npm install  # If not already done
npm start
```

The app will open at http://localhost:3000

## 📝 Step 4: Configure Contract Addresses

### Method 1: Using the UI (Recommended)

1. **Connect Your Wallet**

   - Click "Connect Wallet" button in the top right
   - Approve the connection in MetaMask
   - Make sure you're on Base Sepolia network

2. **Enter Contract Addresses**
   - Go to the **"Contract Info"** tab
   - Enter your deployed contract addresses:
     - **NFT Factory Address**: `0x202bF02756feE008ddC081163A0a2a910e85c83F`
     - **NFT Collection Address**: (from your deployment output)
     - **Vault Address**: (from your deployment output)
   - Click **"Update Addresses"** button
   - Click **"Refresh Info"** to load contract data

### Method 2: Update Default Addresses (Optional)

You can also set default addresses in the code. Edit `frontend/src/App.js`:

```javascript
// Around line 29, update the default contract addresses:
const [contracts, setContracts] = useState({
  nftFactory: "0x202bF02756feE008ddC081163A0a2a910e85c83F", // Your factory address
  nftCollection: "YOUR_NFT_COLLECTION_ADDRESS",
  vault: "YOUR_VAULT_ADDRESS",
});
```

## 🎯 Step 5: Interact with Contracts

### Available Features

1. **Contract Info Tab**

   - View factory statistics
   - View NFT collection details
   - View vault information
   - Auto-discover vault address from NFT collection

2. **Mint NFT Tab**

   - Mint new NFTs
   - View your NFT balance
   - Set metadata URI

3. **Vault Management Tab**

   - Deposit ETH into vault
   - Withdraw ETH from vault
   - View vault shares balance
   - Redeem shares for ETH

4. **Other Tabs**
   - UMA Oracle: Interact with oracle contracts
   - Carbon Index: View carbon index data
   - Geo Index Token: View token information
   - Nature Index Tracker: Track nature unit values
   - Reward Token: View and claim rewards
   - SP1 Proof Status: Check zk-proof verification status

## 🔍 Verifying Your Setup

### Check Network Connection

1. Look at the top of the app - it should show:

   ```
   Connected to: baseSepolia (Chain ID: 84532)
   ```

2. In MetaMask, verify you're on "Base Sepolia" network

### Check Contract Connection

1. Go to **Contract Info** tab
2. Enter your NFT Factory address
3. Click **"Refresh Info"**
4. You should see:
   - Total Collections count
   - Deployed NFT addresses list
   - Contract information

## 🐛 Troubleshooting

### "Provider not initialized"

- Refresh the page
- Check MetaMask is installed and unlocked
- Try disconnecting and reconnecting wallet

### "Failed to connect wallet"

- Ensure MetaMask is unlocked
- Check you're on Base Sepolia network
- Try switching networks and switching back

### "Contract not found" or "Invalid address"

- Verify contract addresses are correct (copy from deployment output)
- Ensure contracts are deployed on Base Sepolia
- Check addresses on Base Sepolia explorer: https://sepolia-explorer.base.org

### "Insufficient funds"

- Get more test ETH from faucets
- Check your wallet balance in MetaMask
- Ensure you have enough for transaction + gas fees

### "Transaction failed"

- Check gas limit (should auto-estimate)
- Verify contract is active
- Check if you have enough ETH
- View transaction on explorer for error details

### Network Mismatch

- Frontend expects Base Sepolia (Chain ID: 84532)
- Switch MetaMask to Base Sepolia network
- Or update the frontend to support multiple networks

## 📊 Viewing Contracts on Explorer

After deployment, view your contracts on Base Sepolia Explorer:

- **NFT Factory**: https://sepolia-explorer.base.org/address/0x202bF02756feE008ddC081163A0a2a910e85c83F
- **NFT Collection**: https://sepolia-explorer.base.org/address/YOUR_NFT_ADDRESS
- **Vault**: https://sepolia-explorer.base.org/address/YOUR_VAULT_ADDRESS

## 🎉 Next Steps

Once connected:

1. **Test Minting**: Create your first NFT
2. **Test Vault**: Deposit and withdraw ETH
3. **Explore Features**: Try all the different tabs
4. **Monitor Transactions**: Watch transactions on the explorer

## 📚 Additional Resources

- Base Sepolia Explorer: https://sepolia-explorer.base.org
- Base Documentation: https://docs.base.org
- MetaMask Guide: https://metamask.io/faqs

---

**Happy Interacting! 🚀**
