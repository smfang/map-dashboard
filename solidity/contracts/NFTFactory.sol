// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./ProjectNFT.sol";
import "./NFTVault.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract NFTFactory is Ownable {
    // Array to store all deployed NFT contracts
    address[] public deployedNFTs;
    
    // Mapping from NFT address to creator
    mapping(address => address) public nftCreators;
    
    // Mapping from NFT address to associated vault
    mapping(address => address) public nftVaults;
    
    // Factory fee for creating new collections
    uint256 public factoryFee;
    
    // Events
    event NFTCollectionCreated(
        address indexed nftAddress,
        address indexed vaultAddress,
        address indexed creator,
        string name,
        string symbol,
        uint256 maxSupply,
        uint256 mintPrice
    );
    
    event FactoryFeeUpdated(uint256 newFee);
    
    constructor(uint256 _factoryFee) {
        factoryFee = _factoryFee;
    }
    
    // Create a new NFT collection with associated vault
    function createNFTCollection(
        string memory name,
        string memory symbol,
        uint256 maxSupply,
        uint256 mintPrice,
        string memory baseURI
    ) public payable returns (address, address) {
        require(msg.value >= factoryFee, "Insufficient factory fee");
        
        // Deploy new NFT contract
        ProjectNFT newNFT = new ProjectNFT(
            name,
            symbol,
            maxSupply,
            mintPrice,
            baseURI
        );
        
        // Create vault name and symbol
        string memory vaultName = string(abi.encodePacked(name, " Vault"));
        string memory vaultSymbol = string(abi.encodePacked(symbol, "V"));
        
        // Deploy associated vault contract
        NFTVault newVault = new NFTVault(
            address(newNFT),
            vaultName,
            vaultSymbol,
            msg.sender
        );
        
        // Transfer NFT ownership to the creator
        newNFT.transferOwnership(msg.sender);
        
        // Store the deployed contracts
        deployedNFTs.push(address(newNFT));
        nftCreators[address(newNFT)] = msg.sender;
        nftVaults[address(newNFT)] = address(newVault);
        
        emit NFTCollectionCreated(
            address(newNFT),
            address(newVault),
            msg.sender,
            name,
            symbol,
            maxSupply,
            mintPrice
        );
        
        return (address(newNFT), address(newVault));
    }
    
    // Get all deployed NFT contracts
    function getDeployedNFTs() public view returns (address[] memory) {
        return deployedNFTs;
    }
    
    // Get NFT creator
    function getNFTCreator(address nftAddress) public view returns (address) {
        return nftCreators[nftAddress];
    }
    
    // Get vault associated with NFT
    function getNFTVault(address nftAddress) public view returns (address) {
        return nftVaults[nftAddress];
    }
    
    // Get total number of deployed collections
    function getTotalCollections() public view returns (uint256) {
        return deployedNFTs.length;
    }
    
    // Get collection info including vault
    function getCollectionInfo(address nftAddress) public view returns (
        address creator,
        address vault,
        bool hasVault
    ) {
        creator = nftCreators[nftAddress];
        vault = nftVaults[nftAddress];
        hasVault = vault != address(0);
    }
    
    // Update factory fee (owner only)
    function setFactoryFee(uint256 _factoryFee) public onlyOwner {
        factoryFee = _factoryFee;
        emit FactoryFeeUpdated(_factoryFee);
    }
    
    // Withdraw factory fees (owner only)
    function withdrawFees() public onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        
        payable(owner()).transfer(balance);
    }
    
    // Check if an address is a deployed NFT
    function isDeployedNFT(address nftAddress) public view returns (bool) {
        for (uint256 i = 0; i < deployedNFTs.length; i++) {
            if (deployedNFTs[i] == nftAddress) {
                return true;
            }
        }
        return false;
    }
    
    // Check if an address is a deployed vault
    function isDeployedVault(address vaultAddress) public view returns (bool) {
        for (uint256 i = 0; i < deployedNFTs.length; i++) {
            if (nftVaults[deployedNFTs[i]] == vaultAddress) {
                return true;
            }
        }
        return false;
    }
} 