# Solidity Workspace

This folder contains smart contracts, Hardhat configuration, deployment scripts, and build artifacts.

## Structure

- `contracts/`
  - `CarbonIndex.sol` — Stores carbon index values, supports updates via verified proofs
  - `SP1Verifier.sol` — Verifies SP1 zk proofs and exposes public values
  - `InputOracle.sol` — Simple oracle interface (legacy/mock)
  - `UMAInputOracle.sol` — UMA OOV3 Data Asserter style input oracle
  - `NFTFactory.sol`, `NFTVault.sol`, `ProjectNFT.sol` — NFT + vault system
- `scripts/` — Deployment and interaction scripts
- `hardhat.config.js` — Hardhat configuration
- `deploy.sh` — Convenience deployment script
- `artifacts/`, `cache/` — Build outputs (auto-generated)
- `new_project/` — Scaffolding/examples

## Quickstart

```bash
cd solidity
npm install
npx hardhat compile

# Start local node
npx hardhat node

# Deploy (example)
npx hardhat run scripts/deploy.js --network localhost
```

## Environment

- Node.js 16+
- Hardhat toolbox
- (Optional) Etherscan/Polygonscan API keys for verification

## Notes

- Addresses produced here should be referenced by the frontend and Python tools as needed.
- UMA OOV3 Data Asserter docs: https://docs.uma.xyz/developers/optimistic-oracle-v3/data-asserter
