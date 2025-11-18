# Python Workspace

This folder contains all Python code for data processing, proof generation, and dashboards.

## Structure

- `application.py` — Flask/Dash entrypoint (if applicable)
- `map_dashboard.py` — Interactive dashboard for visualizing carbon indices
- `netcdf_handler.py` — NetCDF reading utilities
- `netcdf_spatial_subsetting.py` — Spatial subsetting and grid handling
- `netcdf_tools.py` — Additional NetCDF helpers
- `indexcalc.py` — Reference calculations for NHI/carbon index
- `generate_mock_netcdf.py` — Utility to generate sample NetCDF data
- `test_map_dashboard.py` — Basic tests
- `requirements.txt` — Python dependencies
- `data/` — Sample datasets (e.g., `mock_data.nc`, `temp_mock_data.nc`)
- `zk_proofs/` — SP1 proof tooling
  - `generate_proof.py` — Orchestrates proof generation end-to-end
  - `verify_proof.py` — Submits and checks proofs on-chain
  - `deploy_and_test.py` — Demo workflow: deploy, generate proof, verify, update
  - `sp1_program/` — Rust/SP1 program used to produce proofs

## Quickstart

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate a proof from mock data
python zk_proofs/generate_proof.py

# Run the dashboard (if used)
python map_dashboard.py
```

## Notes

- Proof generation uses Succinct SP1 (see program in `zk_proofs/sp1_program`).
- Large NetCDF files should be stored in `python/data/` and git-ignored as needed.
