const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);

  // Superfluid addresses (mainnet)
  const host = "0x3E14dC1b13c488a8d5D310918780c983bD5982E7";
  const cfa = "0x6EeE6060f715257b970700bc2656De21dEdF074C";
  
  // Deploy Mock SuperToken for testing
  const MockSuperToken = await hre.ethers.getContractFactory("MockSuperToken");
  const mockSuperToken = await MockSuperToken.deploy();
  await mockSuperToken.waitForDeployment();
  console.log("MockSuperToken deployed to:", await mockSuperToken.getAddress());

  // Deploy SuperfluidStream
  const SuperfluidStream = await hre.ethers.getContractFactory("SuperfluidStream");
  const superfluidStream = await SuperfluidStream.deploy(
    host,
    cfa,
    await mockSuperToken.getAddress()
  );
  await superfluidStream.waitForDeployment();
  console.log("SuperfluidStream deployed to:", await superfluidStream.getAddress());
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 