const { ethers } = require("hardhat");

async function main() {
  console.log("🏦 NFT Vault Interaction Script\n");

  // Configuration - replace with your deployed contract addresses
  const NFT_FACTORY_ADDRESS = "YOUR_NFT_FACTORY_ADDRESS";
  const NFT_COLLECTION_ADDRESS = "YOUR_NFT_COLLECTION_ADDRESS";
  const VAULT_ADDRESS = "YOUR_VAULT_ADDRESS";

  // Get signer
  const [signer] = await ethers.getSigners();
  console.log("👤 Connected account:", signer.address);
  console.log(
    "💰 Balance:",
    ethers.utils.formatEther(await signer.getBalance()),
    "ETH\n"
  );

  try {
    // Get contract instances
    const NFTFactory = await ethers.getContractFactory("NFTFactory");
    const MyNFT = await ethers.getContractFactory("MyNFT");
    const NFTVault = await ethers.getContractFactory("NFTVault");

    const factory = NFTFactory.attach(NFT_FACTORY_ADDRESS);
    const nftContract = MyNFT.attach(NFT_COLLECTION_ADDRESS);
    const vaultContract = NFTVault.attach(VAULT_ADDRESS);

    console.log("📋 Contract Information:");
    console.log("   NFT Factory:", NFT_FACTORY_ADDRESS);
    console.log("   NFT Collection:", NFT_COLLECTION_ADDRESS);
    console.log("   Vault:", VAULT_ADDRESS);
    console.log();

    // Get vault information
    console.log("🏦 Vault Information:");
    const vaultInfo = await vaultContract.getVaultInfo();
    console.log("   Vault Name:", vaultInfo._vaultName);
    console.log("   Vault Symbol:", vaultInfo._vaultSymbol);
    console.log("   Active:", vaultInfo._vaultActive);
    console.log(
      "   Total Assets:",
      ethers.utils.formatEther(vaultInfo._totalAssets),
      "ETH"
    );
    console.log("   Total Shares:", vaultInfo._totalShares.toString());
    console.log(
      "   Current Deposit Limit:",
      ethers.utils.formatEther(vaultInfo._currentDepositLimit),
      "ETH"
    );
    console.log(
      "   Max Deposit Limit:",
      ethers.utils.formatEther(vaultInfo._maxDepositLimit),
      "ETH"
    );
    console.log();

    // Check user's vault shares
    const userShares = await vaultContract.balanceOf(signer.address);
    console.log("👤 Your Vault Shares:", userShares.toString());
    console.log();

    // Example: Deposit ETH into vault
    console.log("💡 To deposit ETH into the vault:");
    console.log("   const depositAmount = ethers.utils.parseEther('0.1');");
    console.log(
      "   const tx = await vaultContract.deposit(depositAmount, signer.address, { value: depositAmount });"
    );
    console.log("   await tx.wait();");
    console.log();

    // Example: Check deposit preview
    const sampleDeposit = ethers.utils.parseEther("0.1");
    const sharesPreview = await vaultContract.previewDeposit(sampleDeposit);
    console.log("📊 Deposit Preview (0.1 ETH):");
    console.log("   ETH to deposit:", ethers.utils.formatEther(sampleDeposit));
    console.log("   Shares to receive:", sharesPreview.toString());
    console.log();

    // Example: Check withdrawal preview
    if (userShares.gt(0)) {
      const assetsPreview = await vaultContract.previewRedeem(userShares);
      console.log("📊 Withdrawal Preview (all shares):");
      console.log("   Shares to redeem:", userShares.toString());
      console.log(
        "   ETH to receive:",
        ethers.utils.formatEther(assetsPreview)
      );
      console.log();
    }

    // Example: Check max deposit/withdraw
    const maxDeposit = await vaultContract.maxDeposit(signer.address);
    const maxWithdraw = await vaultContract.maxWithdraw(signer.address);
    console.log("📊 Limits:");
    console.log("   Max deposit:", ethers.utils.formatEther(maxDeposit), "ETH");
    console.log(
      "   Max withdraw:",
      ethers.utils.formatEther(maxWithdraw),
      "ETH"
    );
    console.log();

    // Example: Check NFT ownership
    const nftBalance = await nftContract.balanceOf(signer.address);
    console.log("🎨 NFT Information:");
    console.log("   Your NFT balance:", nftBalance.toString());
    console.log("   NFT name:", await nftContract.name());
    console.log("   NFT symbol:", await nftContract.symbol());
    console.log("   Max supply:", (await nftContract.maxSupply()).toString());
    console.log(
      "   Mint price:",
      ethers.utils.formatEther(await nftContract.mintPrice()),
      "ETH"
    );
    console.log();

    // Example: Mint an NFT (if you have enough ETH)
    const mintPrice = await nftContract.mintPrice();
    const userBalance = await signer.getBalance();

    if (userBalance.gte(mintPrice)) {
      console.log("💡 To mint an NFT:");
      console.log(
        "   const tx = await nftContract.mint('https://api.example.com/metadata/1', { value: mintPrice });"
      );
      console.log("   await tx.wait();");
      console.log();
    } else {
      console.log("⚠️  Insufficient balance to mint NFT");
      console.log("   Required:", ethers.utils.formatEther(mintPrice), "ETH");
      console.log(
        "   Available:",
        ethers.utils.formatEther(userBalance),
        "ETH"
      );
      console.log();
    }

    console.log("🚀 Ready to interact with your vault!");
    console.log(
      "   Use the examples above to deposit, withdraw, and manage your vault shares."
    );
  } catch (error) {
    console.error("❌ Error:", error.message);
    console.log("\n💡 Make sure to:");
    console.log("   1. Replace the contract addresses with your deployed ones");
    console.log("   2. Have some ETH in your wallet for transactions");
    console.log("   3. Be connected to the correct network");
  }
}

// Helper function to format large numbers
function formatNumber(num) {
  if (num >= 1e18) {
    return (num / 1e18).toFixed(4) + " ETH";
  } else if (num >= 1e9) {
    return (num / 1e9).toFixed(4) + " Gwei";
  } else {
    return num.toString();
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Script failed:", error);
    process.exit(1);
  });
