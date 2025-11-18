// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./SP1Verifier.sol";

/**
 * @title CarbonIndex
 * @dev Enhanced carbon index contract that uses SP1 zk proofs for verification
 * This contract stores carbon index values that are verified through zk proofs
 * proving the correctness of the underlying calculations.
 */
contract CarbonIndex is Ownable, ReentrancyGuard {
    
    // The SP1 verifier contract
    SP1Verifier public immutable sp1Verifier;
    
    // Current index value (1e18-scaled)
    uint256 private _indexValue;
    
    // Mapping to store verified proof hashes and their associated index values
    mapping(bytes32 => uint256) public verifiedIndexValues;
    
    // Mapping to store proof metadata
    mapping(bytes32 => ProofMetadata) public proofMetadata;
    
    // Struct to store proof metadata
    struct ProofMetadata {
        uint256 timestamp;
        uint256 latMin;
        uint256 latMax;
        uint256 lonMin;
        uint256 lonMax;
        address verifier;
        bool isActive;
    }
    
    // Events
    event IndexUpdated(uint256 oldValue, uint256 newValue);
    event IndexUpdatedWithProof(
        bytes32 indexed proofHash,
        uint256 oldValue,
        uint256 newValue,
        address indexed verifier
    );
    event ProofAccepted(bytes32 indexed proofHash, uint256 indexValue);
    event ProofRejected(bytes32 indexed proofHash, string reason);

    constructor(uint256 initialValue, address _sp1Verifier) {
        _indexValue = initialValue; // expected 1e18 scaled
        sp1Verifier = SP1Verifier(_sp1Verifier);
    }

    /**
     * @dev Get the current carbon index value
     * @return The current index value (1e18 scaled)
     */
    function getIndex() external view returns (uint256) {
        return _indexValue;
    }

    /**
     * @dev Set the index value (only owner, for emergency updates)
     * @param newValue The new index value (1e18 scaled)
     */
    function setIndex(uint256 newValue) external onlyOwner {
        uint256 old = _indexValue;
        _indexValue = newValue;
        emit IndexUpdated(old, newValue);
    }

    /**
     * @dev Update the index value using a verified SP1 proof
     * @param proofHash The hash of the verified proof
     */
    function updateIndexWithProof(bytes32 proofHash) external nonReentrant {
        // Verify that the proof exists in the SP1 verifier
        require(sp1Verifier.isProofVerified(proofHash), "Proof not verified");
        
        // Get the carbon index value from the proof
        uint256 newIndexValue = sp1Verifier.getCarbonIndexValue(proofHash);
        
        // Get proof data for metadata
        SP1Verifier.CarbonIndexProof memory proofData = sp1Verifier.getProofData(proofHash);
        
        // Store the verified index value
        verifiedIndexValues[proofHash] = newIndexValue;
        
        // Store proof metadata
        proofMetadata[proofHash] = ProofMetadata({
            timestamp: proofData.timestamp,
            latMin: proofData.latMin,
            latMax: proofData.latMax,
            lonMin: proofData.lonMin,
            lonMax: proofData.lonMax,
            verifier: msg.sender,
            isActive: true
        });
        
        // Update the current index value
        uint256 oldValue = _indexValue;
        _indexValue = newIndexValue;
        
        emit IndexUpdatedWithProof(proofHash, oldValue, newIndexValue, msg.sender);
        emit ProofAccepted(proofHash, newIndexValue);
    }

    /**
     * @dev Get the index value associated with a specific proof
     * @param proofHash The hash of the proof
     * @return The index value from that proof
     */
    function getIndexFromProof(bytes32 proofHash) external view returns (uint256) {
        require(verifiedIndexValues[proofHash] > 0, "Proof not found");
        return verifiedIndexValues[proofHash];
    }

    /**
     * @dev Get proof metadata
     * @param proofHash The hash of the proof
     * @return The proof metadata
     */
    function getProofMetadata(bytes32 proofHash) external view returns (ProofMetadata memory) {
        require(proofMetadata[proofHash].timestamp > 0, "Proof metadata not found");
        return proofMetadata[proofHash];
    }

    /**
     * @dev Check if a proof has been used to update the index
     * @param proofHash The hash of the proof
     * @return Whether the proof has been used
     */
    function isProofUsed(bytes32 proofHash) external view returns (bool) {
        return verifiedIndexValues[proofHash] > 0;
    }

    /**
     * @dev Deactivate a proof (only owner, for emergency situations)
     * @param proofHash The hash of the proof to deactivate
     */
    function deactivateProof(bytes32 proofHash) external onlyOwner {
        require(proofMetadata[proofHash].timestamp > 0, "Proof not found");
        proofMetadata[proofHash].isActive = false;
    }

    /**
     * @dev Get the latest verified proof hash and its value
     * @return proofHash The hash of the latest proof
     * @return indexValue The index value from the latest proof
     */
    function getLatestVerifiedProof() external view returns (bytes32 proofHash, uint256 indexValue) {
        // This is a simplified implementation
        // In practice, you might want to maintain a list of proof hashes
        // or use events to track the latest proof
        
        // For now, we'll return the current index value
        // A more sophisticated implementation would track proof history
        return (bytes32(0), _indexValue);
    }

    /**
     * @dev Verify and update index in one transaction
     * This function combines proof verification and index update
     * @param proof The SP1 proof bytes
     * @param publicValues The public values from the proof
     * @param proofHash The hash of the proof
     */
    function verifyAndUpdateIndex(
        bytes calldata proof,
        SP1Verifier.CarbonIndexProof calldata publicValues,
        bytes32 proofHash
    ) external nonReentrant {
        // First verify the proof
        try sp1Verifier.verifyProof(proof, publicValues, proofHash) {
            // If verification succeeds, update the index
            this.updateIndexWithProof(proofHash);
        } catch Error(string memory reason) {
            emit ProofRejected(proofHash, reason);
            revert(reason);
        } catch {
            emit ProofRejected(proofHash, "Unknown verification error");
            revert("Proof verification failed");
        }
    }
}


