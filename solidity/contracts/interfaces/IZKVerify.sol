// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IZKVerify
 * @dev Interface for ZKVerify proof verification contract
 *      Based on Horizen's ZKVerify network for proof verification
 */
interface IZKVerify {
    
    // Events
    event ProofSubmitted(bytes32 indexed proofId, address indexed submitter);
    event ProofVerified(bytes32 indexed proofId, bool verified);
    
    // Structs
    struct ProofStatus {
        bool submitted;
        bool verified;
        uint256 submissionTime;
        uint256 verificationTime;
        string errorMessage;
    }
    
    /**
     * @dev Submit a proof for verification
     * @param proof The proof bytes
     * @param publicInputs The public inputs as bytes
     * @return proofId The unique identifier for this proof submission
     */
    function submitProof(
        bytes calldata proof,
        bytes calldata publicInputs
    ) external returns (bytes32 proofId);
    
    /**
     * @dev Check if a proof has been verified
     * @param proofId The proof identifier
     * @return verified Whether the proof is verified
     */
    function verifyProof(bytes32 proofId) external view returns (bool verified);
    
    /**
     * @dev Get detailed status of a proof
     * @param proofId The proof identifier
     * @return status The proof status struct
     */
    function getProofStatus(bytes32 proofId) external view returns (ProofStatus memory status);
    
    /**
     * @dev Get the verification fee for submitting a proof
     * @return fee The fee in wei
     */
    function getVerificationFee() external view returns (uint256 fee);
    
    /**
     * @dev Check if the contract is accepting new proof submissions
     * @return accepting Whether new submissions are accepted
     */
    function isAcceptingSubmissions() external view returns (bool accepting);
}
