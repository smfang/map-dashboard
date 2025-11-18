// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

interface ICarbonIndexLike {
    function getIndex() external view returns (uint256);
}

/**
 * @title ProjectVault
 * @dev Minimal ERC-4626 compliant vault representing a project. Holds a single
 *      underlying ERC20 asset and exposes associated project metadata and
 *      optional carbon index source.
 */
contract ProjectVault is ERC4626, Ownable, ReentrancyGuard {
    // Project identifier (e.g., geohash or keccak of lat/lon bounds)
    bytes32 public immutable projectId;

    // Optional carbon index source (e.g., CarbonIndex contract)
    address public indexSource;

    event IndexSourceUpdated(address indexed oldSource, address indexed newSource);

    constructor(
        ERC20 underlyingAsset,
        string memory vaultName,
        string memory vaultSymbol,
        bytes32 _projectId,
        address _indexSource,
        address owner_
    )
        ERC20(vaultName, vaultSymbol)
        ERC4626(underlyingAsset)
    {
        projectId = _projectId;
        indexSource = _indexSource;
        _transferOwnership(owner_);
    }

    function setIndexSource(address newSource) external onlyOwner {
        address old = indexSource;
        indexSource = newSource;
        emit IndexSourceUpdated(old, newSource);
    }

    function getProjectInfo() external view returns (
        bytes32 _projectId,
        address _asset,
        address _indexSource,
        uint256 _currentIndex
    ) {
        _projectId = projectId;
        _asset = address(asset());
        _indexSource = indexSource;
        _currentIndex = _readIndex();
    }

    function _readIndex() internal view returns (uint256) {
        if (indexSource == address(0)) return 0;
        try ICarbonIndexLike(indexSource).getIndex() returns (uint256 v) {
            return v;
        } catch {
            return 0;
        }
    }
}
