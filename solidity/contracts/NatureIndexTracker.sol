// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

interface IGeoIndexToken {
    function totalSupply() external view returns (uint256);
    function decimals() external view returns (uint8);
}

interface IExternalOracle {
    function latest() external view returns (uint256);
}

/**
 * @title NatureIndexTracker
 * @dev Tracks the value of external nature units (carbon credits, biodiversity units, etc.)
 *      and correlates them with GeoIndexToken values. Provides pricing and conversion functions.
 */
contract NatureIndexTracker is Ownable, ReentrancyGuard {
    
    // External oracle for nature unit prices (e.g., carbon credit price per ton)
    address public externalOracle;
    
    // GeoIndexToken that represents the computed carbon index
    address public geoIndexToken;
    
    // Conversion rate: how many nature units per 1e18 scaled index point
    uint256 public conversionRate; // e.g., 1e18 = 1 ton CO2 equivalent
    
    // Price multiplier for nature units (scaled by 1e18)
    uint256 public priceMultiplier; // e.g., 1e18 = $50 per ton CO2
    
    // Track historical correlations
    struct IndexSnapshot {
        uint256 timestamp;
        uint256 geoIndexValue;
        uint256 natureUnitPrice;
        uint256 computedValue;
    }
    
    mapping(uint256 => IndexSnapshot) public snapshots;
    uint256 public snapshotCount;
    
    // Events
    event ExternalOracleUpdated(address indexed oldOracle, address indexed newOracle);
    event GeoIndexTokenUpdated(address indexed oldToken, address indexed newToken);
    event ConversionRateUpdated(uint256 oldRate, uint256 newRate);
    event PriceMultiplierUpdated(uint256 oldMultiplier, uint256 newMultiplier);
    event SnapshotCreated(uint256 indexed snapshotId, uint256 geoIndexValue, uint256 natureUnitPrice, uint256 computedValue);
    
    constructor(
        address _externalOracle,
        address _geoIndexToken,
        uint256 _conversionRate,
        uint256 _priceMultiplier
    ) {
        externalOracle = _externalOracle;
        geoIndexToken = _geoIndexToken;
        conversionRate = _conversionRate;
        priceMultiplier = _priceMultiplier;
    }
    
    // Admin functions
    function setExternalOracle(address newOracle) external onlyOwner {
        address old = externalOracle;
        externalOracle = newOracle;
        emit ExternalOracleUpdated(old, newOracle);
    }
    
    function setGeoIndexToken(address newToken) external onlyOwner {
        address old = geoIndexToken;
        geoIndexToken = newToken;
        emit GeoIndexTokenUpdated(old, newToken);
    }
    
    function setConversionRate(uint256 newRate) external onlyOwner {
        uint256 old = conversionRate;
        conversionRate = newRate;
        emit ConversionRateUpdated(old, newRate);
    }
    
    function setPriceMultiplier(uint256 newMultiplier) external onlyOwner {
        uint256 old = priceMultiplier;
        priceMultiplier = newMultiplier;
        emit PriceMultiplierUpdated(old, newMultiplier);
    }
    
    // Core functions
    function getCurrentGeoIndexValue() public view returns (uint256) {
        if (geoIndexToken == address(0)) return 0;
        try IGeoIndexToken(geoIndexToken).totalSupply() returns (uint256 value) {
            return value;
        } catch {
            return 0;
        }
    }
    
    function getCurrentNatureUnitPrice() public view returns (uint256) {
        if (externalOracle == address(0)) return 0;
        try IExternalOracle(externalOracle).latest() returns (uint256 price) {
            return price;
        } catch {
            return 0;
        }
    }
    
    function computeCurrentValue() public view returns (uint256) {
        uint256 geoValue = getCurrentGeoIndexValue();
        uint256 naturePrice = getCurrentNatureUnitPrice();
        
        if (geoValue == 0 || naturePrice == 0) return 0;
        
        // Convert geo index to nature units, then multiply by price
        // geoValue (1e18) * conversionRate (nature units per 1e18) * naturePrice (price per unit) * priceMultiplier / 1e18^3
        return (geoValue * conversionRate * naturePrice * priceMultiplier) / (1e18 * 1e18 * 1e18);
    }
    
    function createSnapshot() external nonReentrant returns (uint256 snapshotId) {
        uint256 geoValue = getCurrentGeoIndexValue();
        uint256 naturePrice = getCurrentNatureUnitPrice();
        uint256 computedValue = computeCurrentValue();
        
        snapshotId = snapshotCount;
        snapshots[snapshotId] = IndexSnapshot({
            timestamp: block.timestamp,
            geoIndexValue: geoValue,
            natureUnitPrice: naturePrice,
            computedValue: computedValue
        });
        
        snapshotCount++;
        
        emit SnapshotCreated(snapshotId, geoValue, naturePrice, computedValue);
    }
    
    function getLatestSnapshot() external view returns (IndexSnapshot memory) {
        require(snapshotCount > 0, "No snapshots available");
        return snapshots[snapshotCount - 1];
    }
    
    function getSnapshot(uint256 snapshotId) external view returns (IndexSnapshot memory) {
        require(snapshotId < snapshotCount, "Invalid snapshot ID");
        return snapshots[snapshotId];
    }
    
    // Conversion functions
    function convertGeoIndexToNatureUnits(uint256 geoIndexValue) public view returns (uint256) {
        return (geoIndexValue * conversionRate) / 1e18;
    }
    
    function convertNatureUnitsToValue(uint256 natureUnits) external view returns (uint256) {
        uint256 naturePrice = getCurrentNatureUnitPrice();
        if (naturePrice == 0) return 0;
        return (natureUnits * naturePrice * priceMultiplier) / (1e18 * 1e18);
    }
    
    // Get comprehensive current state
    function getCurrentState() external view returns (
        uint256 geoIndexValue,
        uint256 natureUnitPrice,
        uint256 computedValue,
        uint256 natureUnitsEquivalent,
        uint256 lastSnapshotId
    ) {
        geoIndexValue = getCurrentGeoIndexValue();
        natureUnitPrice = getCurrentNatureUnitPrice();
        computedValue = computeCurrentValue();
        natureUnitsEquivalent = convertGeoIndexToNatureUnits(geoIndexValue);
        lastSnapshotId = snapshotCount > 0 ? snapshotCount - 1 : 0;
    }
}
