const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);

  // Superfluid addresses (mainnet)
  const host = "0x3E14dC1b13c488a8d5D310918780c983bD5982E7";
  
  // Deploy Mock SuperToken for NFT wrapping
  const MockSuperToken = await hre.ethers.getContractFactory("MockSuperToken");
  const mockSuperToken = await MockSuperToken.deploy();
  await mockSuperToken.waitForDeployment();
  console.log("MockSuperToken deployed to:", await mockSuperToken.getAddress());

  // Deploy NFT contract (for testing)
  const MockNFT = await hre.ethers.getContractFactory("MockNFT");
  const mockNFT = await MockNFT.deploy();
  await mockNFT.waitForDeployment();
  console.log("MockNFT deployed to:", await mockNFT.getAddress());

  // Deploy NFTWrapper
  const NFTWrapper = await hre.ethers.getContractFactory("NFTWrapper");
  const nftWrapper = await NFTWrapper.deploy(
    host,
    await mockSuperToken.getAddress(),
    await mockNFT.getAddress()
  );
  await nftWrapper.waitForDeployment();
  console.log("NFTWrapper deployed to:", await nftWrapper.getAddress());
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 