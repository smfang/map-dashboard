#!/usr/bin/env python3
"""
SP1 Proof Generation Script for Carbon Index Calculations

This script generates zk proofs for carbon index calculations using SP1.
It processes NetCDF data, calculates the carbon index, and generates a proof
that the calculation was performed correctly.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import netCDF4 as nc
from datetime import datetime
import hashlib

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

from netcdf_handler import NetCDFProcessor
from netcdf_spatial_subsetting import GridHandler, GeoBoundingBox, SpatialQuery

class CarbonIndexProofGenerator:
    def __init__(self, sp1_program_path: str = "zk_proofs/sp1_program"):
        self.sp1_program_path = Path(sp1_program_path)
        self.proof_output_dir = Path("zk_proofs/proofs")
        self.proof_output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_proof_from_netcdf(
        self,
        netcdf_path: str,
        variable_name: str,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        time_idx: int = 0,
        current_rainfall: float = None
    ) -> Dict[str, Any]:
        """
        Generate a zk proof for carbon index calculation from NetCDF data.
        
        Args:
            netcdf_path: Path to the NetCDF file
            variable_name: Name of the variable to process
            lat_min, lat_max: Latitude bounds
            lon_min, lon_max: Longitude bounds
            time_idx: Time index to extract
            current_rainfall: Current rainfall value (if None, will be extracted from data)
            
        Returns:
            Dictionary containing proof data and metadata
        """
        print(f"Processing NetCDF file: {netcdf_path}")
        
        # Process NetCDF data
        processor = NetCDFProcessor(netcdf_path)
        
        try:
            # Get spatial subset of data
            subset_data = processor.get_spatial_subset(
                variable_name, lat_min, lat_max, lon_min, lon_max, time_idx
            )
            
            # Extract rainfall data
            rainfall_data = self._extract_rainfall_data(subset_data)
            
            # Use current rainfall from data if not provided
            if current_rainfall is None:
                current_rainfall = float(np.mean(rainfall_data))
            
            # Generate timestamp
            timestamp = int(datetime.now().timestamp())
            
            # Generate the proof
            proof_data = self._generate_sp1_proof(
                rainfall_data=rainfall_data,
                current_rainfall=current_rainfall,
                lat_min=lat_min,
                lat_max=lat_max,
                lon_min=lon_min,
                lon_max=lon_max,
                timestamp=timestamp
            )
            
            # Save proof data
            proof_hash = self._calculate_proof_hash(proof_data)
            proof_file = self.proof_output_dir / f"proof_{proof_hash}.json"
            
            with open(proof_file, 'w') as f:
                json.dump(proof_data, f, indent=2)
            
            print(f"Proof generated successfully: {proof_file}")
            print(f"Proof hash: {proof_hash}")
            
            return proof_data
            
        finally:
            processor.close()
    
    def _extract_rainfall_data(self, subset_data: Dict[str, Any]) -> List[float]:
        """Extract rainfall data from NetCDF subset."""
        data = subset_data['data']
        
        # Flatten the data and convert to list
        if hasattr(data, 'flatten'):
            rainfall_values = data.flatten()
        else:
            rainfall_values = np.array(data).flatten()
        
        # Remove NaN values and convert to list
        rainfall_values = rainfall_values[~np.isnan(rainfall_values)]
        
        # Ensure we have enough data points
        if len(rainfall_values) < 10:
            raise ValueError("Insufficient rainfall data points")
        
        return rainfall_values.tolist()
    
    def _generate_sp1_proof(
        self,
        rainfall_data: List[float],
        current_rainfall: float,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        timestamp: int
    ) -> Dict[str, Any]:
        """Generate SP1 proof using the Rust program."""
        
        # Create input file for SP1 program
        input_data = {
            "rainfall_data": rainfall_data,
            "current_rainfall": current_rainfall,
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
            "timestamp": timestamp
        }
        
        input_file = self.proof_output_dir / "input.json"
        with open(input_file, 'w') as f:
            json.dump(input_data, f)
        
        # Run SP1 program to generate proof
        try:
            # Change to SP1 program directory
            original_cwd = os.getcwd()
            os.chdir(self.sp1_program_path)
            
            # Build the program
            print("Building SP1 program...")
            build_result = subprocess.run(
                ["cargo", "build", "--release"],
                capture_output=True,
                text=True
            )
            
            if build_result.returncode != 0:
                raise RuntimeError(f"Build failed: {build_result.stderr}")
            
            # Run the program with input
            print("Generating proof...")
            run_result = subprocess.run(
                ["cargo", "run", "--release"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True
            )
            
            if run_result.returncode != 0:
                raise RuntimeError(f"Proof generation failed: {run_result.stderr}")
            
            # Read the generated proof
            proof_file = Path("proof-with-io.json")
            if not proof_file.exists():
                raise RuntimeError("Proof file not generated")
            
            with open(proof_file, 'r') as f:
                proof_data = json.load(f)
            
            # Format proof for ZKVerify submission
            zkverify_proof = self._format_proof_for_zkverify(proof_data, input_data)
            
            # Add metadata
            proof_data["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "input_data": input_data,
                "program_version": "0.1.0"
            }
            
            # Add ZKVerify formatted proof
            proof_data["zkverify_proof"] = zkverify_proof
            
            return proof_data
            
        finally:
            os.chdir(original_cwd)
    
    def _format_proof_for_zkverify(self, proof_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format proof data for ZKVerify submission."""
        try:
            # Extract proof bytes from SP1 proof data
            sp1_proof = proof_data.get("proof", {})
            
            # Convert proof to bytes (this would be the actual proof bytes in production)
            # For now, we'll create a mock proof bytes structure
            proof_bytes = json.dumps(sp1_proof, sort_keys=True).encode('utf-8')
            
            # Format public values to match Solidity encoding
            public_values = {
                "nhi_score": int(input_data.get("rainfall_data", [0])[0] * 1e18) if input_data.get("rainfall_data") else 0,
                "p20_percentile": int(20.0 * 1e18),  # Mock value
                "p90_percentile": int(90.0 * 1e18),  # Mock value
                "gamma_shape": int(2.0 * 1e18),      # Mock value
                "gamma_scale": int(20.0 * 1e18),     # Mock value
                "gamma_loc": int(0.0 * 1e18),        # Mock value
                "carbon_index_value": int(0.5 * 1e18),  # Mock value
                "timestamp": int(input_data.get("timestamp", 0)),
                "lat_min": int(input_data.get("lat_min", 0) * 1e18),
                "lat_max": int(input_data.get("lat_max", 0) * 1e18),
                "lon_min": int(input_data.get("lon_min", 0) * 1e18),
                "lon_max": int(input_data.get("lon_max", 0) * 1e18)
            }
            
            return {
                "proof_bytes": proof_bytes.hex(),
                "public_values": public_values,
                "proof_type": "sp1_carbon_index"
            }
            
        except Exception as e:
            print(f"Warning: Failed to format proof for ZKVerify: {e}")
            return {
                "proof_bytes": "0x",
                "public_values": {},
                "proof_type": "sp1_carbon_index",
                "error": str(e)
            }
    
    def _calculate_proof_hash(self, proof_data: Dict[str, Any]) -> str:
        """Calculate hash of the proof for identification."""
        # Create a deterministic hash from the proof data
        proof_string = json.dumps(proof_data, sort_keys=True)
        return hashlib.sha256(proof_string.encode()).hexdigest()[:16]
    
    def generate_proof_from_mock_data(
        self,
        lat_min: float = -10.0,
        lat_max: float = 10.0,
        lon_min: float = -10.0,
        lon_max: float = 10.0
    ) -> Dict[str, Any]:
        """Generate a proof using mock rainfall data for testing."""
        
        # Generate mock historical rainfall data (20 years of July rainfall)
        np.random.seed(42)  # For reproducible results
        rainfall_data = np.random.gamma(2.0, 20.0, 20).tolist()
        
        # Current season rainfall
        current_rainfall = 45.0
        
        # Generate timestamp
        timestamp = int(datetime.now().timestamp())
        
        return self._generate_sp1_proof(
            rainfall_data=rainfall_data,
            current_rainfall=current_rainfall,
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            timestamp=timestamp
        )

def main():
    """Main function to demonstrate proof generation."""
    generator = CarbonIndexProofGenerator()
    
    # Check if we have a NetCDF file
    netcdf_file = Path("mock_data.nc")
    
    if netcdf_file.exists():
        print("Generating proof from NetCDF data...")
        proof_data = generator.generate_proof_from_netcdf(
            netcdf_path=str(netcdf_file),
            variable_name="rainfall",  # Adjust based on your NetCDF variable
            lat_min=-10.0,
            lat_max=10.0,
            lon_min=-10.0,
            lon_max=10.0,
            time_idx=0
        )
    else:
        print("NetCDF file not found, generating proof from mock data...")
        proof_data = generator.generate_proof_from_mock_data()
    
    print("\nProof generation completed!")
    print(f"Carbon Index Value: {proof_data.get('public_values', {}).get('carbon_index_value', 'N/A')}")
    print(f"NHI Score: {proof_data.get('public_values', {}).get('nhi_score', 'N/A')}")

if __name__ == "__main__":
    main()

