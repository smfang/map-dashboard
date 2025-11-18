#!/usr/bin/env python3
"""
SP1 Proof Verification Script

This script verifies zk proofs on-chain using the SP1Verifier contract.
It reads proof data and submits it to the blockchain for verification.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from web3 import Web3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SP1ProofVerifier:
    def __init__(self, rpc_url: str = None, private_key: str = None):
        """
        Initialize the proof verifier.
        
        Args:
            rpc_url: Ethereum RPC URL
            private_key: Private key for signing transactions
        """
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://localhost:8545")
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        
        if not self.private_key:
            raise ValueError("Private key is required for verification")
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node")
        
        # Load contract ABI and address
        self.contract_abi = self._load_contract_abi()
        self.contract_address = os.getenv("SP1_VERIFIER_ADDRESS")
        
        if not self.contract_address:
            raise ValueError("SP1_VERIFIER_ADDRESS environment variable is required")
        
        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
        
        # Get account
        self.account = self.w3.eth.account.from_key(self.private_key)
        print(f"Connected to {self.rpc_url}")
        print(f"Account: {self.account.address}")
        print(f"Contract: {self.contract_address}")
    
    def _load_contract_abi(self) -> list:
        """Load the SP1Verifier contract ABI."""
        # This would typically be loaded from a compiled contract file
        # For now, we'll define the essential ABI methods
        return [
            {
                "inputs": [
                    {"internalType": "bytes", "name": "proof", "type": "bytes"},
                    {
                        "components": [
                            {"internalType": "uint256", "name": "nhiScore", "type": "uint256"},
                            {"internalType": "uint256", "name": "p20Percentile", "type": "uint256"},
                            {"internalType": "uint256", "name": "p90Percentile", "type": "uint256"},
                            {"internalType": "uint256", "name": "gammaShape", "type": "uint256"},
                            {"internalType": "uint256", "name": "gammaScale", "type": "uint256"},
                            {"internalType": "uint256", "name": "gammaLoc", "type": "uint256"},
                            {"internalType": "uint256", "name": "carbonIndexValue", "type": "uint256"},
                            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                            {"internalType": "uint256", "name": "latMin", "type": "uint256"},
                            {"internalType": "uint256", "name": "latMax", "type": "uint256"},
                            {"internalType": "uint256", "name": "lonMin", "type": "uint256"},
                            {"internalType": "uint256", "name": "lonMax", "type": "uint256"}
                        ],
                        "internalType": "struct SP1Verifier.CarbonIndexProof",
                        "name": "publicValues",
                        "type": "tuple"
                    },
                    {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"}
                ],
                "name": "verifyProof",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "proofHash", "type": "bytes32"}],
                "name": "isProofVerified",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "proofHash", "type": "bytes32"}],
                "name": "getCarbonIndexValue",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "bytes32", "name": "proofHash", "type": "bytes32"},
                    {"indexed": False, "internalType": "uint256", "name": "carbonIndexValue", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"indexed": True, "internalType": "address", "name": "verifier", "type": "address"}
                ],
                "name": "ProofVerified",
                "type": "event"
            }
        ]
    
    def verify_proof_from_file(self, proof_file: str) -> Dict[str, Any]:
        """
        Verify a proof from a JSON file.
        
        Args:
            proof_file: Path to the proof JSON file
            
        Returns:
            Dictionary containing verification results
        """
        proof_path = Path(proof_file)
        if not proof_path.exists():
            raise FileNotFoundError(f"Proof file not found: {proof_file}")
        
        with open(proof_path, 'r') as f:
            proof_data = json.load(f)
        
        return self.verify_proof(proof_data)
    
    def verify_proof(self, proof_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a proof on-chain.
        
        Args:
            proof_data: Dictionary containing proof data
            
        Returns:
            Dictionary containing verification results
        """
        try:
            # Extract proof and public values
            proof_bytes = self._extract_proof_bytes(proof_data)
            public_values = self._extract_public_values(proof_data)
            proof_hash = self._calculate_proof_hash(proof_data)
            
            # Check if proof is already verified
            is_verified = self.contract.functions.isProofVerified(proof_hash).call()
            if is_verified:
                print(f"Proof {proof_hash.hex()} is already verified")
                return {
                    "success": True,
                    "proof_hash": proof_hash.hex(),
                    "already_verified": True,
                    "carbon_index_value": self.contract.functions.getCarbonIndexValue(proof_hash).call()
                }
            
            # Step 1: Submit proof to SP1Verifier (which forwards to ZKVerify)
            print(f"Submitting proof to SP1Verifier...")
            transaction = self.contract.functions.verifyProof(
                proof_bytes,
                public_values,
                proof_hash
            ).build_transaction({
                'from': self.account.address,
                'gas': 2000000,  # Adjust based on gas requirements
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            print(f"Proof submission transaction: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                return {
                    "success": False,
                    "proof_hash": proof_hash.hex(),
                    "transaction_hash": tx_hash.hex(),
                    "error": "Proof submission failed"
                }
            
            print(f"Proof submitted successfully! Waiting for ZKVerify verification...")
            
            # Step 2: Wait for ZKVerify verification and finalize
            finalize_result = self._wait_for_zkverify_verification(proof_hash)
            
            if finalize_result["success"]:
                # Get the carbon index value
                carbon_index_value = self.contract.functions.getCarbonIndexValue(proof_hash).call()
                
                return {
                    "success": True,
                    "proof_hash": proof_hash.hex(),
                    "submission_tx": tx_hash.hex(),
                    "finalize_tx": finalize_result.get("transaction_hash"),
                    "carbon_index_value": carbon_index_value,
                    "gas_used": receipt.gasUsed + finalize_result.get("gas_used", 0)
                }
            else:
                return {
                    "success": False,
                    "proof_hash": proof_hash.hex(),
                    "submission_tx": tx_hash.hex(),
                    "error": finalize_result.get("error", "ZKVerify verification failed")
                }
                
        except Exception as e:
            print(f"Verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _wait_for_zkverify_verification(self, proof_hash: bytes, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        Wait for ZKVerify to verify the proof and then finalize it.
        
        Args:
            proof_hash: The proof hash
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Dictionary containing finalization results
        """
        import time
        
        print(f"Waiting for ZKVerify verification (max {max_wait_time}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check if proof is submitted
                is_submitted = self.contract.functions.isProofSubmitted(proof_hash).call()
                if not is_submitted:
                    time.sleep(5)
                    continue
                
                # Get ZKVerify proof ID
                zkverify_proof_id = self.contract.functions.getZKVerifyProofId(proof_hash).call()
                if zkverify_proof_id == bytes32(0):
                    time.sleep(5)
                    continue
                
                # Try to finalize the proof
                print(f"Attempting to finalize proof...")
                transaction = self.contract.functions.finalizeProof(proof_hash).build_transaction({
                    'from': self.account.address,
                    'gas': 500000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address)
                })
                
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                
                print(f"Finalization transaction: {tx_hash.hex()}")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt.status == 1:
                    print(f"Proof finalized successfully!")
                    return {
                        "success": True,
                        "transaction_hash": tx_hash.hex(),
                        "gas_used": receipt.gasUsed
                    }
                else:
                    return {
                        "success": False,
                        "error": "Finalization transaction failed"
                    }
                    
            except Exception as e:
                if "Proof verification failed" in str(e) or "ZKVerify verification failed" in str(e):
                    return {
                        "success": False,
                        "error": f"ZKVerify verification failed: {str(e)}"
                    }
                # For other errors, continue waiting
                print(f"Waiting for verification... ({str(e)})")
                time.sleep(10)
        
        return {
            "success": False,
            "error": f"Timeout waiting for ZKVerify verification after {max_wait_time}s"
        }
    
    def _extract_proof_bytes(self, proof_data: Dict[str, Any]) -> bytes:
        """Extract proof bytes from proof data."""
        # Try to get ZKVerify formatted proof first
        zkverify_proof = proof_data.get("zkverify_proof", {})
        if zkverify_proof and "proof_bytes" in zkverify_proof:
            proof_hex = zkverify_proof["proof_bytes"]
            if proof_hex.startswith("0x"):
                proof_hex = proof_hex[2:]
            return bytes.fromhex(proof_hex)
        
        # Fallback to original proof data
        proof_string = json.dumps(proof_data.get("proof", {}), sort_keys=True)
        return proof_string.encode()
    
    def _extract_public_values(self, proof_data: Dict[str, Any]) -> tuple:
        """Extract public values from proof data."""
        public_values = proof_data.get("public_values", {})
        
        # Convert to wei (1e18) scaled values
        def to_wei(value: float) -> int:
            return int(value * 1e18)
        
        return (
            to_wei(public_values.get("nhi_score", 0.0)),
            to_wei(public_values.get("p20_percentile", 0.0)),
            to_wei(public_values.get("p90_percentile", 0.0)),
            to_wei(public_values.get("gamma_shape", 0.0)),
            to_wei(public_values.get("gamma_scale", 0.0)),
            to_wei(public_values.get("gamma_loc", 0.0)),
            int(public_values.get("carbon_index_value", 0)),
            int(public_values.get("timestamp", 0)),
            to_wei(public_values.get("lat_min", 0.0)),
            to_wei(public_values.get("lat_max", 0.0)),
            to_wei(public_values.get("lon_min", 0.0)),
            to_wei(public_values.get("lon_max", 0.0))
        )
    
    def _calculate_proof_hash(self, proof_data: Dict[str, Any]) -> bytes:
        """Calculate hash of the proof for identification."""
        import hashlib
        proof_string = json.dumps(proof_data, sort_keys=True)
        return hashlib.sha256(proof_string.encode()).digest()
    
    def check_proof_status(self, proof_hash: str) -> Dict[str, Any]:
        """Check the status of a proof."""
        try:
            proof_hash_bytes = bytes.fromhex(proof_hash.replace('0x', ''))
            is_verified = self.contract.functions.isProofVerified(proof_hash_bytes).call()
            
            if is_verified:
                carbon_index_value = self.contract.functions.getCarbonIndexValue(proof_hash_bytes).call()
                return {
                    "verified": True,
                    "carbon_index_value": carbon_index_value
                }
            else:
                return {
                    "verified": False
                }
        except Exception as e:
            return {
                "error": str(e)
            }

def main():
    """Main function to demonstrate proof verification."""
    if len(sys.argv) < 2:
        print("Usage: python verify_proof.py <proof_file.json>")
        sys.exit(1)
    
    proof_file = sys.argv[1]
    
    try:
        verifier = SP1ProofVerifier()
        result = verifier.verify_proof_from_file(proof_file)
        
        if result["success"]:
            print(f"\n✅ Proof verification successful!")
            print(f"Proof Hash: {result['proof_hash']}")
            print(f"Carbon Index Value: {result['carbon_index_value']}")
            if "gas_used" in result:
                print(f"Gas Used: {result['gas_used']}")
        else:
            print(f"\n❌ Proof verification failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

