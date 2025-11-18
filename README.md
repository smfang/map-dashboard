# 🎨 NFT Factory & NFT Contract Deployment

A complete setup for deploying NFT contracts, an NFT factory, and associated vaults on Ethereum and Polygon networks.

## 🚀 What This Project Does

- **NFT Contract**: ERC-721 standard NFT with minting functionality
- **NFT Factory**: Creates new NFT collections with customizable parameters
- **NFT Vaults**: ERC4626 vaults linked to each NFT collection for deposits and withdrawals
- **Easy Deployment**: Simple scripts for local and testnet deployment

## 📋 Prerequisites

Before you start, you need:

1. **Node.js** (version 16 or higher)
2. **MetaMask** wallet with some test ETH
3. **Infura account** (free) for blockchain access
4. **Basic understanding** of Ethereum and smart contracts

## 🛠️ Installation

### Step 1: Install Dependencies
```bash
npm install
```

### Step 2: Set Up Environment Variables
Create a `.env` file in the root directory:

```bash
# Network URLs (get from Infura)
SEPOLIA_URL=https://sepolia.infura.io/v3/YOUR-PROJECT-ID
MUMBAI_URL=https://polygon-mumbai.infura.io/v3/YOUR-PROJECT-ID

# Your private key (from MetaMask)
PRIVATE_KEY=your_private_key_here_without_0x_prefix

# API Keys for verification
ETHERSCAN_API_KEY=your_etherscan_api_key_here
POLYGONSCAN_API_KEY=your_polygonscan_api_key_here
```

### Step 3: Get Required Keys

#### A. Infura Project ID
1. Go to [Infura.io](https://infura.io)
2. Create a free account
3. Create a new project
4. Copy the project ID from the project settings

#### B. MetaMask Private Key
1. Open MetaMask
2. Click the three dots → Account Details
3. Click "Export Private Key"
4. Enter your password
5. Copy the private key (remove the "0x" prefix)

#### C. Etherscan API Key
1. Go to [Etherscan.io](https://etherscan.io)
2. Create a free account
3. Go to API Keys section
4. Create a new API key

## 🚀 Deployment

### Local Development (Recommended for Beginners)
```bash
# Start local blockchain
npx hardhat node

# In a new terminal, deploy contracts
npm run deploy:local
```

### Testnet Deployment (Sepolia - Ethereum)
```bash
npm run deploy:testnet
```

### Testnet Deployment (Mumbai - Polygon)
```bash
npx hardhat run scripts/deploy.js --network mumbai
```

## 📚 Understanding the Contracts

### MyNFT.sol
- **ERC-721 Standard**: Follows Ethereum's NFT standard
- **Minting**: Anyone can mint by paying the mint price
- **Owner Functions**: Owner can mint for free and withdraw funds
- **Metadata**: Supports custom token URIs for images/attributes

### NFTFactory.sol
- **Collection Creation**: Deploys new NFT contracts
- **Vault Creation**: Automatically creates associated vaults for each NFT collection
- **Fee System**: Charges a fee for creating collections
- **Management**: Tracks all deployed collections and vaults
- **Ownership**: Transfers ownership to collection creators

### NFTVault.sol
- **ERC4626 Standard**: Compliant vault for deposits and withdrawals
- **ETH Deposits**: Users can deposit ETH and receive vault shares
- **Share Redemption**: Users can redeem shares for ETH
- **Linked to NFT**: Each vault is specifically linked to an NFT collection
- **Owner Controls**: Vault owners can manage deposit limits and vault status

## 🔧 Contract Functions

### NFT Contract Functions
```solidity
// Mint an NFT (pay the mint price)
mint(string memory tokenURI) public payable

// Owner can mint for free
ownerMint(address to, string memory tokenURI) public onlyOwner

// Withdraw collected funds
withdraw() public onlyOwner

// Update mint price
setMintPrice(uint256 _mintPrice) public onlyOwner
```

### Factory Functions
```solidity
// Create new NFT collection with associated vault
createNFTCollection(
    string memory name,
    string memory symbol,
    uint256 maxSupply,
    uint256 mintPrice,
    string memory baseURI
) public payable returns (address, address)

// Get all deployed collections
getDeployedNFTs() public view returns (address[] memory)

// Get vault associated with NFT
getNFTVault(address nftAddress) public view returns (address)
```

### Vault Functions
```solidity
// Deposit ETH and receive vault shares
deposit(uint256 assets, address receiver) public payable

// Withdraw ETH by burning shares
withdraw(uint256 assets, address receiver, address owner) public

// Redeem shares for ETH
redeem(uint256 shares, address receiver, address owner) public

// Preview functions for calculations
previewDeposit(uint256 assets) public view returns (uint256)
previewWithdraw(uint256 assets) public view returns (uint256)
```

## 💰 Costs

### Factory Deployment
- **Gas Fee**: ~0.001-0.005 ETH (varies by network)
- **Factory Fee**: 0.01 ETH (configurable)

### Collection Creation
- **Factory Fee**: 0.01 ETH (paid to factory owner)
- **Gas Fee**: ~0.001-0.003 ETH (varies by network)
- **Vault Creation**: Included in collection creation gas

### NFT Minting
- **Mint Price**: 0.001 ETH (configurable per collection)
- **Gas Fee**: ~0.0005-0.002 ETH (varies by network)

### Vault Operations
- **Deposit**: Gas fee only (~0.0003-0.001 ETH)
- **Withdrawal**: Gas fee only (~0.0003-0.001 ETH)
- **No additional fees** for vault operations

## 🧪 Testing

### Compile Contracts
```bash
npm run compile
```

### Run Tests
```bash
npm test
```

### Test Vault Interactions
```bash
# Update addresses in scripts/vault-interactions.js first
npx hardhat run scripts/vault-interactions.js --network localhost
```

## 🌐 Network Information

### Sepolia (Ethereum Testnet)
- **Chain ID**: 11155111
- **RPC URL**: https://sepolia.infura.io/v3/YOUR-PROJECT-ID
- **Block Explorer**: https://sepolia.etherscan.io
- **Faucet**: https://sepoliafaucet.com

### Mumbai (Polygon Testnet)
- **Chain ID**: 80001
- **RPC URL**: https://polygon-mumbai.infura.io/v3/YOUR-PROJECT-ID
- **Block Explorer**: https://mumbai.polygonscan.com
- **Faucet**: https://faucet.polygon.technology

## 🔍 Verifying Contracts

After deployment, verify your contracts on block explorers:

### Sepolia
```bash
npx hardhat verify --network sepolia DEPLOYED_CONTRACT_ADDRESS
```

### Mumbai
```bash
npx hardhat verify --network mumbai DEPLOYED_CONTRACT_ADDRESS
```

## 📱 Interacting with Contracts

### Using Hardhat Console
```bash
npx hardhat console --network sepolia

# Get contract instances
const factory = await ethers.getContractAt("NFTFactory", "FACTORY_ADDRESS")
const vault = await ethers.getContractAt("NFTVault", "VAULT_ADDRESS")

# Create new collection with vault
const tx = await factory.createNFTCollection(
    "My Collection",
    "MC",
    1000,
    ethers.utils.parseEther("0.001"),
    "https://api.example.com/metadata/",
    { value: ethers.utils.parseEther("0.01") }
)

# Deposit ETH into vault
const depositTx = await vault.deposit(
    ethers.utils.parseEther("0.1"), 
    "YOUR_ADDRESS", 
    { value: ethers.utils.parseEther("0.1") }
)
```

### Using Remix
1. Go to [Remix.ethereum.org](https://remix.ethereum.org)
2. Connect your wallet
3. Load the contract ABI
4. Interact with deployed contracts

## 🏦 Vault Use Cases

### Investment Pools
- Users deposit ETH into vaults associated with popular NFT collections
- Vault shares represent proportional ownership of the pooled funds
- Can be used for yield farming, staking, or collective investments

### NFT Backing
- Vaults can hold assets that back the value of NFT collections
- Provides liquidity and price discovery for NFT markets
- Enables fractional ownership of valuable NFT assets

### DeFi Integration
- Vault shares can be used as collateral in lending protocols
- Integration with DEXs for trading vault shares
- Yield generation through DeFi strategies

## 🚨 Important Security Notes

1. **Never share your private key**
2. **Use testnets for development**
3. **Test thoroughly before mainnet**
4. **Keep your deployment addresses safe**
5. **Verify contracts after deployment**
6. **Understand vault risks before depositing funds**
7. **Check vault limits and fees before transactions**

## 🆘 Troubleshooting

### Common Issues

#### "Insufficient funds"
- Get test ETH from faucets
- Check your wallet balance

#### "Nonce too low"
- Wait for pending transactions
- Reset MetaMask account

#### "Contract verification failed"
- Check constructor arguments
- Ensure correct compiler version

#### "Gas estimation failed"
- Check contract parameters
- Ensure sufficient gas limit

#### "Vault not active"
- Check if vault is paused
- Contact vault owner

#### "Exceeds deposit limit"
- Check vault's current deposit limit
- Wait for other users to withdraw

## 📞 Getting Help

If you encounter issues:

1. Check the error messages in the terminal
2. Verify your environment variables
3. Ensure you have test ETH
4. Check network connectivity
5. Review contract parameters
6. Check vault status and limits

## 🎯 Next Steps

After successful deployment:

1. **Create your first NFT collection with vault**
2. **Mint some test NFTs**
3. **Test vault deposits and withdrawals**
4. **Set up metadata storage** (IPFS, Arweave, etc.)
5. **Build a frontend** to interact with contracts and vaults
6. **Integrate with DeFi protocols** for yield generation
7. **Deploy to mainnet** (when ready)

## 📄 License

This project is licensed under the MIT License.

---

**Happy Deploying! 🚀** 