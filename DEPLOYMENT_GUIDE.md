# 🚀 Comprehensive Crypto Deployment Guide

This guide covers the complete deployment of the crypto infrastructure for the Nature Index Dashboard project, including smart contracts, oracles, and NFT systems.

## 📋 Project Overview

This project includes multiple interconnected smart contract systems:

- **Carbon Index System**: SP1 zk-proof verified carbon index tracking
- **NFT Factory & Vaults**: ERC-721 NFT collections with ERC-4626 vaults
- **Nature Index Tracker**: External oracle integration for nature unit pricing
- **Project Management**: Project-specific NFTs and vaults
- **Reward System**: Token rewards for participation

## 🔧 Enhanced Development Experience

This project now integrates **Tenderly RPC service** for superior development and debugging:

### 🚀 **Tenderly Integration Benefits**

- **🔍 Advanced Debugging**: Step-by-step transaction execution with detailed state changes
- **🧪 Simulation Engine**: Test complex scenarios before mainnet deployment
- **📊 Gas Analytics**: Optimize gas usage with detailed consumption reports
- **🔄 Fork Testing**: Create mainnet forks for realistic testing environments
- **📈 Real-time Monitoring**: Track contract interactions and performance
- **🛡️ Security Insights**: Identify potential vulnerabilities early
- **⚡ Fast RPC**: High-performance RPC endpoints for reliable development

## 🛠️ Prerequisites

### Required Software

- **Node.js** (version 16 or higher)
- **Git** for version control
- **MetaMask** wallet with test ETH
- **Infura account** (free) for blockchain access
- **Etherscan/Polygonscan accounts** for contract verification

### Required Knowledge

- Basic understanding of Ethereum and smart contracts
- Familiarity with command line tools
- Understanding of testnet vs mainnet deployment

## 🔧 Environment Setup

### 1. Install Dependencies

Navigate to the solidity directory and install dependencies:

```bash
cd solidity
npm install
```

**Note**: The project now uses TypeScript configuration with Tenderly integration for enhanced debugging capabilities.

### 2. Create Environment File

Create a `.env` file in the solidity directory:

```bash
# Network URLs (get from Infura/Alchemy)
SEPOLIA_URL=https://sepolia.infura.io/v3/YOUR-PROJECT-ID
MUMBAI_URL=https://polygon-mumbai.infura.io/v3/YOUR-PROJECT-ID
MAINNET_URL=https://mainnet.infura.io/v3/YOUR-PROJECT-ID
POLYGON_URL=https://polygon-mainnet.infura.io/v3/YOUR-PROJECT-ID

# Your private key (from MetaMask - remove 0x prefix)
PRIVATE_KEY=your_private_key_here_without_0x_prefix

# API Keys for contract verification
ETHERSCAN_API_KEY=your_etherscan_api_key_here
POLYGONSCAN_API_KEY=your_polygonscan_api_key_here

# Tenderly integration (Enhanced debugging and simulation)
TENDERLY_USERNAME=samfang
TENDERLY_PROJECT=project
TENDERLY_FORK_URL=https://rpc.tenderly.co/fork/YOUR_FORK_ID

# Optional: UMA Oracle configuration
UMA_ORACLE_ADDRESS=0x3E14dC1b13c488a8d5D310918780c983bD5982E7
```

### 3. Get Required API Keys

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

#### D. Polygonscan API Key

1. Go to [Polygonscan.com](https://polygonscan.com)
2. Create a free account
3. Go to API Keys section
4. Create a new API key

#### E. Tenderly Setup (Optional but Recommended)

1. Go to [Tenderly.co](https://tenderly.co)
2. Create a free account
3. Create a new project
4. Note your username and project name
5. Get your fork URL from the Tenderly dashboard

## 🚀 Deployment Options

### Option 1: Local Development (Recommended for Testing)

```bash
# Terminal 1: Start local blockchain
npx hardhat node

# Terminal 2: Deploy contracts
npx hardhat run scripts/deploy.js --network localhost
```

### Option 2: Tenderly RPC Service (Enhanced Debugging)

The project now uses **Tenderly RPC service** for enhanced debugging and simulation capabilities:

```bash
# Deploy using Tenderly RPC (Default network)
npx hardhat run scripts/deploy.js --network tenderly

# Or use the npm script
npm run deploy:tenderly
```

**Benefits of Tenderly RPC:**

- 🔍 **Enhanced Debugging**: Detailed transaction traces and state changes
- 🧪 **Simulation**: Test transactions before sending to mainnet
- 📊 **Analytics**: Gas usage analysis and optimization insights
- 🔄 **Forking**: Create forks of mainnet for testing
- 📈 **Monitoring**: Real-time contract monitoring and alerts

### Option 3: Testnet Deployment

#### Sepolia (Ethereum Testnet)

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

#### Mumbai (Polygon Testnet)

```bash
npx hardhat run scripts/deploy.js --network mumbai
```

### Option 4: Tenderly Fork Testing

Create a fork of mainnet for testing with real state:

```bash
# Deploy to Tenderly fork
npx hardhat run scripts/deploy.js --network tenderlyFork

# Or use the npm script
npm run deploy:tenderly-fork
```

### Option 5: Mainnet Deployment (Production)

⚠️ **WARNING**: Only deploy to mainnet after thorough testing!

```bash
# Ethereum Mainnet
npx hardhat run scripts/deploy.js --network mainnet

# Polygon Mainnet
npx hardhat run scripts/deploy.js --network polygon
```

## 📦 What Gets Deployed

### Core Contracts

1. **CarbonIndex.sol** - SP1 zk-proof verified carbon index storage
2. **SP1Verifier.sol** - Zero-knowledge proof verification
3. **InputOracle.sol** - Simple oracle interface
4. **UMAInputOracle.sol** - UMA OOV3 Data Asserter integration

### NFT & Vault System

5. **NFTFactory.sol** - Factory for creating NFT collections
6. **ProjectNFT.sol** - ERC-721 NFT collections
7. **NFTVault.sol** - ERC-4626 vaults linked to NFT collections
8. **VaultFactory.sol** - Factory for creating project vaults

### Token & Reward System

9. **GeoIndexToken.sol** - ERC-20 token representing carbon index
10. **RewardToken.sol** - Reward token for participants
11. **NatureIndexTracker.sol** - Tracks nature unit values and correlations

### Project Management

12. **ProjectVault.sol** - Project-specific vaults with carbon index integration

## 🔄 Deployment Process

### Step 1: Compile Contracts

```bash
# Compile with TypeScript support
npx hardhat compile

# Or use the npm script
npm run compile
```

### Step 2: Run Tests (Optional but Recommended)

```bash
npx hardhat test
```

### Step 3: Deploy Core System

The main deployment script will deploy contracts in the following order:

1. **SP1Verifier** - Zero-knowledge proof verifier
2. **CarbonIndex** - Main carbon index contract
3. **InputOracle** - Simple oracle for testing
4. **UMAInputOracle** - UMA integration oracle
5. **NFTFactory** - NFT collection factory
6. **Sample NFT Collection** - Test NFT with associated vault
7. **VaultFactory** - Project vault factory
8. **GeoIndexToken** - Carbon index token
9. **RewardToken** - Reward token
10. **NatureIndexTracker** - Nature unit tracker

### Step 4: Verify Contracts (Testnet/Mainnet)

```bash
# Verify on Etherscan
npx hardhat verify --network sepolia <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>

# Verify on Polygonscan
npx hardhat verify --network mumbai <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
```

## 🧪 Testing Your Deployment

### 1. Check Contract Addresses

After deployment, you'll receive addresses for all contracts. Save these for frontend integration.

### 2. Test Core Functions

```bash
# Test vault interactions
npx hardhat run scripts/vault-interactions.js --network localhost

# Test NFT minting
npx hardhat run scripts/deploy-nft-wrapper.js --network localhost

# Test with Tenderly RPC (enhanced debugging)
npx hardhat run scripts/vault-interactions.js --network tenderly
```

### 3. Available NPM Scripts

The project now includes convenient npm scripts for different deployment scenarios:

```bash
# Local development
npm run deploy:local

# Testnet deployment (Sepolia)
npm run deploy:testnet

# Tenderly RPC deployment (enhanced debugging)
npm run deploy:tenderly

# Tenderly fork deployment (mainnet fork testing)
npm run deploy:tenderly-fork

# Compile contracts
npm run compile

# Run tests
npm run test
```

### 4. Verify on Block Explorers

- **Sepolia**: https://sepolia.etherscan.io
- **Mumbai**: https://mumbai.polygonscan.com
- **Mainnet**: https://etherscan.io
- **Polygon**: https://polygonscan.com

## 🔧 Advanced Deployment Options

### Tenderly-Specific Features

#### Enhanced Debugging with Tenderly

```bash
# Deploy with Tenderly for enhanced debugging
npx hardhat run scripts/deploy.js --network tenderly

# View detailed transaction traces in Tenderly dashboard
# Access: https://dashboard.tenderly.co
```

#### Fork Testing

```bash
# Create a mainnet fork for testing
# 1. Go to Tenderly dashboard
# 2. Create a new fork
# 3. Copy the fork URL to your .env file
# 4. Deploy to fork
npx hardhat run scripts/deploy.js --network tenderlyFork
```

#### Simulation and Testing

```bash
# Simulate transactions before deployment
npx hardhat console --network tenderly

# Test complex scenarios with real mainnet state
npx hardhat run scripts/vault-interactions.js --network tenderlyFork
```

### Custom Deployment Scripts

#### Deploy Specific Components

```bash
# Deploy only NFT system
npx hardhat run scripts/deploy-nft-wrapper.js --network localhost

# Deploy only vault system
npx hardhat run scripts/vault-interactions.js --network localhost

# Deploy with Tenderly debugging
npx hardhat run scripts/deploy-nft-wrapper.js --network tenderly
```

#### Deploy with Custom Parameters

You can modify the deployment scripts to customize:

- Factory fees
- Mint prices
- Vault parameters
- Oracle addresses
- Token parameters

### Gas Optimization

For mainnet deployment, consider:

- Using gas estimation tools
- Deploying during low-gas periods
- Using gas optimization techniques
- Batch deployments where possible

## 🚨 Troubleshooting

### Common Issues

#### "Insufficient funds"

- **Solution**: Get test ETH from faucets
- **Sepolia Faucet**: https://sepoliafaucet.com
- **Mumbai Faucet**: https://faucet.polygon.technology

#### "Nonce too low"

- **Solution**: Wait for pending transactions to confirm
- **Alternative**: Reset nonce in MetaMask

#### "Contract verification failed"

- **Solution**: Check constructor arguments match deployment
- **Debug**: Use `--show-stack-traces` flag

#### "Network connection failed"

- **Solution**: Check your RPC URL and API keys
- **Alternative**: Try different RPC providers (Alchemy, QuickNode)

#### "Out of gas"

- **Solution**: Increase gas limit in deployment script
- **Alternative**: Deploy contracts individually

### Debug Commands

```bash
# Show detailed error traces
npx hardhat run scripts/deploy.js --network localhost --show-stack-traces

# Check network connection
npx hardhat console --network sepolia

# Verify contract compilation
npx hardhat compile --force
```

## 📊 Post-Deployment

### 1. Save Contract Addresses

Create a deployment record with:

- Contract addresses
- Transaction hashes
- Block numbers
- Network information
- Constructor arguments

### 2. Update Frontend Configuration

Update your frontend with the deployed contract addresses:

- Update contract ABIs
- Configure network settings
- Set up wallet connections

### 3. Test Integration

- Test wallet connections
- Verify contract interactions
- Test all user flows
- Monitor for errors

### 4. Monitor and Maintain

- Set up monitoring for contract events
- Track gas usage
- Monitor for security issues
- Plan for upgrades

## 🔐 Security Considerations

### Before Mainnet Deployment

1. **Audit Contracts**: Consider professional security audits
2. **Test Thoroughly**: Use testnets extensively
3. **Review Code**: Have multiple developers review
4. **Documentation**: Maintain clear documentation
5. **Access Control**: Implement proper access controls

### Best Practices

- Use multi-signature wallets for admin functions
- Implement time locks for critical changes
- Regular security reviews
- Keep dependencies updated
- Monitor for unusual activity

## 📚 Next Steps

1. **Integrate with Frontend**: Connect deployed contracts to your React app
2. **Set up Monitoring**: Implement event monitoring and alerts
3. **User Testing**: Test with real users on testnet
4. **Documentation**: Create user guides and API documentation
5. **Mainnet Preparation**: Plan mainnet deployment strategy

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review contract documentation
3. Test on local network first
4. Use testnets for experimentation
5. Join community forums for help

Remember: Always test thoroughly before deploying to mainnet!
