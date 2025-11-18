// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

interface IInputOracle {
    function latest() external view returns (uint256);
}

contract NFTVault is ERC4626, Ownable, ReentrancyGuard {
    using Math for uint256;
    
    // The NFT contract this vault is associated with
    address public immutable nftContract;
    
    // Vault metadata
    string public vaultName;
    string public vaultSymbol;
    // Oracle to affect vault value via an index
    address public inputOracle; // expects contract with latest() -> 1e18-scaled
    uint256 private constant ONE = 1e18;

    
    // Vault state
    bool public vaultActive;
    uint256 public maxDepositLimit;
    uint256 public currentDepositLimit;
    
    // Events
    event VaultActivated(address indexed nftContract);
    event VaultDeactivated(address indexed nftContract);
    event DepositLimitUpdated(uint256 oldLimit, uint256 newLimit);
    event EmergencyWithdraw(address indexed owner, uint256 amount);
    
    constructor(
        address _nftContract,
        string memory _vaultName,
        string memory _vaultSymbol,
        address _owner
    ) ERC4626(IERC20(address(0))) ERC20(_vaultName, _vaultSymbol) {
        require(_nftContract != address(0), "Invalid NFT contract");
        require(_owner != address(0), "Invalid owner");
        
        nftContract = _nftContract;
        vaultName = _vaultName;
        vaultSymbol = _vaultSymbol;
        vaultActive = true;
        maxDepositLimit = type(uint256).max;
        currentDepositLimit = 0;
        
        _transferOwnership(_owner);
    }

    // Admin: set the input oracle address
    function setInputOracle(address oracle) external onlyOwner {
        inputOracle = oracle;
    }

    function _oraclePrice() internal view returns (uint256) {
        if (inputOracle == address(0)) {
            return ONE;
        }
        return IInputOracle(inputOracle).latest();
    }
    
    // Override decimals to match ETH (18 decimals)
    function decimals() public pure override returns (uint8) {
        return 18;
    }
    
    // Override asset to return ETH
    function asset() public pure override returns (address) {
        return address(0); // ETH
    }
    
    // Deposit ETH into the vault (payable function)
    function depositETH(address receiver) 
        public 
        payable 
        nonReentrant 
        returns (uint256 shares) 
    {
        require(vaultActive, "Vault is not active");
        require(msg.value > 0, "Cannot deposit 0");
        require(currentDepositLimit + msg.value <= maxDepositLimit, "Exceeds deposit limit");
        
        shares = previewDeposit(msg.value);
        require(shares > 0, "Invalid shares");
        
        _mint(receiver, shares);
        currentDepositLimit += msg.value;
        
        emit Deposit(msg.sender, receiver, msg.value, shares);
    }
    
    // Standard ERC4626 deposit function (for compatibility)
    function deposit(uint256 assets, address receiver) 
        public 
        override 
        nonReentrant 
        returns (uint256 shares) 
    {
        require(vaultActive, "Vault is not active");
        require(assets > 0, "Cannot deposit 0");
        require(currentDepositLimit + assets <= maxDepositLimit, "Exceeds deposit limit");
        
        shares = previewDeposit(assets);
        require(shares > 0, "Invalid shares");
        
        _mint(receiver, shares);
        currentDepositLimit += assets;
        
        emit Deposit(msg.sender, receiver, assets, shares);
    }
    
    // Withdraw ETH from the vault
    function withdraw(uint256 assets, address receiver, address owner) 
        public 
        override 
        nonReentrant 
        returns (uint256 shares) 
    {
        require(vaultActive, "Vault is not active");
        require(assets > 0, "Cannot withdraw 0");
        
        shares = previewWithdraw(assets);
        require(shares > 0, "Invalid shares");
        
        if (msg.sender != owner) {
            uint256 allowed = allowance(owner, msg.sender);
            if (allowed != type(uint256).max) {
                _spendAllowance(owner, msg.sender, shares);
            }
        }
        
        _burn(owner, shares);
        currentDepositLimit -= assets;
        
        (bool success, ) = receiver.call{value: assets}("");
        require(success, "ETH transfer failed");
        
        emit Withdraw(msg.sender, receiver, owner, assets, shares);
    }
    
    // Redeem shares for ETH
    function redeem(uint256 shares, address receiver, address owner) 
        public 
        override 
        nonReentrant 
        returns (uint256 assets) 
    {
        require(vaultActive, "Vault is not active");
        require(shares > 0, "Cannot redeem 0 shares");
        
        assets = previewRedeem(shares);
        require(assets > 0, "Invalid assets");
        
        if (msg.sender != owner) {
            uint256 allowed = allowance(owner, msg.sender);
            if (allowed != type(uint256).max) {
                _spendAllowance(owner, msg.sender, shares);
            }
        }
        
        _burn(owner, shares);
        currentDepositLimit -= assets;
        
        (bool success, ) = receiver.call{value: assets}("");
        require(success, "ETH transfer failed");
        
        emit Withdraw(msg.sender, receiver, owner, assets, shares);
    }
    
    // Preview functions for ERC4626 compliance
    function totalAssets() public view override returns (uint256) {
        return address(this).balance;
    }
    
    function convertToShares(uint256 assets) public view override returns (uint256) {
        uint256 supply = totalSupply();
        uint256 price = _oraclePrice();
        uint256 adjustedAssets = (assets * price) / ONE;
        if (supply == 0) {
            return adjustedAssets;
        }
        return adjustedAssets.mulDiv(supply, totalAssets(), Math.Rounding.Down);
    }
    
    function convertToAssets(uint256 shares) public view override returns (uint256) {
        uint256 supply = totalSupply();
        uint256 price = _oraclePrice();
        if (supply == 0) {
            // convert shares to assets at price 1
            return (shares * ONE) / price;
        }
        uint256 baseAssets = shares.mulDiv(totalAssets(), supply, Math.Rounding.Down);
        return (baseAssets * ONE) / price;
    }
    
    function previewDeposit(uint256 assets) public view override returns (uint256) {
        return convertToShares(assets);
    }
    
    function previewMint(uint256 shares) public view override returns (uint256) {
        uint256 supply = totalSupply();
        if (supply == 0) {
            return shares;
        }
        return shares.mulDiv(totalAssets(), supply, Math.Rounding.Up);
    }
    
    function previewWithdraw(uint256 assets) public view override returns (uint256) {
        uint256 supply = totalSupply();
        if (supply == 0) {
            return 0;
        }
        return assets.mulDiv(supply, totalAssets(), Math.Rounding.Up);
    }
    
    function previewRedeem(uint256 shares) public view override returns (uint256) {
        return convertToAssets(shares);
    }
    
    // Owner functions
    function setVaultActive(bool _active) external onlyOwner {
        vaultActive = _active;
        if (_active) {
            emit VaultActivated(nftContract);
        } else {
            emit VaultDeactivated(nftContract);
        }
    }
    
    function setMaxDepositLimit(uint256 _limit) external onlyOwner {
        require(_limit >= currentDepositLimit, "Limit too low");
        uint256 oldLimit = maxDepositLimit;
        maxDepositLimit = _limit;
        emit DepositLimitUpdated(oldLimit, _limit);
    }
    
    function emergencyWithdraw() external onlyOwner {
        require(!vaultActive, "Vault is still active");
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        
        (bool success, ) = owner().call{value: balance}("");
        require(success, "ETH transfer failed");
        
        emit EmergencyWithdraw(owner(), balance);
    }
    
    // View functions
    function getVaultInfo() external view returns (
        address _nftContract,
        string memory _vaultName,
        string memory _vaultSymbol,
        bool _vaultActive,
        uint256 _maxDepositLimit,
        uint256 _currentDepositLimit,
        uint256 _totalAssets,
        uint256 _totalShares
    ) {
        return (
            nftContract,
            vaultName,
            vaultSymbol,
            vaultActive,
            maxDepositLimit,
            currentDepositLimit,
            totalAssets(),
            totalSupply()
        );
    }
    
    // Required overrides for ERC4626
    function maxDeposit(address) public view override returns (uint256) {
        return vaultActive ? maxDepositLimit - currentDepositLimit : 0;
    }
    
    function maxMint(address) public view override returns (uint256) {
        return convertToShares(maxDeposit(address(0)));
    }
    
    function maxWithdraw(address owner) public view override returns (uint256) {
        return convertToAssets(balanceOf(owner));
    }
    
    function maxRedeem(address owner) public view override returns (uint256) {
        return balanceOf(owner);
    }
    
    // Receive ETH
    receive() external payable {
        // Allow receiving ETH (for deposits)
    }
} 