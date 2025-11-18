import numpy as np
from netCDF4 import Dataset

# Create a new NetCDF file
with Dataset('mock_data.nc', 'w', format='NETCDF4') as ds:
    # Dimensions
    lat_dim = ds.createDimension('lat', 10)
    lon_dim = ds.createDimension('lon', 10)
    
    # Variables
    lats = ds.createVariable('lat', np.float32, ('lat',))
    lons = ds.createVariable('lon', np.float32, ('lon',))
    temp = ds.createVariable('temperature', np.float32, ('lat', 'lon'))
    wind = ds.createVariable('windspeed', np.float32, ('lat', 'lon'))
    precip = ds.createVariable('precipitation', np.float32, ('lat', 'lon'))
    
    # Attributes
    temp.units = 'degC'
    temp.long_name = 'Temperature'
    wind.units = 'm/s'
    wind.long_name = 'Windspeed'
    precip.units = 'mm'
    precip.long_name = 'Precipitation'
    
    # Data
    lats[:] = np.linspace(-90, 90, 10)
    lons[:] = np.linspace(-180, 180, 10)
    temp[:, :] = 15 + 10 * np.random.randn(10, 10)
    wind[:, :] = 5 + 2 * np.random.randn(10, 10)
    precip[:, :] = 50 + 20 * np.random.randn(10, 10)

print("Mock NetCDF file 'mock_data.nc' created.") 