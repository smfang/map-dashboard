// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title GeoIndexToken
 * @dev ERC20 whose total supply mirrors a geography's index (1e18 scaled),
 *      mint/burn controlled by an authorized updater. Intended for display or
 *      composability; not a claim on assets by default.
 */
contract GeoIndexToken is ERC20, Ownable {
    // Authorized updater that can set supply based on index
    address public updater;

    event UpdaterChanged(address indexed oldUpdater, address indexed newUpdater);

    constructor(string memory name_, string memory symbol_, address owner_) ERC20(name_, symbol_) {
        _transferOwnership(owner_);
    }

    modifier onlyUpdater() {
        require(msg.sender == updater || msg.sender == owner(), "not updater");
        _;
    }

    function setUpdater(address newUpdater) external onlyOwner {
        address old = updater;
        updater = newUpdater;
        emit UpdaterChanged(old, newUpdater);
    }

    // Set total supply to mirror indexValue (1e18 scaled) by minting/burning to owner
    function syncSupply(uint256 indexValue) external onlyUpdater {
        address treasury = owner();
        uint256 current = totalSupply();
        if (indexValue > current) {
            _mint(treasury, indexValue - current);
        } else if (indexValue < current) {
            _burn(treasury, current - indexValue);
        }
    }
}
