// Integration Instructions: https://docs.tenderly.co/node/integrations-smart-contract-frameworks/hardhat
import { HardhatUserConfig, task, types } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as tenderly from "@tenderly/hardhat-tenderly";
import * as dotenv from 'dotenv';

dotenv.config();
tenderly.setup({ automaticVerifications: true });

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  defaultNetwork: "tenderly",
  networks: {
    // Local development network
    localhost: {
      url: "http://127.0.0.1:8545"
    },
    // Sepolia testnet (Ethereum) - using Tenderly RPC
    sepolia: {
      url: process.env.SEPOLIA_URL || "https://sepolia.infura.io/v3/YOUR-PROJECT-ID",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    },
    // Mumbai testnet (Polygon)
    mumbai: {
      url: process.env.MUMBAI_URL || "https://polygon-mumbai.infura.io/v3/YOUR-PROJECT-ID",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    },
    // Base Sepolia testnet
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_URL || "https://sepolia.base.org",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 84532
    },
    // Tenderly RPC service for enhanced debugging and simulation
    tenderly: {
      url: "https://sepolia.gateway.tenderly.co/6gKmq8GzMquyyN3AbKvPY9",
      chainId: 11155111,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    },
    // Tenderly fork networks for testing
    tenderlyFork: {
      url: process.env.TENDERLY_FORK_URL || "https://rpc.tenderly.co/fork/YOUR_FORK_ID",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    }
  },
  etherscan: {
    apiKey: {
      sepolia: process.env.ETHERSCAN_API_KEY,
      baseSepolia: process.env.BASESCAN_API_KEY || process.env.ETHERSCAN_API_KEY
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia-explorer.base.org"
        }
      }
    ]
  },
  tenderly: {
    username: "samfang",
    project: "project",
    privateVerification: true
  }
};

export default config; 