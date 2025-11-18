// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

interface IGeoIndexToken {
    function totalSupply() external view returns (uint256);
    function decimals() external view returns (uint8);
}

/**
 * @title RewardToken
 * @dev ERC20 token that mints rewards when GeoIndexToken value increases.
 *      Tracks the last known index value and mints tokens proportionally
 *      when the index goes up, incentivizing positive environmental outcomes.
 */
contract RewardToken is ERC20, Ownable, ReentrancyGuard {
    
    // GeoIndexToken to track
    address public geoIndexToken;
    
    // Last recorded index value
    uint256 public lastIndexValue;
    
    // Minting parameters
    uint256 public mintRate; // How many reward tokens per 1e18 index increase
    uint256 public maxTotalSupply; // Maximum total supply cap
    uint256 public mintingEnabled; // Timestamp when minting becomes enabled
    
    // Tracking
    uint256 public totalMinted;
    uint256 public lastMintTimestamp;
    
    // Events
    event GeoIndexTokenUpdated(address indexed oldToken, address indexed newToken);
    event MintRateUpdated(uint256 oldRate, uint256 newRate);
    event MaxSupplyUpdated(uint256 oldMax, uint256 newMax);
    event RewardsMinted(address indexed to, uint256 amount, uint256 indexIncrease);
    event MintingEnabled(uint256 timestamp);
    
    constructor(
        string memory name_,
        string memory symbol_,
        address _geoIndexToken,
        uint256 _mintRate,
        uint256 _maxTotalSupply,
        address owner_
    ) ERC20(name_, symbol_) {
        geoIndexToken = _geoIndexToken;
        mintRate = _mintRate;
        maxTotalSupply = _maxTotalSupply;
        mintingEnabled = block.timestamp + 1 days; // Enable minting after 1 day
        
        // Initialize with current index value
        if (_geoIndexToken != address(0)) {
            try IGeoIndexToken(_geoIndexToken).totalSupply() returns (uint256 value) {
                lastIndexValue = value;
            } catch {
                lastIndexValue = 0;
            }
        }
        
        _transferOwnership(owner_);
    }
    
    // Admin functions
    function setGeoIndexToken(address newToken) external onlyOwner {
        address old = geoIndexToken;
        geoIndexToken = newToken;
        
        // Update last index value
        if (newToken != address(0)) {
            try IGeoIndexToken(newToken).totalSupply() returns (uint256 value) {
                lastIndexValue = value;
            } catch {
                lastIndexValue = 0;
            }
        }
        
        emit GeoIndexTokenUpdated(old, newToken);
    }
    
    function setMintRate(uint256 newRate) external onlyOwner {
        uint256 old = mintRate;
        mintRate = newRate;
        emit MintRateUpdated(old, newRate);
    }
    
    function setMaxTotalSupply(uint256 newMax) external onlyOwner {
        uint256 old = maxTotalSupply;
        maxTotalSupply = newMax;
        emit MaxSupplyUpdated(old, newMax);
    }
    
    function enableMinting() external onlyOwner {
        mintingEnabled = block.timestamp;
        emit MintingEnabled(block.timestamp);
    }
    
    // Core minting function
    function checkAndMintRewards(address recipient) external nonReentrant returns (uint256 mintedAmount) {
        require(block.timestamp >= mintingEnabled, "Minting not yet enabled");
        require(geoIndexToken != address(0), "No geo index token set");
        require(recipient != address(0), "Invalid recipient");
        
        // Get current index value
        uint256 currentIndexValue;
        try IGeoIndexToken(geoIndexToken).totalSupply() returns (uint256 value) {
            currentIndexValue = value;
        } catch {
            return 0; // If we can't read, don't mint
        }
        
        // Calculate increase
        if (currentIndexValue <= lastIndexValue) {
            return 0; // No increase, no rewards
        }
        
        uint256 indexIncrease = currentIndexValue - lastIndexValue;
        
        // Calculate reward amount
        mintedAmount = (indexIncrease * mintRate) / 1e18;
        
        // Check max supply
        if (totalSupply() + mintedAmount > maxTotalSupply) {
            mintedAmount = maxTotalSupply - totalSupply();
            if (mintedAmount == 0) return 0;
        }
        
        // Mint rewards
        if (mintedAmount > 0) {
            _mint(recipient, mintedAmount);
            totalMinted += mintedAmount;
            lastIndexValue = currentIndexValue;
            lastMintTimestamp = block.timestamp;
            
            emit RewardsMinted(recipient, mintedAmount, indexIncrease);
        }
        
        return mintedAmount;
    }
    
    // Batch minting for multiple recipients
    function batchCheckAndMintRewards(address[] calldata recipients) external nonReentrant returns (uint256 totalMintedAmount) {
        require(block.timestamp >= mintingEnabled, "Minting not yet enabled");
        require(geoIndexToken != address(0), "No geo index token set");
        
        // Get current index value once
        uint256 currentIndexValue;
        try IGeoIndexToken(geoIndexToken).totalSupply() returns (uint256 value) {
            currentIndexValue = value;
        } catch {
            return 0;
        }
        
        if (currentIndexValue <= lastIndexValue) {
            return 0; // No increase, no rewards
        }
        
        uint256 indexIncrease = currentIndexValue - lastIndexValue;
        uint256 rewardPerRecipient = (indexIncrease * mintRate) / (1e18 * recipients.length);
        
        if (rewardPerRecipient == 0) return 0;
        
        // Check if we can mint for all recipients
        uint256 totalNeeded = rewardPerRecipient * recipients.length;
        if (totalSupply() + totalNeeded > maxTotalSupply) {
            totalNeeded = maxTotalSupply - totalSupply();
            rewardPerRecipient = totalNeeded / recipients.length;
            if (rewardPerRecipient == 0) return 0;
        }
        
        // Mint for each recipient
        for (uint256 i = 0; i < recipients.length; i++) {
            if (recipients[i] != address(0)) {
                _mint(recipients[i], rewardPerRecipient);
                emit RewardsMinted(recipients[i], rewardPerRecipient, indexIncrease);
            }
        }
        
        totalMinted += totalNeeded;
        lastIndexValue = currentIndexValue;
        lastMintTimestamp = block.timestamp;
        
        return totalMintedAmount = totalNeeded;
    }
    
    // View functions
    function getCurrentIndexValue() external view returns (uint256) {
        if (geoIndexToken == address(0)) return 0;
        try IGeoIndexToken(geoIndexToken).totalSupply() returns (uint256 value) {
            return value;
        } catch {
            return 0;
        }
    }
    
    function getPendingRewards() external view returns (uint256) {
        if (geoIndexToken == address(0) || block.timestamp < mintingEnabled) return 0;
        
        uint256 currentIndexValue;
        try IGeoIndexToken(geoIndexToken).totalSupply() returns (uint256 value) {
            currentIndexValue = value;
        } catch {
            return 0;
        }
        
        if (currentIndexValue <= lastIndexValue) return 0;
        
        uint256 indexIncrease = currentIndexValue - lastIndexValue;
        uint256 pendingRewards = (indexIncrease * mintRate) / 1e18;
        
        // Cap by max supply
        if (totalSupply() + pendingRewards > maxTotalSupply) {
            pendingRewards = maxTotalSupply - totalSupply();
        }
        
        return pendingRewards;
    }
    
    function getTokenInfo() external view returns (
        address _geoIndexToken,
        uint256 _lastIndexValue,
        uint256 _mintRate,
        uint256 _maxTotalSupply,
        uint256 _totalMinted,
        uint256 _lastMintTimestamp,
        bool _mintingEnabled
    ) {
        _geoIndexToken = geoIndexToken;
        _lastIndexValue = lastIndexValue;
        _mintRate = mintRate;
        _maxTotalSupply = maxTotalSupply;
        _totalMinted = totalMinted;
        _lastMintTimestamp = lastMintTimestamp;
        _mintingEnabled = block.timestamp >= mintingEnabled;
    }
}
