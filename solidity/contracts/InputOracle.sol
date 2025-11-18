// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

interface ICarbonIndex {
    function getIndex() external view returns (uint256);
}

// UMA-like Input Oracle mock: returns the latest value from a data source (CarbonIndex)
// and allows the owner to switch the source or apply a multiplier for testing.
contract InputOracle is Ownable {
    ICarbonIndex public dataSource;
    // Optional multiplier (1e18 fixed-point) to simulate oracle scaling or staleness adjustments
    uint256 public multiplier; // 1e18 means no change

    event DataSourceUpdated(address indexed oldSource, address indexed newSource);
    event MultiplierUpdated(uint256 oldMultiplier, uint256 newMultiplier);

    constructor(address initialSource) {
        require(initialSource != address(0), "invalid source");
        dataSource = ICarbonIndex(initialSource);
        multiplier = 1e18;
    }

    function setDataSource(address newSource) external onlyOwner {
        require(newSource != address(0), "invalid source");
        address old = address(dataSource);
        dataSource = ICarbonIndex(newSource);
        emit DataSourceUpdated(old, newSource);
    }

    function setMultiplier(uint256 newMultiplier) external onlyOwner {
        uint256 old = multiplier;
        multiplier = newMultiplier;
        emit MultiplierUpdated(old, newMultiplier);
    }

    // Returns 1e18-scaled oracle value
    function latest() external view returns (uint256) {
        uint256 base = dataSource.getIndex();
        // scale: base (1e18) * multiplier (1e18) / 1e18 => 1e18
        return (base * multiplier) / 1e18;
    }
}


