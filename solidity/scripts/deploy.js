const { ethers, network } = require("hardhat");

// Helper functions for ethers v5/v6 compatibility
const parseEther = (value) => {
  if (ethers.parseEther) {
    return ethers.parseEther(value);
  } else if (ethers.utils && ethers.utils.parseEther) {
    return ethers.utils.parseEther(value);
  }
  throw new Error("parseEther not available");
};

const formatEther = (value) => {
  if (ethers.formatEther) {
    return ethers.formatEther(value);
  } else if (ethers.utils && ethers.utils.formatEther) {
    return ethers.utils.formatEther(value);
  }
  throw new Error("formatEther not available");
};

async function main() {
  console.log("🚀 Starting NFT Factory and NFT Contract deployment...\n");

  // Get the deployer account
  const [deployer] = await ethers.getSigners();
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("📝 Deploying contracts with account:", deployer.address);
  console.log("💰 Account balance:", balance.toString(), "wei\n");

  // Deploy NFT Factory first
  console.log("🏭 Deploying NFT Factory...");
  const NFTFactory = await ethers.getContractFactory("NFTFactory");
  
  // Set factory fee to 0.01 ETH (in wei)
  const factoryFee = parseEther("0.01");
  const nftFactoryContract = await NFTFactory.deploy(factoryFee);
  await nftFactoryContract.waitForDeployment();
  const nftFactoryAddress = await nftFactoryContract.getAddress();
  
  // Get contract instance for interaction
  const nftFactory = NFTFactory.attach(nftFactoryAddress);
  
  console.log("✅ NFT Factory deployed to:", nftFactoryAddress);
  console.log("💰 Factory fee set to:", formatEther(factoryFee), "ETH\n");

  // Deploy a sample NFT collection through the factory
  console.log("🎨 Creating sample NFT collection with associated vault...");
  
  const collectionName = "My First Collection";
  const collectionSymbol = "MFC";
  const maxSupply = 1000;
  const mintPrice = parseEther("0.001"); // 0.001 ETH per NFT
  const baseURI = "https://api.example.com/metadata/"; // Replace with your metadata API
  
  console.log("📋 Collection details:");
  console.log("   Name:", collectionName);
  console.log("   Symbol:", collectionSymbol);
  console.log("   Max Supply:", maxSupply);
  console.log("   Mint Price:", formatEther(mintPrice), "ETH");
  console.log("   Base URI:", baseURI);
  console.log();

  // Create the collection (this will cost the factory fee)
  const tx = await nftFactory.createNFTCollection(
    collectionName,
    collectionSymbol,
    maxSupply,
    mintPrice,
    baseURI,
    { value: factoryFee }
  );
  
  console.log("⏳ Transaction sent:", tx.hash);
  console.log("⏳ Waiting for confirmation...");
  
  const receipt = await tx.wait();
  console.log("✅ Transaction confirmed in block:", receipt.blockNumber);
  
  // Get the deployed NFT and vault addresses from the event
  const event = receipt.events.find(event => event.event === 'NFTCollectionCreated');
  const deployedNFTAddress = event.args.nftAddress;
  const deployedVaultAddress = event.args.vaultAddress;
  
  console.log("🎉 Sample NFT Collection deployed to:", deployedNFTAddress);
  console.log("🏦 Associated Vault deployed to:", deployedVaultAddress);
  console.log("👤 Collection creator:", event.args.creator);
  console.log();

  // Get factory statistics
  const totalCollections = await nftFactory.getTotalCollections();
  const deployedNFTs = await nftFactory.getDeployedNFTs();
  
  console.log("📊 Factory Statistics:");
  console.log("   Total Collections:", totalCollections.toString());
  console.log("   Deployed NFTs:", deployedNFTs);
  console.log();

  // Verify the NFT contract
  const MyNFT = await ethers.getContractFactory("MyNFT");
  const nftContract = MyNFT.attach(deployedNFTAddress);
  
  const nftName = await nftContract.name();
  const nftSymbol = await nftContract.symbol();
  const nftMaxSupply = await nftContract.maxSupply();
  const nftMintPrice = await nftContract.mintPrice();
  
  console.log("🔍 NFT Contract Verification:");
  console.log("   Name:", nftName);
  console.log("   Symbol:", nftSymbol);
  console.log("   Max Supply:", nftMaxSupply.toString());
  console.log("   Mint Price:", ethers.utils.formatEther(nftMintPrice), "ETH");
  console.log();

  // Verify the vault contract
  const NFTVault = await ethers.getContractFactory("NFTVault");
  const vaultContract = NFTVault.attach(deployedVaultAddress);
  
  const vaultName = await vaultContract.vaultName();
  const vaultSymbol = await vaultContract.vaultSymbol();
  const vaultActive = await vaultContract.vaultActive();
  const nftContractAddress = await vaultContract.nftContract();
  
  console.log("🏦 Vault Contract Verification:");
  console.log("   Name:", vaultName);
  console.log("   Symbol:", vaultSymbol);
  console.log("   Active:", vaultActive);
  console.log("   Linked NFT:", nftContractAddress);
  console.log();

  // Test vault functionality
  console.log("🧪 Testing vault functionality...");
  
  // Get vault info
  const vaultInfo = await vaultContract.getVaultInfo();
  console.log("   Total Assets:", formatEther(vaultInfo._totalAssets), "ETH");
  console.log("   Total Shares:", vaultInfo._totalShares.toString());
  console.log("   Current Deposit Limit:", formatEther(vaultInfo._currentDepositLimit), "ETH");
  console.log("   Max Deposit Limit:", formatEther(vaultInfo._maxDepositLimit), "ETH");
  console.log();

  // Test deposit functionality (optional - requires ETH)
  console.log("💡 To test vault deposits:");
  console.log("   1. Connect to the vault contract:", deployedVaultAddress);
  console.log("   2. Call deposit() with some ETH");
  console.log("   3. Check your vault shares balance");
  console.log();

  console.log("🎯 Deployment Summary:");
  console.log("   NFT Factory:", nftFactoryAddress);
  console.log("   Sample NFT Collection:", deployedNFTAddress);
  console.log("   Associated Vault:", deployedVaultAddress);
  console.log("   Network:", network.name);
  console.log("   Deployer:", deployer.address);
  console.log();

  // Save deployment addresses for future use
  const deploymentInfo = {
    network: network.name,
    deployer: deployer.address,
    nftFactory: nftFactoryAddress,
    sampleNFT: deployedNFTAddress,
    sampleVault: deployedVaultAddress,
    factoryFee: formatEther(factoryFee),
    collectionName,
    collectionSymbol,
    maxSupply: maxSupply.toString(),
    mintPrice: formatEther(mintPrice),
    baseURI
  };

  console.log("💾 Deployment info saved. You can use these addresses to:");
  console.log("   1. Interact with the NFT Factory");
  console.log("   2. Mint NFTs from the sample collection");
  console.log("   3. Create new NFT collections with vaults");
  console.log("   4. Deposit/withdraw from vaults");
  console.log("   5. View on block explorers (if on testnet)");
  console.log();

  if (network.name !== "localhost") {
    console.log("🔍 View your contracts on:");
    let explorerUrl;
    if (network.name === "baseSepolia") {
      explorerUrl = "https://sepolia-explorer.base.org/address";
    } else if (network.name === "sepolia") {
      explorerUrl = "https://sepolia.etherscan.io/address";
    } else {
      explorerUrl = `https://${network.name}.etherscan.io/address`;
    }
    console.log("   NFT Factory:", `${explorerUrl}/${nftFactoryAddress}`);
    console.log("   Sample NFT:", `${explorerUrl}/${deployedNFTAddress}`);
    console.log("   Sample Vault:", `${explorerUrl}/${deployedVaultAddress}`);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  }); 