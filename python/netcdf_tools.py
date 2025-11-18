import netCDF4 as nc
import numpy as np

def detect_lat_lon_variables(dataset):
    """
    Detect latitude and longitude variables in a NetCDF dataset.
    
    Args:
        dataset (netCDF4.Dataset): The NetCDF dataset to analyze
        
    Returns:
        tuple: (lat_var, lon_var) where each is a netCDF4.Variable or None
    """
    lat_var = None
    lon_var = None
    
    # Common names for latitude and longitude variables
    lat_names = ['lat', 'latitude', 'LAT', 'Latitude', 'LATITUDE']
    lon_names = ['lon', 'longitude', 'LON', 'Longitude', 'LONGITUDE']
    
    # Check standard names first
    for var_name, var in dataset.variables.items():
        if hasattr(var, 'standard_name'):
            if var.standard_name == 'latitude':
                lat_var = var
            elif var.standard_name == 'longitude':
                lon_var = var
    
    # If not found by standard_name, check variable names
    if lat_var is None:
        for name in lat_names:
            if name in dataset.variables:
                lat_var = dataset.variables[name]
                break
    
    if lon_var is None:
        for name in lon_names:
            if name in dataset.variables:
                lon_var = dataset.variables[name]
                break
    
    return lat_var, lon_var

def is_observable(dataset, var_name):
    """
    Check if a variable is an observable (not a coordinate variable).
    
    Args:
        dataset (netCDF4.Dataset): The NetCDF dataset
        var_name (str): Name of the variable to check
        
    Returns:
        bool: True if the variable is an observable, False otherwise
    """
    var = dataset.variables[var_name]
    
    # Check if it's a coordinate variable
    if var_name in dataset.dimensions:
        return False
    
    # Check if it has axis attribute
    if hasattr(var, 'axis'):
        return False
    
    # Check if it has standard_name attribute
    if hasattr(var, 'standard_name'):
        return False
    
    return True

def count_decimal_places(value):
    """
    Count the number of decimal places in a number.
    
    Args:
        value (float): The number to check
        
    Returns:
        int: Number of decimal places
    """
    if isinstance(value, (int, np.integer)):
        return 0
    return len(str(value).split('.')[-1])

def count_significant_decimals(value):
    """
    Count the number of significant decimal places in a number.
    
    Args:
        value (float): The number to check
        
    Returns:
        int: Number of significant decimal places
    """
    if isinstance(value, (int, np.integer)):
        return 0
    return len(str(value).rstrip('0').split('.')[-1]) 