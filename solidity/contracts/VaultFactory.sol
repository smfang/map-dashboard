// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./ProjectVault.sol";

/**
 * @title VaultFactory
 * @dev Deploys ERC-4626 ProjectVault instances per project/geography.
 */
contract VaultFactory is Ownable {
    event VaultDeployed(address indexed vault, address indexed asset, bytes32 indexed projectId, address indexSource, address owner);

    function deployVault(
        address asset,
        string memory vaultName,
        string memory vaultSymbol,
        bytes32 projectId,
        address indexSource,
        address owner_
    ) external onlyOwner returns (address) {
        require(asset != address(0), "invalid asset");
        ERC20 underlying = ERC20(asset);
        ProjectVault vault = new ProjectVault(
            underlying,
            vaultName,
            vaultSymbol,
            projectId,
            indexSource,
            owner_
        );
        emit VaultDeployed(address(vault), asset, projectId, indexSource, owner_);
        return address(vault);
    }
}
