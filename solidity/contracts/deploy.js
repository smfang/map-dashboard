// Deployment script for Natural Hazard Index Data Service
const { ethers } = require("hardhat");

async function main() {
    console.log("Deploying Natural Hazard Index Data Service...");
    
    // Get deployer account
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with account:", deployer.address);
    console.log("Account balance:", (await deployer.getBalance()).toString());
    
    // Deploy InputOracle first
    console.log("\n1. Deploying InputOracle...");
    const InputOracle = await ethers.getContractFactory("InputOracle");
    const oracle = await InputOracle.deploy();
    await oracle.deployed();
    console.log("InputOracle deployed to:", oracle.address);
    
    // Deploy IndexToken with Oracle address
    console.log("\n2. Deploying IndexToken...");
    const IndexToken = await ethers.getContractFactory("IndexToken");
    const indexToken = await IndexToken.deploy(oracle.address);
    await indexToken.deployed();
    console.log("IndexToken deployed to:", indexToken.address);
    
    // Deploy IndexContract with IndexToken and Oracle addresses
    console.log("\n3. Deploying IndexContract...");
    const IndexContract = await ethers.getContractFactory("IndexContract");
    const indexContract = await IndexContract.deploy(indexToken.address, oracle.address);
    await indexContract.deployed();
    console.log("IndexContract deployed to:", indexContract.address);
    
    // Deploy IndexVault with all contract addresses
    console.log("\n4. Deploying IndexVault...");
    const IndexVault = await ethers.getContractFactory("IndexVault");
    const vault = await IndexVault.deploy(
        indexToken.address,
        indexContract.address,
        oracle.address
    );
    await vault.deployed();
    console.log("IndexVault deployed to:", vault.address);
    
    // Initialize with some mock data
    console.log("\n5. Initializing with mock data...");
    
    // Update oracle with initial rainfall data (45mm as in indexcalc.py)
    const initialRainfall = ethers.utils.parseEther("45"); // 45mm scaled
    await oracle.updateIndex(initialRainfall);
    console.log("Oracle initialized with 45mm rainfall");
    
    // Update index token price
    await indexToken.updatePrice();
    console.log("Index token price updated");
    
    // Take initial snapshot in index contract
    await indexContract.takeSnapshot();
    console.log("Initial snapshot taken");
    
    // Summary
    console.log("\n=== DEPLOYMENT SUMMARY ===");
    console.log("InputOracle:", oracle.address);
    console.log("IndexToken:", indexToken.address);
    console.log("IndexContract:", indexContract.address);
    console.log("IndexVault:", vault.address);
    
    // Get initial metrics
    const currentPrice = await indexToken.getCurrentPrice();
    const [nhiScore, rainfall, timestamp, isValid] = await oracle.getCurrentIndex();
    const sharePrice = await vault.getCurrentSharePrice();
    
    console.log("\n=== INITIAL METRICS ===");
    console.log("Index Token Price:", ethers.utils.formatEther(currentPrice), "ETH");
    console.log("NHI Score:", ethers.utils.formatEther(nhiScore));
    console.log("Rainfall:", ethers.utils.formatEther(rainfall), "mm");
    console.log("Vault Share Price:", ethers.utils.formatEther(sharePrice), "ETH");
    console.log("Oracle Valid:", isValid);
    
    // Save deployment addresses to file
    const deploymentInfo = {
        network: await ethers.provider.getNetwork(),
        deployer: deployer.address,
        contracts: {
            InputOracle: oracle.address,
            IndexToken: indexToken.address,
            IndexContract: indexContract.address,
            IndexVault: vault.address
        },
        timestamp: new Date().toISOString(),
        initialMetrics: {
            tokenPrice: ethers.utils.formatEther(currentPrice),
            nhiScore: ethers.utils.formatEther(nhiScore),
            rainfall: ethers.utils.formatEther(rainfall),
            sharePrice: ethers.utils.formatEther(sharePrice)
        }
    };
    
    const fs = require('fs');
    fs.writeFileSync(
        './deployment-info.json', 
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("\nDeployment info saved to deployment-info.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
