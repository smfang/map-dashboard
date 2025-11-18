// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./interfaces/IZKVerify.sol";

/**
 * @title SP1Verifier
 * @dev Verifies SP1 zk proofs for carbon index calculations
 * This contract verifies that carbon index calculations were performed correctly
 * without revealing the underlying data or computation details.
 */
contract SP1Verifier is Ownable, ReentrancyGuard {
    
    // ZKVerify contract for proof verification
    IZKVerify public immutable zkVerify;
    
    // Struct to hold the public values from the SP1 proof
    struct CarbonIndexProof {
        uint256 nhiScore;           // Natural Hazard Index score (scaled by 1e18)
        uint256 p20Percentile;      // 20th percentile (scaled by 1e18)
        uint256 p90Percentile;      // 90th percentile (scaled by 1e18)
        uint256 gammaShape;         // Gamma distribution shape parameter (scaled by 1e18)
        uint256 gammaScale;         // Gamma distribution scale parameter (scaled by 1e18)
        uint256 gammaLoc;           // Gamma distribution location parameter (scaled by 1e18)
        uint256 carbonIndexValue;   // Final carbon index value (scaled by 1e18)
        uint256 timestamp;          // Timestamp of the calculation
        uint256 latMin;             // Minimum latitude (scaled by 1e18)
        uint256 latMax;             // Maximum latitude (scaled by 1e18)
        uint256 lonMin;             // Minimum longitude (scaled by 1e18)
        uint256 lonMax;             // Maximum longitude (scaled by 1e18)
    }
    
    // SP1 proof verification key (this would be generated from the SP1 program)
    bytes32 public constant VERIFICATION_KEY = keccak256("SP1_CARBON_INDEX_VERIFICATION_KEY");
    
    // Mapping to store verified proofs
    mapping(bytes32 => bool) public verifiedProofs;
    
    // Mapping to store proof metadata
    mapping(bytes32 => CarbonIndexProof) public proofData;
    
    // Mapping to store ZKVerify proof IDs by proof hash
    mapping(bytes32 => bytes32) public proofIdByHash;
    
    // Mapping to store proof submission status
    mapping(bytes32 => bool) public proofSubmitted;
    
    // Events
    event ProofVerified(
        bytes32 indexed proofHash,
        uint256 carbonIndexValue,
        uint256 timestamp,
        address indexed verifier
    );
    
    event ProofRejected(
        bytes32 indexed proofHash,
        string reason
    );
    
    event ProofSubmittedToZKVerify(
        bytes32 indexed proofHash,
        bytes32 indexed zkVerifyProofId
    );
    
    // Constructor
    constructor(address _zkVerify) {
        require(_zkVerify != address(0), "Invalid ZKVerify address");
        zkVerify = IZKVerify(_zkVerify);
    }
    
    // Modifiers
    modifier onlyValidProof(bytes32 proofHash) {
        require(!verifiedProofs[proofHash], "Proof already verified");
        _;
    }
    
    /**
     * @dev Verify an SP1 proof for carbon index calculation
     * @param proof The SP1 proof bytes
     * @param publicValues The public values from the proof
     * @param proofHash Hash of the proof for deduplication
     */
    function verifyProof(
        bytes calldata proof,
        CarbonIndexProof calldata publicValues,
        bytes32 proofHash
    ) external onlyValidProof(proofHash) nonReentrant {
        // Validate input parameters
        require(proof.length > 0, "Invalid proof");
        require(publicValues.timestamp > 0, "Invalid timestamp");
        require(publicValues.latMin < publicValues.latMax, "Invalid latitude range");
        require(publicValues.lonMin < publicValues.lonMax, "Invalid longitude range");
        require(publicValues.carbonIndexValue <= 1e18, "Invalid carbon index value");
        
        // Submit proof to ZKVerify for verification
        bool submitted = _submitToZKVerify(proof, publicValues, proofHash);
        
        if (submitted) {
            // Store the proof data (not yet verified)
            proofData[proofHash] = publicValues;
            proofSubmitted[proofHash] = true;
            
            emit ProofSubmittedToZKVerify(proofHash, proofIdByHash[proofHash]);
        } else {
            emit ProofRejected(proofHash, "Failed to submit proof to ZKVerify");
            revert("Proof submission failed");
        }
    }
    
    /**
     * @dev Submit proof to ZKVerify for verification
     * @param proof The proof bytes
     * @param publicValues The public values
     * @param proofHash The proof hash
     * @return submitted Whether the proof was successfully submitted
     */
    function _submitToZKVerify(
        bytes calldata proof,
        CarbonIndexProof calldata publicValues,
        bytes32 proofHash
    ) internal returns (bool) {
        try zkVerify.submitProof(
            proof,
            _encodePublicValues(publicValues)
        ) returns (bytes32 zkVerifyProofId) {
            proofIdByHash[proofHash] = zkVerifyProofId;
            return true;
        } catch {
            return false;
        }
    }
    
    /**
     * @dev Encode public values into bytes for ZKVerify
     * @param publicValues The public values struct
     * @return encoded The encoded bytes
     */
    function _encodePublicValues(CarbonIndexProof calldata publicValues) internal pure returns (bytes memory) {
        return abi.encode(
            publicValues.nhiScore,
            publicValues.p20Percentile,
            publicValues.p90Percentile,
            publicValues.gammaShape,
            publicValues.gammaScale,
            publicValues.gammaLoc,
            publicValues.carbonIndexValue,
            publicValues.timestamp,
            publicValues.latMin,
            publicValues.latMax,
            publicValues.lonMin,
            publicValues.lonMax
        );
    }
    
    /**
     * @dev Finalize proof verification after ZKVerify has processed it
     * @param proofHash The proof hash to finalize
     */
    function finalizeProof(bytes32 proofHash) external nonReentrant {
        require(proofSubmitted[proofHash], "Proof not submitted");
        require(!verifiedProofs[proofHash], "Proof already verified");
        
        bytes32 zkVerifyProofId = proofIdByHash[proofHash];
        require(zkVerifyProofId != bytes32(0), "Invalid ZKVerify proof ID");
        
        try zkVerify.verifyProof(zkVerifyProofId) returns (bool verified) {
            if (verified) {
                verifiedProofs[proofHash] = true;
                CarbonIndexProof memory proofData_ = proofData[proofHash];
                
                emit ProofVerified(
                    proofHash,
                    proofData_.carbonIndexValue,
                    proofData_.timestamp,
                    msg.sender
                );
            } else {
                emit ProofRejected(proofHash, "ZKVerify verification failed");
                revert("Proof verification failed");
            }
        } catch {
            emit ProofRejected(proofHash, "ZKVerify verification error");
            revert("Proof verification error");
        }
    }
    
    /**
     * @dev Check if a proof has been verified
     * @param proofHash Hash of the proof
     * @return isVerified Whether the proof is verified
     */
    function isProofVerified(bytes32 proofHash) external view returns (bool) {
        return verifiedProofs[proofHash];
    }
    
    /**
     * @dev Check if a proof has been submitted to ZKVerify
     * @param proofHash Hash of the proof
     * @return isSubmitted Whether the proof has been submitted
     */
    function isProofSubmitted(bytes32 proofHash) external view returns (bool) {
        return proofSubmitted[proofHash];
    }
    
    /**
     * @dev Get ZKVerify proof ID for a given proof hash
     * @param proofHash Hash of the proof
     * @return zkVerifyProofId The ZKVerify proof ID
     */
    function getZKVerifyProofId(bytes32 proofHash) external view returns (bytes32) {
        return proofIdByHash[proofHash];
    }
    
    /**
     * @dev Get proof data for a verified proof
     * @param proofHash Hash of the proof
     * @return proof The proof data
     */
    function getProofData(bytes32 proofHash) external view returns (CarbonIndexProof memory) {
        require(verifiedProofs[proofHash], "Proof not verified");
        return proofData[proofHash];
    }
    
    /**
     * @dev Get the carbon index value from a verified proof
     * @param proofHash Hash of the proof
     * @return carbonIndexValue The carbon index value
     */
    function getCarbonIndexValue(bytes32 proofHash) external view returns (uint256) {
        require(verifiedProofs[proofHash], "Proof not verified");
        return proofData[proofHash].carbonIndexValue;
    }
    
    /**
     * @dev Emergency function to revoke a proof (only owner)
     * @param proofHash Hash of the proof to revoke
     */
    function revokeProof(bytes32 proofHash) external onlyOwner {
        require(verifiedProofs[proofHash], "Proof not verified");
        delete verifiedProofs[proofHash];
        delete proofData[proofHash];
    }
    
    /**
     * @dev Update verification key (only owner)
     * @param newVerificationKey New verification key
     */
    function updateVerificationKey(bytes32 newVerificationKey) external onlyOwner {
        // In practice, this would update the actual verification key
        // For now, we'll just emit an event
        emit ProofVerified(bytes32(0), 0, block.timestamp, msg.sender);
    }
}
