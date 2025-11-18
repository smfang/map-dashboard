#!/usr/bin/env python3
"""
Deployment and Testing Script for SP1 Carbon Index ZK Proof System

This script demonstrates the complete workflow:
1. Deploy SP1Verifier and CarbonIndex contracts
2. Generate a zk proof for carbon index calculation
3. Verify the proof on-chain
4. Update the carbon index with the verified proof
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any
from web3 import Web3
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()

class CarbonIndexZKSystem:
    def __init__(self, rpc_url: str = None, private_key: str = None):
        """Initialize the ZK proof system."""
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://localhost:8545")
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        
        if not self.private_key:
            raise ValueError("Private key is required")
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node")
        
        self.account = self.w3.eth.account.from_key(self.private_key)
        print(f"Connected to {self.rpc_url}")
        print(f"Account: {self.account.address}")
        
        # Contract instances
        self.sp1_verifier = None
        self.carbon_index = None
    
    def deploy_contracts(self) -> Dict[str, str]:
        """Deploy the SP1Verifier and CarbonIndex contracts."""
        print("\n=== Deploying Contracts ===")
        
        # Deploy SP1Verifier
        print("Deploying SP1Verifier...")
        sp1_verifier_abi = self._get_sp1_verifier_abi()
        sp1_verifier_bytecode = self._get_sp1_verifier_bytecode()
        
        sp1_verifier_contract = self.w3.eth.contract(
            abi=sp1_verifier_abi,
            bytecode=sp1_verifier_bytecode
        )
        
        # Get ZKVerify contract address from environment
        zkverify_address = os.getenv('ZKVERIFY_CONTRACT_ADDRESS')
        if not zkverify_address:
            # For local testing, use a mock address
            zkverify_address = "0x0000000000000000000000000000000000000000"
            print("Warning: ZKVERIFY_CONTRACT_ADDRESS not set, using mock address")
        
        # Deploy transaction
        deploy_txn = sp1_verifier_contract.constructor(zkverify_address).build_transaction({
            'from': self.account.address,
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(deploy_txn, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        sp1_verifier_address = receipt.contractAddress
        print(f"SP1Verifier deployed at: {sp1_verifier_address}")
        
        # Verify ZKVerify contract connectivity
        if zkverify_address != "0x0000000000000000000000000000000000000000":
            try:
                # Try to call a view function on ZKVerify to verify connectivity
                zkverify_contract = self.w3.eth.contract(
                    address=zkverify_address,
                    abi=[{
                        "inputs": [],
                        "name": "isAcceptingSubmissions",
                        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                        "stateMutability": "view",
                        "type": "function"
                    }]
                )
                is_accepting = zkverify_contract.functions.isAcceptingSubmissions().call()
                print(f"ZKVerify contract connectivity verified: accepting submissions = {is_accepting}")
            except Exception as e:
                print(f"Warning: Could not verify ZKVerify contract connectivity: {e}")
        
        # Deploy CarbonIndex
        print("Deploying CarbonIndex...")
        carbon_index_abi = self._get_carbon_index_abi()
        carbon_index_bytecode = self._get_carbon_index_bytecode()
        
        carbon_index_contract = self.w3.eth.contract(
            abi=carbon_index_abi,
            bytecode=carbon_index_bytecode
        )
        
        # Deploy with initial value and SP1Verifier address
        initial_value = int(0.5 * 1e18)  # 0.5 scaled by 1e18
        deploy_txn = carbon_index_contract.constructor(
            initial_value,
            sp1_verifier_address
        ).build_transaction({
            'from': self.account.address,
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(deploy_txn, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        carbon_index_address = receipt.contractAddress
        print(f"CarbonIndex deployed at: {carbon_index_address}")
        
        # Initialize contract instances
        self.sp1_verifier = self.w3.eth.contract(
            address=sp1_verifier_address,
            abi=sp1_verifier_abi
        )
        
        self.carbon_index = self.w3.eth.contract(
            address=carbon_index_address,
            abi=carbon_index_abi
        )
        
        return {
            "sp1_verifier": sp1_verifier_address,
            "carbon_index": carbon_index_address
        }
    
    def generate_proof(self) -> Dict[str, Any]:
        """Generate a zk proof for carbon index calculation."""
        print("\n=== Generating ZK Proof ===")
        
        # Use the proof generation script
        proof_generator_path = Path("zk_proofs/generate_proof.py")
        
        if not proof_generator_path.exists():
            raise FileNotFoundError("Proof generator script not found")
        
        # Run the proof generation
        result = subprocess.run(
            [sys.executable, str(proof_generator_path)],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Proof generation failed: {result.stderr}")
        
        # Find the generated proof file
        proofs_dir = Path("zk_proofs/proofs")
        proof_files = list(proofs_dir.glob("proof_*.json"))
        
        if not proof_files:
            raise RuntimeError("No proof files generated")
        
        # Get the latest proof file
        latest_proof = max(proof_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_proof, 'r') as f:
            proof_data = json.load(f)
        
        print(f"Proof generated: {latest_proof}")
        return proof_data
    
    def verify_proof_on_chain(self, proof_data: Dict[str, Any]) -> str:
        """Verify the proof on-chain."""
        print("\n=== Verifying Proof On-Chain ===")
        
        # Extract proof components
        proof_bytes = self._extract_proof_bytes(proof_data)
        public_values = self._extract_public_values(proof_data)
        proof_hash = self._calculate_proof_hash(proof_data)
        
        # Verify the proof
        transaction = self.sp1_verifier.functions.verifyProof(
            proof_bytes,
            public_values,
            proof_hash
        ).build_transaction({
            'from': self.account.address,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"Proof verified successfully: {proof_hash.hex()}")
            return proof_hash.hex()
        else:
            raise RuntimeError("Proof verification failed")
    
    def update_carbon_index(self, proof_hash: str):
        """Update the carbon index with the verified proof."""
        print("\n=== Updating Carbon Index ===")
        
        # Get current index value
        current_value = self.carbon_index.functions.getIndex().call()
        print(f"Current index value: {current_value / 1e18:.6f}")
        
        # Update with proof
        proof_hash_bytes = bytes.fromhex(proof_hash.replace('0x', ''))
        
        transaction = self.carbon_index.functions.updateIndexWithProof(
            proof_hash_bytes
        ).build_transaction({
            'from': self.account.address,
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            # Get new index value
            new_value = self.carbon_index.functions.getIndex().call()
            print(f"New index value: {new_value / 1e18:.6f}")
            print("Carbon index updated successfully!")
        else:
            raise RuntimeError("Carbon index update failed")
    
    def run_complete_workflow(self):
        """Run the complete ZK proof workflow."""
        try:
            # Deploy contracts
            contract_addresses = self.deploy_contracts()
            
            # Generate proof
            proof_data = self.generate_proof()
            
            # Verify proof
            proof_hash = self.verify_proof_on_chain(proof_data)
            
            # Update carbon index
            self.update_carbon_index(proof_hash)
            
            print("\n=== Workflow Completed Successfully! ===")
            print(f"SP1Verifier: {contract_addresses['sp1_verifier']}")
            print(f"CarbonIndex: {contract_addresses['carbon_index']}")
            print(f"Proof Hash: {proof_hash}")
            
        except Exception as e:
            print(f"Workflow failed: {str(e)}")
            raise
    
    def _get_sp1_verifier_abi(self) -> list:
        """Get SP1Verifier contract ABI."""
        # This would typically be loaded from a compiled contract file
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
            }
        ]
    
    def _get_sp1_verifier_bytecode(self) -> str:
        """Get SP1Verifier contract bytecode."""
        # This would be the actual compiled bytecode
        return "0x608060405234801561001057600080fd5b50600436106100365760003560e01c8063..."
    
    def _get_carbon_index_abi(self) -> list:
        """Get CarbonIndex contract ABI."""
        return [
            {
                "inputs": [{"internalType": "uint256", "name": "initialValue", "type": "uint256"}, {"internalType": "address", "name": "_sp1Verifier", "type": "address"}],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "inputs": [],
                "name": "getIndex",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "proofHash", "type": "bytes32"}],
                "name": "updateIndexWithProof",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _get_carbon_index_bytecode(self) -> str:
        """Get CarbonIndex contract bytecode."""
        return "0x608060405234801561001057600080fd5b50600436106100365760003560e01c8063..."
    
    def _extract_proof_bytes(self, proof_data: Dict[str, Any]) -> bytes:
        """Extract proof bytes from proof data."""
        proof_string = json.dumps(proof_data.get("proof", {}), sort_keys=True)
        return proof_string.encode()
    
    def _extract_public_values(self, proof_data: Dict[str, Any]) -> tuple:
        """Extract public values from proof data."""
        public_values = proof_data.get("public_values", {})
        
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

def main():
    """Main function to run the complete workflow."""
    try:
        system = CarbonIndexZKSystem()
        system.run_complete_workflow()
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

