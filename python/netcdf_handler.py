import netCDF4 as nc
from netcdf_spatial_subsetting import GridHandler, GeoBoundingBox, SpatialQuery
import numpy as np

class NetCDFProcessor:
    def __init__(self, netcdf_path):
        """
        Initialize the NetCDF processor with a file path.
        
        Args:
            netcdf_path (str): Path to the NetCDF file
        """
        self.dataset = nc.Dataset(netcdf_path)
        self.grid_handler = GridHandler(self.dataset)
        
    def get_variable_info(self):
        """
        Get information about available variables in the dataset.
        
        Returns:
            dict: Dictionary containing variable information
        """
        variables = {}
        for var_name, var in self.dataset.variables.items():
            if not is_observable(self.dataset, var_name):
                continue
            variables[var_name] = {
                'name': var_name,
                'dimensions': var.dimensions,
                'shape': var.shape,
                'units': getattr(var, 'units', 'N/A'),
                'long_name': getattr(var, 'long_name', var_name)
            }
        return variables
    
    def get_spatial_subset(self, var_name, lat_min, lat_max, lon_min, lon_max, time_idx=None):
        """
        Get a spatial subset of data for a specific variable.
        
        Args:
            var_name (str): Name of the variable to subset
            lat_min, lat_max (float): Latitude bounds
            lon_min, lon_max (float): Longitude bounds
            time_idx (int, optional): Time index to extract
            
        Returns:
            dict: Dictionary containing the subset data and metadata
        """
        # Create bounding box
        bbox = GeoBoundingBox(lat_min, lat_max, lon_min, lon_max, self.grid_handler)
        
        # Create spatial query
        query = SpatialQuery(var_name, bbox)
        
        # Set up the data slice
        if time_idx is not None:
            query.set_sliced_data(time_selector=time_idx)
        else:
            query.set_sliced_data(time_selector=0)  # Default to first time step
            
        # Get the data snapshot
        data = query.get_snapshot()
        
        # Get coordinate information
        if self.grid_handler.is_rectilinear:
            lats = bbox.masked_lats
            lons = bbox.masked_lons
        else:
            # For curvilinear grids, reshape the data to match the grid
            data = query.reshape_to_spatial_grid(data)
            lats = self.grid_handler.lats
            lons = self.grid_handler.lons
            
        return {
            'data': data,
            'lats': lats,
            'lons': lons,
            'variable_name': var_name,
            'units': getattr(self.dataset.variables[var_name], 'units', 'N/A')
        }
    
    def close(self):
        """Close the NetCDF dataset"""
        self.dataset.close()

def is_observable(dataset, var_name):
    """Check if a variable is an observable (not a coordinate variable)"""
    var = dataset.variables[var_name]
    return not (hasattr(var, 'axis') or hasattr(var, 'standard_name') or var_name in dataset.dimensions) 