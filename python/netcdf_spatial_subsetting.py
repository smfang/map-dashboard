"""
Module:
    netcdf_spatial_subsetting

Notes:    
    This module comprises three classes, which together facilitate handling coordinate grid
    manipulations (GridHandler), spatial filtering (GeoBoundingBox), and variable interpolation
    across the coordinate grid (SpatialQuery). The classes handle rectilinear and curvilinear 
    grids, the former with independent regularly spaced longitude and latitude axes, the latter
    with combined 2D indices for each coordinate.

    A point of special attention is the ordering of the coordinates and their respective indices
    as they are passed around from one method to the other. The code invokes several libraries
    and methods, which implement different conventions: some expect the coordinates in the order
    (x, y) - or (longitude, latitude); some others expect them in reverse order; while some others
    yet are indifferent to the ordering so long as it is self-consistent. To handle this complexity
    we adopt the following strategy:

    - To begin with, we adopt the ordering convention (lat, lon) throughout this module.
    - Where needed, we reverse the order to (lon, lat) and transpose the respective vectors.
    - For a variable in a dataset, we determine explicitly the order of its dimensions as implemented.
    
    A further point of attention is the handling of curvilinear grids, where certain operations like
    interpolation require latitudes and longitudes in radians if the Haversine distance is defined as
    the metric. On the other hand, many netcdf libraries and CF conventions use degrees. Therefore,
    the best practice is to keep the grid in degrees for as long as possible and only convert to
    radians where required. This approach minimizes the risk of conversion errors and preserves CF
    conventions, while still allowing accurate geospatial computations where needed.
    
# Author: Marios Kagarlis
# Copyright (c) 2025 Ecomonitor
"""
import numpy as np                                                                      # Used for efficient vectorized operations where possible
from math import radians, atan2, sin, cos, sqrt                                         # Used to compute the Haversine distance metric
from shapely.geometry import Point, Polygon                                             # Expect coordinates in the order (lon, lat) or (x, y)
from sklearn.neighbors import BallTree                                                  # Expects coordinates in the order (lat, lon) or (y, x)
from scipy.spatial import KDTree                                                        # Insensitive to the coordinate order so long as used consistently
import netCDF4 as nc                                                                    # The order of coordinate dimensions per variable in principle may vary
from scipy.interpolate import RegularGridInterpolator, griddata, NearestNDInterpolator  # It's vital to handle the ordering of lat, lon consistently
from netcdf_tools import detect_lat_lon_variables, is_observable, count_decimal_places, count_significant_decimals  # Local utility functions

def is_int(i):                                                                          # Helper to check if type is Python or Numpy integer
    return isinstance(i, (int, np.integer))

def is_int_array(v):                                                                    # Helper to check if type is Numpy array of integers
    return isinstance(v, np.ndarray) and v.dtype == np.integer

#______________________________________________________________________________
class GridHandler:
    """
    Handles grid detection and coordinate operations based on dataset metadata.
    Implements enhanced spatial indexing for both rectilinear and curvilinear grids.

    This class provides methods for:
        - Detecting and validating latitude and longitude grid variables.
        - Extracting grid properties such as resolution, minimum/maximum values, and grid type.
        - Building spatial indices (KDTree or BallTree) for efficient searches in curvilinear grids.
        - Finding the grid pixel containing a given coordinate.
        - Finding the nearest grid point to a given coordinate.

    Attributes:
        CF_ATTRS (dict): Standard naming conventions for latitude and longitude resolution.
        use_haversine_matrix_on_tree_search_failure (bool): Flag to specify behavior in case of tree search failure.
        dataset (netCDF4.Dataset): The netCDF dataset.
        lat_var (netCDF4.Variable): Latitude variable.
        lon_var (netCDF4.Variable): Longitude variable.
        lats (ndarray): Latitude grid.
        lons (ndarray): Longitude grid.
        is_rectilinear (bool): True if the grid is rectilinear, False if curvilinear.
        lon_offset (int): Offset for longitude convention (0 for 0-360, 180 for -180-180).
        lat_dim_reversed (bool): True if latitude dimension is reversed.
        lat_min (float): Minimum latitude value.
        lat_max (float): Maximum latitude value.
        lat_res (float): Latitude resolution.
        lat_decimals (int): Latitude precision (number of significant decimals).
        lon_min (float): Minimum longitude value.
        lon_max (float): Maximum longitude value.
        lon_res (float): Longitude resolution.
        lon_decimals (int): Longitude precision (number of significant decimals).
        points (ndarray): (lat, lon) points in radians for curvilinear grids.
        tree (KDTree): KDTree for spatial indexing in curvilinear grids.
        shape (tuple): Shape of the latitude array for curvilinear grids.
        pixel_polygons (dict): Cache of pixel boundaries for curvilinear grids.
    """
    
    # Standard naming comventions for lat & lon resolution
    CF_ATTRS = {
        'lat': ['geospatial_lat_min', 'geospatial_lat_max', 'geospatial_lat_resolution'],
        'lon': ['geospatial_lon_min', 'geospatial_lon_max', 'geospatial_lon_resolution']
    }
 
    # Boolean flag specifying behavior in case of a failed k-d / Ball tree 
    # search, to identify the pixel of a curvilinear grid that contains a 
    # 2D point. See _precision_fallback method.
    use_haversine_matrix_on_tree_search_failure = False
    
    # Determines whether to cache polygons for curvilinear grids. Caching improves speed
    # but for large datasets caching polygons may crash memory, so best to build on the fly.
    cache_polygons = False
    
    """
    Options for nearest-neighbor searches:
    'kd_tree': Use for low to moderate dimensional data, efficient exact k-NN and axis-aligned range queries.
    'ball_tree': Use for moderate to high dimensional data, efficient approximate/exact k-NN for general distances.
    """
    nn_search_options = ['kd_tree', 'ball_tree']

    def __init__(self, dataset:nc.Dataset, user_lon_range = None, snap_grid = False):     # Grid handler constructor
        """
        Initializes GridHandler with a NetCDF dataset.
        
        Args:
            dataset: A netcdf dataset
            user_lon_range (tuple) = Optional (grid_lon_min, grid_lon_max) to set the range to [-180, 180) or [0, 360)
            snap_grid (bool): Uses precision computation to "snap" coordinate grids
                              to avoid potential roundoff errors (defaults to False)
        """
        if not isinstance(dataset, nc.Dataset):
            raise TypeError("GridHandler: constructor: 'dataset' must be a netCDF4.Dataset object")
        self._init_state()                                                     # Initialize the attributes
        self.dataset = dataset                                                 # Store the dataset
        self.lat_var, self.lon_var = detect_lat_lon_variables(dataset)         # Identify the coordinates in the dataset
        if self.lat_var is None or self.lon_var is None:
            raise ValueError("GridHandler: constructor: Could not detect latitude and/or longitude variables.")

        self._validate()                                                       # Validate coordinate dimensionalities
        self._get_properties(user_lon_range, snap_grid)                        # Extract grid properties from the dataset
        
    def _init_state(self):                                                     # Reset instance attributes
        # Universal attributes
        self.dataset = None                                                    # netCDF4 dataset
        self.lat_var = None                                                    # Latitude variable
        self.lon_var = None                                                    # Longitude variable
        self.lats = None                                                       # Latitude array (always sorted)
        self.lons = None                                                       # Longitude array (may be sorted or not)
        self.is_rectilinear = None                                             # True: rectilinear, False: curvilinear
        self.antimeridian_crossing = False                                     # True: grid wrapping around the antimeridian; else False (default)
        self.lon_offset = None                                                 # 0 🡺 lon ∈ [0, 360); 180 🡺 lon ∈ [-180, 180)
        self.lat_dim_reversed = None                                           # For lat to be in ascending order: True 🡺 reversed; False 🡺 as is 
        self.lat_min = None                                                    # Latitude minimum
        self.lat_max = None                                                    # Latitude maximum
        self.lat_res = None                                                    # Latitude resolution
        self.lat_decimals = None                                               # Latitude precision (number of significant decimals)
        self.lon_min = None                                                    # Longitude minimum
        self.lon_max = None                                                    # Longitude maximum
        self.lon_res = None                                                    # Longitude resolution
        self.lon_decimals = None                                               # Longitude precision (number of significant decimals)
        self.nn_search_option = 'ball_tree'                                    # Nearest neighbor search algorithm flag (Ball tree default)

        # In GridHandler, if the the longitudes are not crossing the antimeridian,
        # the array 'lons' is sorted and 'sorted_lons' is None (by default). But if
        # the longitudes cross the antimeridian, 'lons' are not monotonic but rolled
        # to move the discontinuity to the edges. In the latter case we keep copy of
        # the sorted longitudes in 'lons_sorted' for use by the interpolators.

        self.lons_sorted = None                                                # Sorted longitude copy only if self.lons not sorted
        
        # Curvilinear specific
        if hasattr(self, 'points'):                                            # (lat, lon) points in radians
            del self.points
        if hasattr(self, 'tree'):                                              # (lat, lon) k-d tree
            del self.tree
        if hasattr(self, 'pixel_polygons'):                                    # Grid pixel representation (for curvilinear grids, if cached)
            del self.pixel_polygons

    def get_type(self):
        """
        Returns the type of the class instance, identifying it as a parent 
        (GridHandler) or child (GeoBoundingBox, SpatialQuery) class instance.
        """
        return type(self).__name__                                            # Returns instance class name
       
    def get_info(self, verbosity=0):
        """
        Generates a string with information about the GridHandler instance.

        Args:
            verbosity (int): 0 for summary, 1 for detailed.

        Returns:
            str: A formatted string containing the GridHandler's attributes and their values.
        """
        info_str = f"GridHandler instance:\n"

        if verbosity == 0:  # Summary with class attributes, coords, and observables.
            info_str += "  Summary of Class Attributes:\n"
            for attr_name, attr_value in self.__dict__.items():
                if isinstance(attr_value, np.ndarray):
                    info_str += f"    {attr_name}: NumPy array with shape {attr_value.shape}\n"
                elif isinstance(attr_value, nc._netCDF4.Variable):
                    info_str += f"    {attr_name}: netCDF4.Variable '{attr_value.name}'\n"
                elif isinstance(attr_value, nc._netCDF4.Dataset):
                    info_str += f"    {attr_name}: netCDF4.Dataset\n"
                else:
                    info_str += f"    {attr_name}: {attr_value}\n"

            if isinstance(self.dataset, nc._netCDF4.Dataset):
                coordinates = []
                observables = []
                for var_name, var in self.dataset.variables.items():
                    if hasattr(var, 'axis') or hasattr(var, 'standard_name') or var_name in self.dataset.dimensions:
                        coordinates.append(var_name)
                    else:
                        observables.append(var_name)

                info_str += "  Dataset Coordinates:\n"
                info_str += f"    {coordinates}\n"
                info_str += "  Dataset Observables:\n"
                info_str += f"    {observables}\n"

        elif verbosity == 1:  # Detailed
            info_str += "  Universal Attributes:\n"
            info_str += f"    Dataset: {self.dataset}\n"
            info_str += f"    Latitude Variable: {self.lat_var.name if self.lat_var else None}\n"
            info_str += f"    Longitude Variable: {self.lon_var.name if self.lon_var else None}\n"
            info_str += f"    Latitude Grid Shape: {self.lats.shape if isinstance(self.lats, np.ndarray) else None}\n"
            info_str += f"    Longitude Grid Shape: {self.lons.shape if isinstance(self.lons, np.ndarray) else None}\n"
            info_str += f"    Is Rectilinear: {self.is_rectilinear}\n"
            info_str += f"    Longitude Offset: {self.lon_offset}\n"
            info_str += f"    Latitude Dimension Reversed: {self.lat_dim_reversed}\n"
            info_str += f"    Latitude Min: {self.lat_min}\n"
            info_str += f"    Latitude Max: {self.lat_max}\n"
            info_str += f"    Latitude Resolution: {self.lat_res}\n"
            info_str += f"    Latitude Decimals: {self.lat_decimals}\n"
            info_str += f"    Longitude Min: {self.lon_min}\n"
            info_str += f"    Longitude Max: {self.lon_max}\n"
            info_str += f"    Longitude Resolution: {self.lon_res}\n"
            info_str += f"    Longitude Decimals: {self.lon_decimals}\n"
            info_str += f"    Nearest Neighbor Search Algorihm: {self.nn_search_option}\n"

            # Curvilinear Specific Attributes
            if not self.is_rectilinear:
                info_str += "  Curvilinear Specific Attributes:\n"
                if isinstance(self.points, np.ndarray):
                    if len(self.points) > 10:
                        info_str += f"    Points Shape: {self.points.shape}\n"
                        info_str += f"    Points (first 5): {self.points[:5]}\n"
                        info_str += f"    Points (last 5): {self.points[-5:]}\n"
                    else:
                        info_str += f"    Points: {self.points}\n"
                else:
                    info_str += f"    Points Shape: {self.points.shape if hasattr(self, 'points') and isinstance(self.points, np.ndarray) else None}\n"

                info_str += f"    KDTree: {'Present' if hasattr(self, 'tree') and self.tree else 'Not Present'}\n"
                info_str += f"    Grid Shape: {self.lats.shape if hasattr(self, 'lats') else None}\n"
                info_str += f"    Pixel Polygons: {'Present' if hasattr(self, 'pixel_polygons') else 'Not Present'}\n"
        else:
            info_str += "  Invalid verbosity level."

        return info_str
    
    def _validate(self):
        """Verify grid properties and dimensionality"""
        if self.lat_var.ndim not in [1, 2] or self.lon_var.ndim not in [1, 2]:
            raise ValueError("Unsupported grid dimensionality")                # Raise error if invalid dimensions

        if self.lat_var.ndim != self.lon_var.ndim:
            raise ValueError("Mismatched lat, lon grid dimensionalities")      # Raise error if dimensions mismatch

    def _get_properties(self, user_lon_range, snap_grid):
        """
        Extract grid coordinates and metadata, including handling 
        masked arrays and optional grid snapping for precision.
        
        Args:
            user_lon_range (tuple) = Optional (grid_lon_min, grid_lon_max) to set the range to [-180, 180) or [0, 360)
        """
        self.is_rectilinear = self.lat_var.ndim == 1                           # Check if rectilinear grid

        if hasattr(self.lat_var, 'mask') and isinstance(self.lat_var.mask, np.ndarray) and np.any(self.lat_var.mask):        # Check if masking exists and any values are masked
            #self.lats = np.ma.filled(self.lat_var, np.nan)                    # Unmask latitudes, fill with NaN
            raise ValueError("GridHandler: _get_properties: Grid latitudes contain masked values.")

        self.lats = np.array(self.lat_var[:])                                  # Copy lat data to avoid modifying the original netcdf variable

        if hasattr(self.lon_var, 'mask') and isinstance(self.lon_var.mask, np.ndarray) and np.any(self.lon_var.mask):        # Check if masking exists and any values are masked
            #self.lons = np.ma.filled(self.lon_var, np.nan)                    # Unmask longitudes, fill with NaN
            raise ValueError("GridHandler: _get_properties: Grid longitudes contain masked values.")

        self.lons = np.array(self.lon_var[:])                                  # Copy lon data to avoid modifying the original netcdf variable

        # Determine axes ranges, and if rectilinear also the resolution and its precision
        self.lat_min, self.lat_max, self.lat_res, self.lat_decimals = self._get_axis_info('lat')   # Set the min, max, resolution, and precision
        self.lon_min, self.lon_max, self.lon_res, self.lon_decimals = self._get_axis_info('lon')   # Set the min, max, resolution, and precision

        self._detect_lon_convention(user_lon_range)                            # Detect longitude convention (0-360 or -180-180)
        self._normalize_grid_order()                                           # Ensure latitude and longitude are in ascending order

        if snap_grid:                                                          # Snap the coordinate grid to avoid precision errors
            if self.lat_decimals is not None:
                self.lats = np.round(self.lats, self.lat_decimals)             # Round latitudes to detected precision
            if self.lon_decimals is not None:
                self.lons = np.round(self.lons, self.lon_decimals)             # Round longitudes to detected precision
         
    def _detect_lon_convention(self, user_lon_range=None):
        """
        Determine the intrinsic longitude convention [-180, 180) or [0, 360) based on metadata or data.
        
        Args:
            user_lon_range (tuple): Optional (grid_lon_min, grid_lon_max) to set the range to [-180, 180) or [0, 360)
        
        If CF metadata is available (via valid_range or actual_range), use it:
        - If valid_range is present and unambiguous (e.g., valid_range[0] < 0 and valid_range[1] <= 180, 
            or valid_range[0] >= 0 and valid_range[1] > 180), use that.
        
        Otherwise, use data-based determination:
        - If the longitude minimum is < 0 and the maximum <= 180 degrees then use [-180, 180).
        - Else if the longitude minimum is >=0 and the maximum > 180 degrees then use [0, 360).
        - Otherwise, the determination is ambiguous; issue a warning and use a heuristic based on the median.
        
        If user_lon_range is provided, then:
        i. If intrinsic determination is unambiguous, it must agree with the user input.
        ii. If ambiguous, accept the user input.
        
        Sets self.lon_offset to 180 for [-180, 180) or 0 for [0, 360), and normalizes self.lons accordingly.
        """
        lon_var = self.lon_var
        self.lons = self.lons.copy()
        intrinsic = None

        # 1. Metadata-based detection
        valid_range = getattr(lon_var, 'valid_range', None)
        actual_range = getattr(lon_var, 'actual_range', None)
        
        if valid_range is not None:
            # If valid_range is provided and unambiguous:
            if valid_range[0] < 0 and valid_range[1] <= 180:
                intrinsic = 180
            elif valid_range[0] >= 0 and valid_range[1] > 180:
                intrinsic = 0

        elif actual_range is not None:
            # Use actual_range if unambiguous
            if actual_range[0] < 0 and np.abs(actual_range[1]) <= 180:
                intrinsic = 180
            elif actual_range[0] >= 0 and actual_range[1] > 180:
                intrinsic = 0

        # 2. Data-based detection if metadata was not unambiguous
        if intrinsic is None:
            if self.lon_min >= 0 and self.lon_max > 180:
                intrinsic = 0
            elif self.lon_min < 0 and self.lon_max <= 180:
                intrinsic = 180

        # 3. User input check (if provided)
        if user_lon_range is not None:
            user_min, user_max = user_lon_range
            if user_min < 0 and user_max <= 180:
                user_offset = 180
            elif user_min >= 0 and user_max > 180:
                user_offset = 0
            else:
                raise ValueError("GridHandler: _detect_lon_convention: User-specified longitude range is invalid")
            # If our data-based determination is unambiguous, they must agree.
            if intrinsic is None:
                intrinsic = user_offset
            elif intrinsic != user_offset:
                raise ValueError("GridHandler: _detect_lon_convention: Intrinsic longitude convention conflicts with user input")
        elif intrinsic is None:
                raise ValueError("GridHandler: _detect_lon_convention: Ambiguous intrinsic longitude range;"
                                 "provide user_lon_range to disambiguate.")
            
        self.lon_offset = intrinsic

        # 4. Final normalization of self.lons based on determined convention
        if self.lon_offset == 0:            # 0-360 convention
            self.lons = self.lons % 360
        else:                               # -180-180 convention
            self.lons = (self.lons + 180) % 360 - 180

    def _normalize_grid_order(self):
        """
        Ensure the grid latitudes are sorted in ascending order and reorder longitudes
        if necessary. For longitudes, if the data spans an antimeridian discontinuity,
        shift the discontinuity to an edge. Otherwise, sort in ascending order.
        
        This method preserves the intrinsic longitude convention (0–360 or –180–180)
        as determined by _detect_lon_convention.
        """
        if self.is_rectilinear:
 
            if self.lats[-1] < self.lats[0]:                                   # Ensure latitudes are ascending
                self.lats = self.lats[::-1]
                self.lat_dim_reversed = True
            else:
                self.lat_dim_reversed = False

            lons_sorted = np.sort(self.lons)                                   # Monotonic version of the longitude array
            # Determine if grid crosses the antimeridian.
            if lons_sorted[-1] - lons_sorted[0] > 180:                         # Crossing the antimeridian if True
                self.antimeridian_crossing = True                              # Flag as crossing the antimeridian
                split_idx = np.argmax(np.diff(self.lons) < 0)                  # Identify split point where crossing occurs
                self.lons = np.roll(self.lons, -split_idx-1)                   # Roll the longitude array to move the discontinuity to the edges
                self.lons_sorted = np.sort(self.lons)                          # Keep a copy of the sorted longitudes for later use
            else:                                                              # No wrap-around detected
                self.lons = lons_sorted                                        # Replace longitudes with the sorted array

    def normalize_longitudes(self, lons):
        """
        Normalize input longitudes to match the grid's storage convention (0–360 or –180–180).
        This method does not perform antimeridian wrap-around adjustments (which are handled
        during containment checks) but simply casts the input values to the proper range.
        """
        is_list = isinstance(lons, list)
        if is_list:
            lons = np.array(lons, dtype=float)
        
        if not (isinstance(lons, (np.ndarray, float, int)) or np.isscalar(lons)):
            raise TypeError("GridHandler: normalize_longitudes: Invalid input type for longitude normalization.\n"
                            "Input can be a single numeric value, or a list or numpy array of numeric values.")

        if self.lon_offset == 180:                                             # [-180, 180) range convention
            normalized = (lons + 180) % 360 - 180
        else:                                                                  # [0, 360) range convention
            normalized = lons % 360

        return normalized.tolist() if is_list else normalized

    def _build_spatial_index(self, points_only = False):                       # Build spatial index for curvilinear grids on demand
        """
        Build spatial index for efficient nearest neighbor searches
        (KDTree of BallTree) with Haversine-aware coordinates, store points as (lats_rad, lons_rad)
        Argument:
            points_only (bool): If True, build only the points array (for use in SpatialQuery).
        Note:
            Ball Tree is a more accurate method for curvilinear grids, using Haversine distance
            as the metric. When the latter is used, BallTree expects the coordinates in the order
            (latitude, longitude). On the other hand, KDTree uses Euclidean distance as the metric
            and consequently it is not sensitive to the order in which the coordinates are passed.
            Nonetheless, for consistency we will adhere to the convention of passing coordinates
            and related indices in the order (latitude, longitude), unless explicitly stated otherwise.
        """
        if self.is_rectilinear:                                                # Not needed - nothing to do
            return
        if self.lats is None or self.lons is None:
            raise ValueError("GridHandler: _build_spatial_index: Latitude and longitude arrays are not set.")
        if self.nn_search_option not in GridHandler.nn_search_options:
            raise ValueError(f"GridHandler: _build_spatial_index: Invalid NN search option {self.nn_search_option}, "
                             f"must be one of {GridHandler.nn_search_options}.")
        use_kd_tree = self.nn_search_option == 'kd_tree'
        lons_rad = np.radians(self.lons.ravel())                               # Convert longitudes to radians
        lats_rad = np.radians(self.lats.ravel())                               # Convert latitudes to radians
        self.points = np.column_stack((lats_rad, lons_rad))                    # Build (lat, lon) points for the tree searches
        if not points_only:
            self.tree = (KDTree(self.points) if use_kd_tree                    # Use a k-d tree for fast spatial queries, or 
                        else BallTree(self.points, metric='haversine'))        # Ball tree (default) for more accurate searches
            if GridHandler.cache_polygons:                                     # Generate and cache pixel polygons if true (memory intensive)
                self._build_pixel_polygons_cache()                             # Create cache of pixel boundaries for efficient point-in-polygon checks

    def _build_pixel_polygons_cache(self):
        """
        Create a cache of pixel boundaries for curvilinear grids.
        
        For a curvilinear grid (where lats and lons are 2D arrays), this method computes 
        a list of shapely Polygon objects, each representing the boundary of a grid cell.
        Assumes that each pixel is defined by the four corner points in (lon, lat) order:
            (lons[i, j], lats[i, j]),
            (lons[i, j+1], lats[i, j+1]),
            (lons[i+1, j+1], lats[i+1, j+1]),
            (lons[i+1, j], lats[i+1, j])
        """
        if self.is_rectilinear:
            return
        M, N = self.lats.shape
        self.pixel_polygons = np.empty(self.lats.shape, dtype=object)          # Initialize the cache
        # Iterate over the grid cells (assume cells defined by adjacent grid points)
        for i in range(M - 1):                                                 # Form polygon from four corners
            for j in range(N - 1):
                self.pixel_polygons[i,j] = Polygon([                           # Polygon expects (x, y) or (lon, lat) order
                    (self.lons[i, j], self.lats[i, j]),
                    (self.lons[i, j+1], self.lats[i, j+1]),
                    (self.lons[i+1, j+1], self.lats[i+1, j+1]),
                    (self.lons[i+1, j], self.lats[i+1, j])
                ])
        
    def get_grid_type(self):
        """Returns the grid type: rectilinear or curvilinear."""
        return "rectilinear" if self.is_rectilinear else "curvilinear"         # Return grid type

    def _get_axis_info(self, axis):
        """
        Get the minimum, maximum, and resolution for a given coordinate axis.

        For rectilinear grids (with 1D coordinate variables), if the resolution is not specified
        in the metadata, the method computes the differences between successive values and checks
        if they are nearly constant. If so, it returns the first difference rounded to the intrinsic
        grid precision (using count_decimal_places). For curvilinear grids (when the coordinate variable
        is not 1D), a single resolution is ambiguous and the method returns None for resolution.

        Args:
            axis (str): 'lat' or 'lon' indicating the coordinate axis.

        Returns:
            tuple: (min_value, max_value, resolution, decimals), where resolution is a float for regular 
            grids, otherwise None, and decimals is the number of significan decimals to keep (if not None)
        """
        if axis == 'lat':
            var = self.lat_var
            var_data = self.lats
        else:
            var = self.lon_var
            var_data = self.lons
        
        var_min = np.nanmin(var_data)
        var_max = np.nanmax(var_data)

        if not self.is_rectilinear or var_data.size < 2:
            return var_min, var_max, None, None

        var_res = None
        attr_name = GridHandler.CF_ATTRS[axis][2]   # e.g. 'geospatial_lat_resolution' or 'geospatial_lon_resolution'
        if attr_name in var.ncattrs():              # Try to retrieve the resolution from metadata using CF conventions.
            try:
                var_res = float(var.getncattr(attr_name))
                decimals = count_decimal_places(var_res)
                var_res = round(var_res, decimals)
            except Exception:
                pass
            
        # If metadata resolution is missing or invalid, calculate it from the data.
        if var_res is None:
            # Calculate from data
            diffs = np.diff(var_data)
            n_diffs = diffs.size
            
            
            median_diff = np.nanmedian(diffs) if n_diffs > 1 else diffs[0]
            # Dynamic tolerance calculation
            grid_span = var_max - var_min
            rel_tol = max(1e-5, 1e-5 * grid_span / n_diffs)
            abs_tol = max(1e-8, 1e-3 * median_diff)

            if not np.allclose(diffs, median_diff, rtol=rel_tol, atol=abs_tol):
                return var_min, var_max, None, None
            
            # Determine precision using numerical methods
            decimals, var_res = count_significant_decimals(median_diff)
        
        return var_min, var_max, var_res, decimals            

    def find_rectilinear_grid_neighbors(self, lat, lon, all_containing_pixel_nodes = False,
                                        cell_corner='SW'):
        """
        Generates valid neighboring indices with bounds checking for rectilinear grids.
        
        For a rectilinear grid, the cell containing the query point is determined via searchsorted
        on the 1D latitude and longitude arrays. If all_containing_pixel_nodes is False, a single 
        candidate is returned based on the specified cell corner (default 'SW'). If True, all four
        cell corner indices are returned.
        
        Args:
            lat (float): Latitude in degrees.
            lon (float): Longitude in degrees.
            all_containing_pixel_nodes (bool): If True, returns the nodes of the containing pixel (typically 4).
            cell_corner (str): One of 'SW', 'SE', 'NW', 'NE' indicating which corner defines the cell.
                               Default is 'SW
        Returns:
            If all_containing_pixel_nodes is False: a tuple (lat_idx, lon_idx) corresponding to the specified corner.
            If True: a numpy.ndarray of shape (N, 2) (typically N=4), where each row is a [lat_idx, lon_idx] pair.
        """
        if not self.is_rectilinear:
            raise ValueError("GridHandler: find_rectilinear_grid_neighbors: Method only for rectilinear grids.")
        
        # Define offset mapping, with latitudes sorted in ascending order (south to north)
        corner_offsets = {                                                     # Define offsets: (4, 2) array
            'SW': np.array([0, 0]),
            'SE': np.array([0, 1]),
            'NW': np.array([1, 0]),
            'NE': np.array([1, 1])
        }

        lon = self.normalize_longitudes(lon)                                   # Normalize longitudes to match grid convention
        
        # Determine the indices such that:
        #   self.lats[lat_idx] <= lat < self.lats[lat_idx+1]
        #   self.lons[lon_idx] <= lon < self.lons[lon_idx+1]
        lat_idx = np.searchsorted(self.lats, lat) - 1                          # Find the latitude index
    
        # Determine the indices using sorted_lons for longitude
        sorted_lons = self.lons_sorted if self.lons_sorted is not None else self.lons
        lon_idx_sorted = np.searchsorted(sorted_lons, lon) - 1                 # Find the longitude index
        
        if self.lons_sorted is not None:                                       # Map back onto the original indices
            target_lon = sorted_lons[lon_idx_sorted]                           # Find closest index in original lons array
            lon_idx = np.argmin(np.abs(self.lons - target_lon))
        else:                                                                  # The sorted and original indices coincide
            lon_idx = lon_idx_sorted
        
        base_candidate = np.array([lat_idx, lon_idx])                          # Base candidate indices: (1, 2)
        
        if not all_containing_pixel_nodes:                                     # Return just the nearest node
             
            if cell_corner not in corner_offsets:                              # Validate cell_corner input
                raise ValueError("GridHandler: find_rectilinear_grid_neighbors:Invalid cell_corner value. Must be one of: 'SW', 'SE', 'NW', 'NE'.")
            
            candidate = base_candidate + corner_offsets[cell_corner]           # Return the single candidate based on the requested corner.

            # Clip indices to ensure we stay within grid bounds.
            candidate[0] = np.clip(candidate[0], 0, self.lats.shape[0] - 1)
            candidate[1] = np.clip(candidate[1], 0, self.lats.shape[1] - 1)

            return tuple(candidate)                                            # Return the single candidate indices

        # Otherwise, generate all four candidates.
        candidate_ijs = np.array([base_candidate + corner_offsets[corner]      # Generate all corner candidates: (1, 2) + (4, 2) 🡺 (4, 2)
                                  for corner in corner_offsets])

        # Clip indices to grid bounds.
        candidate_ijs[:, 0] = np.clip(candidate_ijs[:, 0], 0, self.lats.shape[0] - 1)
        candidate_ijs[:, 1] = np.clip(candidate_ijs[:, 1], 0, self.lons.shape[0] - 1)
        
        # unique_pixels = np.unique(candidate_ijs, axis=0)                       # Remove duplicates if any (e.g., near grid boundaries)

        # To remove potential duplicates (e.g., near grid boundaries): 
        _, idx = np.unique(candidate_ijs, axis=0, return_index=True)           # Use a list to preserve order while removing duplicates
        unique_pixels = candidate_ijs[np.sort(idx)]

        return unique_pixels                                                   # Return unique pixels: (N, 2) with N <= 4


    def find_curvilinear_grid_neighbors(self, lat, lon, k=1):
        """
        Finds the k nearest neighbors and generates candidate pixel indices
        for curvilinear grids. A k-d or BallTree search is used, because for
        curvilinear grids the nearest neighbors may not correspond to simply 
        adjacent pixels in the grid.

        Args:
            lat (float): Latitude in degrees.
            lon (float): Longitude in degrees.
            k (int): Number of nearest neighbors to find.

        Returns:
            numpy.ndarray: Array of candidate pixel indices of shape (k, 2).
            
            The returned candidate indices correspond to grid cell indices
            (row, column) in the 2D coordinate arrays.
        """
        if self.is_rectilinear:
            raise ValueError("GridHandler: find_curvilinear_grid_neighbors: Method only for curvilinear grids.")
        
        lon = self.normalize_longitudes(lon)                                   # Normalize longitudes to match grid convention
        
        if not hasattr(self, 'tree'):                                          # Ensure the tree has been built before searching
            self._build_spatial_index()                                        # Build spatial indices and tree on first call

        target = np.atleast_2d(np.array([radians(lat), radians(lon)]))         # Create 2D target array: (2, ) 🡺 (1, 2)
        _, indices = self.tree.query(target, k=k)                              # Query Ktree for nearest neighbors: (1, 2) 🡺 (1, k)
        if k == 1:
            indices = np.array([indices])                                      # Convert scalar to array: (1, ) 🡺 (1, 1)
        neighbors = np.unravel_index(indices, self.lats.shape)                 # Convert to grid indices: (1, k) 🡺 (k, ), (k, )

        neighbors = np.stack(neighbors, axis=-1)                               # Reshape to: (1, k, 2)
        return np.squeeze(neighbors, axis=0)                                   # Reshape to: (k, 2)


    def find_containing_pixel(self, lat, lon, cell_corner='SW'):
        """
        Find pixel containing the point (lat, lon) using a method depending
        on grid type. Vectorized implementation with edge-case handling.
        
        Args:
            lat: The latitude        
            lon: The longitude
            cell_corner (str): Which corner defines the cell for single-candidate return.
                               Acceptable values are 'SW', 'SE', 'NW', 'NE'. Default is 'SW'.
            
        Returns:
            lat_idx: The latitude index
            lon_idx: The longitude index
        """
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise TypeError("GridHandler: find_containing_pixel: lat and lon must be numeric.")

        lon = self.normalize_longitudes(lon)                                   # Normalize longitudes to match grid convention

         # Bounds check
        if not (self.lon_min <= lon <= self.lon_max
                and self.lat_min <= lat <= self.lat_max):
            return None, None

        if self.is_rectilinear:
            return self.find_rectilinear_grid_neighbors(lat = lat, lon = lon, all_containing_pixel_nodes = False,
                                                        cell_corner=cell_corner)

        # For curvilinear grids, use a tree-based search.
        neighbor_pixels = self.find_curvilinear_grid_neighbors(lat, lon, k=4)
        
        point = Point(lon, lat)                                                # Point expects (lon, lat) in this order
        if GridHandler.cache_polygons:                                         # Expecting pixel polygons to have been cached
            try:                                                               # Vectorized point-in-polygon check
                in_pixel_mask = np.array([
                    self.pixel_polygons[i, j].contains(point)                  # Sel-consistent (lon, lat) order across Point 
                    for i, j in neighbor_pixels                                #  and Polygon for correct containment testing
                ], dtype = bool)
            except ValueError:
                raise ValueError(f"GridHandler: find_containing_pixel: Expected pixel polygon cache not found")
            if np.any(in_pixel_mask):
                return tuple(neighbor_pixels[in_pixel_mask][0])
        else:                                                                  # Generate needed pixel polygons dynamically on demand
            for i, j in neighbor_pixels:
                polygon = Polygon([                                            # Create polygon on-the-fly with (lon, lat) in this order
                    (self.lons[i, j], self.lats[i, j]),
                    (self.lons[i, j+1], self.lats[i, j+1]),
                    (self.lons[i+1, j+1], self.lats[i+1, j+1]),
                    (self.lons[i+1, j], self.lats[i+1, j])
                ])
                if polygon.contains(point):
                    return (i, j)

        # The k-d or Ball tree search should get the pixel in 99.9% of the cases
        # A precision fallback computation for the 0.1 % of cases may be too costly.
        return self._precision_fallback(lat, lon, neighbor_pixels[0])


    def _precision_fallback(self, lat, lon, nearest_ij, n_window = 3):
        """
        Hybrid fallback with thresholding
        
        Args:
            lat: The latitude
            lon: The longitude
            nearest_ij: The nearest indices (lat, lon) tuple
            n_window (int): The window size for the local search
        """
        i, j = nearest_ij                                                      # Unpack the (i, j) tuple

        # To lowest order, we can just return these indices 
        # If use_haversine_matrix_on_k_d_failure == False (default)

        if GridHandler.use_haversine_matrix_on_tree_search_failure:            # Else: apply a hybrid approach

            # Define a local window n_window x n_window around nearest_ij
            i_min = max(0, i - 1)
            i_max = min(self.lats.shape[0], i + n_window - 1)
            j_min = max(0, j - 1)
            j_max = min(self.lats.shape[1], j + n_window - 1)

            local_lats = self.lats[i_min:i_max, j_min:j_max]
            local_lons = self.lons[i_min:i_max, j_min:j_max]

            dist = self._haversine_distance(lat, lon, local_lats, local_lons)  # Compute the Haversine distance to the candidate
            local_min = np.unravel_index(np.argmin(dist), dist.shape)          # Find the local minimum
            
            i = i_min + local_min[0]                                           # Update the indices
            j = j_min + local_min[1]
            
        return i, j
            
    def estimate_local_resolution(self, i, j):
        """
        Calculate effective resolution from neighboring points.
        Useful for curvilinear grids.
        """
        neighbors = []
        # Get valid neighbors (handle grid edges)
        if i > 0: neighbors.append((i-1, j))                        # South (decrement lat)
        if i < self.lats.shape[0]-1: neighbors.append((i+1, j))     # North (increment lat)
        if j > 0: neighbors.append((i, j-1))                        # West (decrement lon)
        if j < self.lats.shape[1]-1: neighbors.append((i, j+1))     # East (increment lon)
        
        if not neighbors:                                           # Edge case with no neighbors
            coverage_fraction = (self.lat_max - self.lat_min) / 360 # Normalize to Earth's full range
            return 40075 / max(self.lats.shape) * coverage_fraction # Global average relative to Earth's circumference in km
        
        # Calculate distances to all valid neighbors
        distances = [
            self._haversine_distance(self.lats[i,j], self.lons[i,j],
                                     self.lats[ni,nj], self.lons[ni,nj])
            for ni, nj in neighbors
        ]
        
        return np.max(distances)                                    # Conservative estimate using max distance
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate great-circle distance between two points"""
        R = 6371                                                   # Earth radius in km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))                   # Distance in km

#______________________________________________________________________________
class GeoBoundingBox:
    """
    Represents geographical bounds with validation and snapping to a grid.

    A user-defined bounding box may represent:
      - an area (if both latitude and longitude ranges are provided),
      - a line (if one coordinate is a range and the other is a single value),
      - or a point (if both are given as single values).

    The bounding box is normalized and "snapped" to the underlying grid (via a GridHandler instance)
    so that the resulting bounds align with grid nodes. This class also provides methods to generate
    boolean masks and masked coordinates for spatial subsetting.

    Attributes:
        grid (GridHandler): The associated grid for spatial context.
        lat_min (float): Snapped minimum latitude.
        lat_max (float): Snapped maximum latitude.
        lon_min (float): Snapped minimum longitude.
        lon_max (float): Snapped maximum longitude.
        lat_mask (np.ndarray): 1D boolean mask for latitudes within the bounding box (rectilinear).
        lon_mask (np.ndarray): 1D boolean mask for longitudes within the bounding box (rectilinear).
        combined_mask (np.ndarray) : flattened 1D boolean mask of combine spatial dimensions (curvilineear).
        masked_lats (np.ndarray): 1D array of latitudes (in degrees) within the bounding box (for rectilinear grids).
        masked_lons (np.ndarray): 1D array of longitudes (in degrees) within the bounding box (for rectilinear grids).
        masked_points (np.ndarray): 2D array of (lat, lon) points in radians for curvilinear grids.
    """
    
    def __init__(self, lat_min=None, lat_max=None, lon_min=None, lon_max=None, # Class constructor
                 grid: GridHandler = None):
        """
        Initializes GeoBoundingBox with latitude and longitude bounds.

        Args:
            lat_min (float or None): Desired minimum latitude.
            lat_max (float or None): Desired maximum latitude.
            lon_min (float or None): Desired minimum longitude.
            lon_max (float or None): Desired maximum longitude.
            grid (GridHandler): A GridHandler instance providing grid context.
            
        The constructed instance is the minimum bounding box on the grid that
        contains the user defined bounding box. If the latter already overlaps 
        with the grid, the two coincide.

        Raises:
            ValueError: If grid is None or if the specified bounds fall outside the grid domain.
        """
        self._init_state()                                                     # Initializes the attributes
        self.set(lat_min, lat_max, lon_min, lon_max, grid)                     # Sets the attributes

    # Private (internal methods)____________________________________________

    # 1. Basic setup

    def _init_state(self):
        """Inatializes the bounding box attributes"""
        self.grid = None                                                       # Placeholder for a GridHandler instance
        self.lat_min = self.lat_max = None                                     # Placeholders for latitude min and max
        self.lon_min = self.lon_max = None                                     # Placeholders for longitude min and max
        self.lat_mask = self.lon_mask = self.combined_mask = None              # Placeholders for spatial coordinate masks
        self.masked_points = None                                              # Placeholder for 2D array of lat/lon points in rad (curvilinear)
        self.masked_lats = self.masked_lons = None                             # Placeholder for 1D lat/lon arrays in degrees (rectilinear)

    def _snap_rectilinear_grid_bounding_box(self, roundoff = 1e-6):
        """
        Adjusts the normalized user-defined bounding box to the nearest enclosing grid 
        nodes for rectilinear grids.
        
        Args:
            roundoff (float): Tolerance for precision errors (default 1e-6).
                              For comparison, the standard Python single-precision 
                              floating point error is ~1.19 x 10⁻⁷

        Uses the grid's sorted latitude and longitude arrays to "snap" the user-defined
        bounds.If the grid crosses the antimeridian, the longitude array is "rolled" to 
        move the discontinuity to the edges and cosequently is not monotonic.
        """
        # Snap latitudes using the grid's sorted (and physically ordered) latitude array.
        self.lat_min = self.grid.lats[self.grid.lats <= self.lat_min - roundoff].max(initial=self.grid.lats[0])
        self.lat_max = self.grid.lats[self.grid.lats >= self.lat_max + roundoff].min(initial=self.grid.lats[-1])
        
        # For longitudes, use the sorted (monotonic) version for snapping.
        sorted_lons = self.grid.lons if self.grid.lons_sorted is None else self.grid.lons_sorted
        self.lon_min = sorted_lons[sorted_lons <= self.lon_min - roundoff].max(initial=sorted_lons[0])
        self.lon_max = sorted_lons[sorted_lons >= self.lon_max + roundoff].min(initial=sorted_lons[-1])

    def _snap_curvilinear_grid_bounding_box(self, roundoff=1e-6):
        """
        Adjusts the bounding box to tightly enclose grid points within the user-defined bounds.
        
        Args:
            roundoff (float): Tolerance for precision errors (default 1e-6).
                              For comparison, the standard Python single-precision 
                              floating point error is ~1.19 x 10⁻⁷

        Uses the grid's 2D latitude and longitude arrays to determine the tightest bounds,
        with a tolerance allowing for precision errors. If no grid points are found within 
        the user bounds, expands to include the cell that contains the center of the user
        defined bounding box.
        """
        # Create a mask based on the user's original bounds (before any snapping)
        user_lat_mask = (self.grid.lats >= self.lat_min - roundoff) & (self.grid.lats <= self.lat_max + roundoff)
        user_lon_mask = (self.grid.lons >= self.lon_min - roundoff) & (self.grid.lons <= self.lon_max + roundoff)
        combined_mask = user_lat_mask & user_lon_mask

        if np.any(combined_mask):    # Calculate snapped bounds using ONLY points within the user's original bounds
            snapped_lat_min = np.nanmin(self.grid.lats[combined_mask])
            snapped_lat_max = np.nanmax(self.grid.lats[combined_mask])
            snapped_lon_min = np.nanmin(self.grid.lons[combined_mask])
            snapped_lon_max = np.nanmax(self.grid.lons[combined_mask])
        else:                        # Fallback: if none, use the cell containing the user bounding box center.
            center_lat = (self.lat_min + self.lat_max) / 2.0
            center_lon = (self.lon_min + self.lon_max) / 2.0
            
            if not (self.grid.lat_min <= center_lat <= self.grid.lat_max and
                    self.grid.lon_min <= center_lon <= self.grid.lon_max):
                raise ValueError("GeoBoundingBox: _snap_curvilinear_grid_bounding_box: Bounding box center lies outside grid domain")

            # Use GridHandler's method to find the containing pixel.
            i, j = self.grid.find_containing_pixel(center_lat, center_lon)
            if i is None or j is None:
                raise ValueError("GeoBoundingBox: _snap_curvilinear_grid_bounding_box: No grid points found in curvilinear grid for user bounding box.")
            # Assume each grid cell is defined by the four corner points:
            cell_lats = [self.grid.lats[i, j], self.grid.lats[i, j+1], self.grid.lats[i+1, j+1], self.grid.lats[i+1, j]]
            cell_lons = [self.grid.lons[i, j], self.grid.lons[i, j+1], self.grid.lons[i+1, j+1], self.grid.lons[i+1, j]]
            snapped_lat_min = min(cell_lats)
            snapped_lat_max = max(cell_lats)
            snapped_lon_min = min(cell_lons)
            snapped_lon_max = max(cell_lons)
         
        self.lat_min, self.lat_max = snapped_lat_min, snapped_lat_max
        self.lon_min, self.lon_max = snapped_lon_min, snapped_lon_max
       
    # 2. Mask setup

    def _set_masks(self, force=False):
        """
        Builds and caches the 1D boolean masks for latitude and longitude that indicate
        which grid points lie within the snapped bounding box. For rectilinear grids is
        stores these masks for later use. For curvilinear grids it combines them into a
        flattened 1D array of booleans, combined_mask, and stores it for later use.

        Args:
            force (bool): Rebuild the masks even if they are already set (default False).

        Raises:
            ValueError: If the resulting masks are invalid.

        Behavior:
            For rectilinear grids: stores two 1D masks for lat & lon separately.
            For curvilinear grids, stores a flattened 2D mask combining elementwise
                                   AND operation applied to both lat and lon arrays.
        """
        recti_grid = self.grid.is_rectilinear
        if (force or (recti_grid and (self.lat_mask is None or self.lon_mask is None))
                or (not recti_grid and self.combined_mask is None)):           # Build the lat/lon masks

            lat_mask = (self.grid.lats >= self.lat_min) & (self.grid.lats <= self.lat_max)
            
            if recti_grid:

                self.lat_mask = lat_mask
                sorted_lons = self.grid.lons_sorted if self.grid.lons_sorted is not None else self.grid.lons
                left = np.searchsorted(sorted_lons, self.lon_min, side='left')
                right = np.searchsorted(sorted_lons, self.lon_max, side='right')

                if self.lon_min <= self.lon_max:                               # Handle non-wrapping bounds
                    valid_sorted_indices = np.arange(left, right)
                else:                                                          # Handle wrapping bounds
                     valid_sorted_indices = np.concatenate([
                        np.arange(left, len(sorted_lons)),
                        np.arange(0, right)
                    ])
                if self.grid.lons_sorted is not None:                          # Map sorted indices to original indices
                    valid_indices = np.where(np.isin(self.grid.lons, sorted_lons[valid_sorted_indices]))[0]
                else:                                                          # Sorted and original indices coincide
                    valid_indices = valid_sorted_indices

                self.lon_mask = np.zeros_like(self.grid.lons, dtype=bool)
                self.lon_mask[valid_indices] = True

                if not np.any(self.lon_mask) or not np.any(self.lat_mask):     # Validate non-empty masks
                    raise ValueError("Bounding box does not intersect the grid.")
            else:                                                              # Curvilinear grid handling
                if self.lon_min <= self.lon_max:
                    lon_mask = (self.grid.lons >= self.lon_min) & (self.grid.lons <= self.lon_max)
                else:                                                          # Crossing the antimeridian
                    lon_mask = (self.grid.lons >= self.lon_min) | (self.grid.lons <= self.lon_max)

                combined = lat_mask & lon_mask
                self.combined_mask = np.flatnonzero(combined.ravel())

                if len(self.combined_mask) == 0:
                    raise ValueError("GeoBoundingBox: _set_masks: Bounding box does not intersect the grid.")
            
    def _build_masked_coordinates(self, force=False):
        """
        Builds masked spatial coordinate arrays for the bounding box.
        
        For rectilinear grids: produces separate 1D arrays (in degrees) for latitudes and longitudes.
        For curvilinear grids: returns a flat 1D array (or 2D array, but flattened) of
                               the spatial coordinates in radians that fall within the bounding box.
        Different units are used for the two cases to align with the respective interpolator conventions.
        
        Parameter:
            force (bool): If True, force rebuilding even if already set.
            
        Raises:
            ValueError if no grid points are found in the bounding box.
        """
        if (force or (    self.grid.is_rectilinear and (self.masked_lats is None or self.masked_lons is None))
                  or (not self.grid.is_rectilinear and self.masked_points is None)):
            self._set_masks(force)                                             # First set the masks if needed
            if self.grid.is_rectilinear:                                       # For rectilinear grids:
                self.masked_lats = self.grid.lats[self.lat_mask]               # Latitude array within the bounding box range
                # See comments related to 'lons_sorted' in GridHandler
                sorted_lons = self.grid.lons if self.grid.lons_sorted is None else self.grid.lons_sorted
                self.masked_lons = sorted_lons[self.lon_mask]                  # Longitude array within the bounding box range
            else:                                                              # For curvilinear grids:
                self.masked_points = np.column_stack((                         # Store the masked points within the bounding box
                    np.radians(self.grid.lats.ravel())[self.combined_mask],
                    np.radians(self.grid.lons.ravel())[self.combined_mask]
                ))
            
    # Public interface______________________________________________________

    # 1. Setter

    def set(self, lat_min=None, lat_max=None, lon_min=None, lon_max=None, grid: GridHandler = None):
        """
        Sets or resets the bounding box parameters based on user input and snaps them
        to the grid's coordinate nodes. This method uses the GridHandler instance to obtain
        the global coordinate arrays and normalizes the input bounds. It then builds boolean
        masks and extracts "masked" coordinate arrays (or points) that represent the local
        subset for subsequent spatial queries.

        Args:
            lat_min, lat_max (float or None): User-specified latitude bounds.
            lon_min, lon_max (float or None): User-specified longitude bounds.
            grid (GridHandler): The associated grid.

        Behavior:
            - If neither lat_min nor lat_max are provided, use the full grid latitude range.
            - If only one of lat_min or lat_max is provided, duplicate that value.
            - The same logic applies for lon_min and lon_max.
            - For rectilinear grids, the provided longitude values are normalized (via grid.normalize_longitudes)
                and then "snapped" to the nearest grid nodes.
            - For curvilinear grids, we simply check that the user bounds (after normalization) lie within the
                grid's overall domain (using np.nanmin and np.nanmax on the 2D coordinate arrays).
        
        Args:
            lat_min, lat_max (float or None): User-specified latitude bounds.
            lon_min, lon_max (float or None): User-specified longitude bounds.
            grid (GridHandler): The associated grid.
        
        Raises:
            ValueError: If grid is None or if the specified bounds are outside the grid domain.
           
        Note:
            The longitude bounds are normalized using grid.normalize_longitudes.

        After processing, the bounding box stores:
            - Snap-adjusted lat_min, lat_max, lon_min, lon_max,
            - Boolean masks (lat_mask, lon_mask) defined on the grid arrays,
            - For rectilinear grids, local coordinate arrays (masked_lats, masked_lons),
            - For curvilinear grids, a 2D array of masked points in radians.
        """
        if grid is None:
            raise ValueError("GeoBoundingBox: set: Requires a GridHandler instance.")
        self.grid = grid
        
        # Process latitude bounds:
        no_lats = lat_min is None and lat_max is None
        if no_lats:
            lat_min, lat_max = self.grid.lat_min, self.grid.lat_max
        elif lat_min is None:
            lat_min = lat_max
        elif lat_max is None:
            lat_max = lat_min
        self.lat_min, self.lat_max = sorted([lat_min, lat_max])
        if not (self.grid.lat_min <= self.lat_min <= self.grid.lat_max and
                self.grid.lat_min <= self.lat_max <= self.grid.lat_max):
            raise ValueError(f"GeoBoundingBox: set: Latitude bounds {self.lat_min}, {self.lat_max} "
                             f"must lie within [{self.grid.lat_min}, {self.grid.lat_max}]")

        # Process longitude bounds:
        no_lons = lon_min is None and lon_max is None
        if no_lons:
            lon_min, lon_max = self.grid.lon_min, self.grid.lon_max
        elif lon_min is not None:
            lon_min = self.grid.normalize_longitudes(lon_min)
            if lon_max is not None:
                lon_max = self.grid.normalize_longitudes(lon_max)
            else:
                lon_max = lon_min
        else:
            lon_min = lon_max = self.grid.normalize_longitudes(lon_max)
            
        self.lon_min, self.lon_max = lon_min, lon_max                          # Store the user bbox bounds
 
        if self.grid.is_rectilinear:        # For rectilinear grids, decide whether the bounds need sorting
            
            # If the physical longitude range (from west to east) is monotonic, which is true if the
            # antimeridian is not crossed, then sorth the user longitude bounds align with the grid.
            # Else, if the the antimeridian is crossed, the longitude range is "rolled" to move the
            # discontinuity to the edges and is not monotonic. In this case we do not sort the user bounds.
            if self.grid.lons_sorted is not None:                              # Signifies longitudes do not cross the antimeridian and are not rolled                
                self.lon_min, self.lon_max = sorted([self.lon_min, self.lon_max])
            if not no_lats or not no_lons:                                     # Call only if any user input
                self._snap_rectilinear_grid_bounding_box()
        else:                               # For curvilinear grids, use the overall domain of the 2D longitude array:
            if not (self.grid.lon_min <= self.lon_min <= self.grid.lon_max and
                    self.grid.lon_min <= self.lon_max <= self.grid.lon_max):
                raise ValueError(f"GeoBoundingBox: set: Longitude bounds {self.lon_min}, {self.lon_max} "
                                 f"must lie within [{self.grid.lon_min}, {self.grid.lon_max}]")
            if not no_lats or not no_lons:                                     # Call only if any user input
                self._snap_curvilinear_grid_bounding_box()
                
    # 2. Getters

    def get_masks(self):
        """
        Returns the latitude and longitude masks for the bounding box. 
        Builds them if not already set.

        Returns:
            tuple: (lat_mask, lon_mask) as numpy boolean arrays.
        """
        self._set_masks()                                                      # Build the masks is not present
        if self.grid.is_rectilinear:                                           # For rectilinear grid
            return self.masked_lats, self.masked_lons                          # Return separate 1D masks
        return self.combined_mask                                              # Else (curvilinear grid) return a flattened 2D array
    
    def get_masked_coordinates(self):
        """
        Retrieves the spatial coordinate arrays within the bounding box.

        Returns:
            tuple or np.ndarray: For rectilinear grids, (masked_lats, masked_lons);
                                 for curvilinear grids, the masked points array.

        Behavior:
        For rectilinear grids, returns separate 1D arrays (in degrees).
        For curvilinear grids, returns a 2D array of (lat, lon) pairs (in radians).

        Different interpolator conventions require different units for each case.
        """
        self._build_masked_coordinates()                                       # Build the masked coordinate arrays if not present
        if self.grid.is_rectilinear:                                           # For rectilinear grid
            return self.masked_lats, self.masked_lons                          # Return separate 1D arrays in degrees
        return self.masked_points                                              # Else (curvilinear grid) return a 2D array of lat/lon points in rad
            
    def get_info(self, verbosity=0):
        """
        Returns information about the GeoBoundingBox instance.
        
        Args:
            verbosity (int): Level of detail (0: summary, 1: detailed).
        
        Returns:
            str: A formatted string describing the bounding box, its snapped ranges, and
                associated grid information.
        """
        info_str = "GeoBoundingBox instance:\n"
        info_str += f"  Snapped Latitude Range: [{self.lat_min}, {self.lat_max}]\n"
        info_str += f"  Snapped Longitude Range: [{self.lon_min}, {self.lon_max}]\n"
        grid_type = "Rectilinear" if self.grid.is_rectilinear else "Curvilinear"
        info_str += f"  Grid Type: {grid_type}\n"
        if verbosity > 0 and self.grid is not None:
            info_str += f"  Grid Latitude Range: [{self.grid.lat_min}, {self.grid.lat_max}]\n"
            info_str += f"  Grid Longitude Range: [{self.grid.lon_min}, {self.grid.lon_max}]\n"
            if self.grid.is_rectilinear:
                if self.masked_lats is not None and self.masked_lons is not None:
                    info_str += f"  Masked Latitudes shape: {self.masked_lats.shape}\n"
                    info_str += f"  Masked Longitudes shape: {self.masked_lons.shape}\n"
            else:
                if self.masked_points is not None:
                    info_str += f"  Masked Points shape: {self.masked_points.shape} (in radians)\n"
        return info_str
    
    # 3. Containment check

    def contains(self, lat, lon):
        """
        Determines whether a given point (lat, lon) lies within the bounding box.

        Args:
            lat (float): Latitude in degrees
            lon (float): Longitude in degrees

        Returns:
            bool: True if the point is inside the bounding box, else False.
        """
        if self.lat_min <= lat <= self.lat_max:
            norm_lon = self.grid.normalize_longitudes(lon)
            if self.lon_min <= self.lon_max:
                return self.lon_min <= norm_lon <= self.lon_max
            return (norm_lon >= self.lon_min or norm_lon <= self.lon_max)      # Wrap-around case
        return False

#______________________________________________________________________________
class SpatialQuery:
    """
    Handles geographic queries on a dataset within a specified bounding box.

    This class provides methods for:
        - Generating boolean masks for grid points within a bounding box.
        - Subsetting data based on coordinates, time, and other dimensions.
        - Creating interpolator functions for efficient data retrieval.
        - Retrieving data values at arbitrary coordinates using interpolation.
    """
    def __init__(self, var_name, bbox : GeoBoundingBox):                       # Class constructor
        """
        Initializes SpatialQuery with a variable name and a geographic bounding box.
        
        Args:
            var_name (str): Name of the variable to query.
            bbox (GeoBoundingBox): The geographic bounding box defining the query region.
        """
        self.set(var_name, bbox)                                               # Set the instance attributes
        self.bbox._build_masked_coordinates()                                  # Build bounding box masks and spatial arrays

        
    # Private (internal methods)____________________________________________

    # 1. Initialization

    def _init_state(self):                                                     # Reset the instance attributes
        self.bbox = None                                                       # Initialize the bounding box
        self.data_var = None                                                   # Initialize the data variable
        self.ex_ante_order = None                                              # Placeholder for coordinate positions before slicing
        self.ex_post_order = None                                              # Placeholder for coordinate positions after slicing
        self.time_selector = None                                              # Placeholder for time index array
        self.active_time_idx = None                                            # Placeholder for active interpolator time index
        self.low_curvilinear_precision = True                                  # Curvilinear grids only: set interpolator precision (default low)
        self.interpolator = None                                               # Initialize an interpolator
        self.data_slice = None                                                 # Placeholder for the sliced data
        
    # 2. Validation halpers

    def _is_ready(self):
        """
        Checks if the SpatialQuery instance is ready for data retrieval.

        Returns:
            bool: True if the latitude mask, longitude mask, and data variable are set, False otherwise.
        """
        return not (self.data_var is None or self.bbox is None)
    
    def _validate_time_selector(self, time_selector):
        """
        Validates the time selector input.
        Parameter:
            - time_selector (int or NDArray[int]): The new time selector.

        If a single int index: Convert to a 1D Numpy array to preserve the time dimension, and
                               set the active time index to it (no ambiguity for single index)
        If a Numpy int array: Reset the active time index as the previous one is invalidated.
        
        Updates are performed only if the new and the cached time selectors differ.        
        """
        if time_selector is not None:
            new_active_time_index = None                                       # Placeholder for new active time index
            if is_int(time_selector):                                          # Input time selector is int
                new_active_time_index = time_selector                          # For single index, also set the active time index
                time_selector = np.atleast_1d(time_selector)                   # Recast to 1d Numpy array to preserve time dimension
            elif not is_int_array(time_selector):                              # If not int or Numpy array it is unsupported
                raise TypeError(f"SpatialQuery: validate_time_selector: Unsupported time_selector type, must be 'int' or 'NDArray[intp]'.")
            if not np.array_equal(time_selector, self.time_selector):          # Input differs from currecached time selectornt
                self.time_selector = time_selector                             # Update the cached time selector
                self.active_time_idx = new_active_time_index                   # Reset the active time index
        elif self.time_selector is None:                                       # Ensure cached selector exists if no input
            raise ValueError(f"SpatialQuery: validate_time_selector: Provide time_selector input to proceed.")
        else:                                                                  # Using the cached time selector
            time_selector = self.time_selector
        return time_selector                                                   # Time selector to use

    def _validate_time_index(self, time_idx):
        """
        Ensures a time index is within the range of the intrinsic time selector.
        
        If the time index is managed externally by a netcdf_temporal_subsetting class 
        instance, this validation check is unecessary.

        Args:
            time_idx (int): Time index to use in the interpolator.

        Raises:
            ValueError or TypeError: If the provided time index is not a supported type 
                                     or is inconsistent with the intrinsic time selector.
        """
        if not is_int(time_idx):
           raise TypeError("SpatialQuery: _validate_time_index: The provided time index must be of type int or np.integer.")            
        if self.time_selector is None:
            raise ValueError("SpatialQuery: _validate_time_index: Cannot validate time_index; time_selector not set.")
        if not bool(np.isin(time_idx, self.time_selector).item()):
            raise ValueError(
                f"SpatialQuery: _validate_time_index: The time index {time_idx} provided for "
                f"the interpolator is not included in the intrinsic time index array."
            )

    # 3. Dimension management
            
    def _set_dim_order(self, var_name):
        """
        Determines the order (position) for all the dimensions defined for a given variable.
        It uses the variable's own dimension tuple and first attempts to determine well-known roles
        (time, lat, lon, vertical) using CF attributes (e.g. 'standard_name' and 'axis'). For any
        missing roles, it falls back to name-based matching using a set of candidate substrings.
        
        Any dimensions that cannot be assigned one of the expected roles are grouped into the
        "other" category. If no extra dimensions are detected, the "other" key is omitted.
        
        Args:
            var_name (str): The name of the variable whose dimension order is to be determined.
        
        Returns:
            dict: A dictionary mapping each recognized role to its index in the variable's dimension tuple.
                For example: {'time': 0, 'lat': 1, 'lon': 2} or, if there are extra dimensions,
                {'time': 0, 'lat': 1, 'lon': 2, 'vertical': 3, 'other': [('foo', 4)]}.
        
        Raises:
            ValueError: If the variable is not found in the dataset or if any of the required
                        dimensions ('time', 'lat', 'lon') cannot be identified.
        """
        # Validate that the variable exists.
        dataset = self.bbox.grid.dataset
        if var_name not in dataset.variables:
            raise ValueError(f"SpatialQuery: _set_dim_order: Variable '{var_name}' not found in dataset")
        var = dataset.variables[var_name]
        dims = list(var.dimensions)  # Retrieve the dimension names as defined for this variable.
        
        # Expected roles with candidate substrings.
        expected_roles = {
            'time': ['time'],
            'lat': ['lat', 'latitude', 'y'],
            'lon': ['lon', 'longitude', 'x'],
            'vertical': ['alt', 'altitude', 'depth', 'height', 'z']
        }
        
        # Initialize the mapping for roles.
        role_map = {}
        assigned = set()
        
        # Phase 1: Use CF attributes (standard_name and axis) for high-confidence matching.
        for i, dim_name in enumerate(dims):
            try:
                dim_var = dataset.variables[dim_name]
            except KeyError:
                continue
            std_name = getattr(dim_var, 'standard_name', '').lower()
            axis = getattr(dim_var, 'axis', '').lower()
            
            # Look for each expected role.
            if ('time' not in role_map) and (std_name == 'time' or axis == 't'):
                role_map['time'] = i
                assigned.add(dim_name)
            elif ('lat' not in role_map) and (std_name in ('latitude', 'lat') or axis == 'y'):
                role_map['lat'] = i
                assigned.add(dim_name)
            elif ('lon' not in role_map) and (std_name in ('longitude', 'lon') or axis == 'x'):
                role_map['lon'] = i
                assigned.add(dim_name)
            elif ('vertical' not in role_map) and (axis == 'z' or any(p in std_name for p in ['alt', 'depth', 'height'])):
                role_map['vertical'] = i
                assigned.add(dim_name)
        
        # Phase 2: For any role not yet assigned, try name-based matching.
        for role, patterns in expected_roles.items():
            if role in role_map:
                continue
            for i, dim_name in enumerate(dims):
                if dim_name in assigned:
                    continue
                lname = dim_name.lower()
                if any(pattern in lname for pattern in patterns):
                    role_map[role] = i
                    assigned.add(dim_name)
                    break
        
        # Ensure we have at least time, lat, and lon.
        for req in ['time', 'lat', 'lon']:
            if req not in role_map:
                raise ValueError(f"SpatialQuery: _set_dim_order: Could not determine dimension for '{req}'")
        
        # Phase 3: Collect any dimensions that were not assigned.
        others = []
        for i, dim_name in enumerate(dims):
            if dim_name not in assigned:
                others.append((dim_name, i))
        
        # Only include 'other' if any unassigned dimensions exist.
        if others:
            role_map['other'] = others

        # To reflect the variable's actual order, reorder the dictionary by the integer indices.
        role_map = dict(sorted(role_map.items(), key=lambda item: (item[1] if item[0] != 'other' else float('inf'))))
        
        self.ex_ante_order = role_map.copy()
        self.ex_post_order = role_map.copy()
        return role_map
       
    def _update_dim_order(self, slices):
        """
        Update the current (post-slicing) dimension order.
        
        Args:
            slices (list): The list of slices applied to the original array.
            
        Updates:
            self.ex_post_order: A list of dimension names corresponding to the dimensions
                                that remain after the slicing operation.
        """
        # Start with the original ex_ante_order dimensions.
        original_dims = list(self.ex_ante_order.keys())

        # The new dimension order will only include dimensions that were not removed by slicing.
        # We assume that if a slice is an integer, that dimension has been removed.
        kept_dims = [dim for i, dim in enumerate(original_dims) if not is_int(slices[i])]
        
        # Assign new indices based on their order in the kept dimensions
        self.ex_post_order = {dim: idx for idx, dim in enumerate(kept_dims)}
               
    def _transpose_spatial_dims(self, data):
        """
        Reorder the variable data so that the spatial dimensions (lat, lon)
        are contiguous, in this order, at the end.
        
        Spatial slicing for curvilinear grids is applied via a combined
        2D mask requiring for (lat, lon) to be contiguous.
        
        Returns:
            np.ndarray: The data with spatial dimensions moved to the end.
        """
        lat_pos = self.ex_post_order.get('lat')                                # Get the current latitude dimension position
        lon_pos = self.ex_post_order.get('lon')                                # Get the current longitude dimension position
        if lat_pos is None or lon_pos is None:                                 # Required dimensions missing
            raise ValueError(f"SpatialQuery: _transpose_spatial_dims: Spatial dimensions have been sliced out.")
        if not (lat_pos == data.ndim-2 and lon_pos == data.ndim-1):            # Only transpose if lat/lon aren't last two dimensions
            all_axes = range(data.ndim)                                        # Index list of variable dimensions
            spatial_axes = [lat_pos, lon_pos]                                  # List of latitude and longitude positions
            new_order = [i for i in all_axes if i not in spatial_axes]         # Build index list of axes other than lat and lon
            new_order += spatial_axes                                          # Build new order: first non-spatial, then spatial.
            data = np.transpose(data, axes=new_order)                          # Transpose data in desired order
            # Update ex_post_order to reflect new positions
            self.ex_post_order['lat'] = data.ndim - 2
            self.ex_post_order['lon'] = data.ndim - 1
        return data

    def _update_dim_order_after_flattening(self, data):
        """
        Update the internal dimension order to reflect that the spatial dimensions have been
        combined (flattened). This function should be called after spatial flattening in set_sliced_data.
        
        Args:
            data (np.ndarray): The sliced and flattened data array.
        """
        non_spatial_dims = [dim for dim in self.ex_post_order if dim not in ['lat', 'lon']] # Ordered non-spatial dims
        new_order = {dim: i for i, dim in enumerate(non_spatial_dims)}                      # Ordered and re-indexed non-spatial dims
        new_order['spatial'] = len(non_spatial_dims)                                        # Combined spatial dim after flattening
        self.ex_post_order = new_order                                                      # Updated internal mapping
        
    # 4. Subsetting operations
    
    def _set_other_slices(self, slices, **dim_slices):
        """
        Sets up slices for dimensions other than latitude and longitude,
        if passed (optinally) in **dim_slices.
        """
        retained_dim = 0                                                       # Initialize number of retained dimensions
        for dim_name, selector in dim_slices.items():                          # Iterate over the additional slices
            if dim_name in self.ex_post_order:                                 # Verify slicing is over a dataset dimension
                if dim_name not in [self.bbox.grid.lat_var.name,               # Skip latitude and longitude if included
                                    self.bbox.grid.lon_var.name]:
                    if not is_int(selector):                                   # The selector is not an integer index
                        if not is_int_array(selector):                         # The selector is not a Numpy integer array either
                            raise TypeError(f"SpatialQuery: _set_other_slices: The selector for '{dim_name}' must be int or NDArray[np.integer].")
                        retained_dim += 1                                      # If an array is used retain the respective dimension
                    slices[self.ex_post_order[dim_name]] = selector            # Set the slices for additional dimensions
            else:
                valid_dims = list(self.ex_post_order.keys())                   # List of available dimensions
                raise ValueError(f"SpatialQuery: _set_other_slices: Invalid dimension '{dim_name}'. Valid dimensions: {valid_dims}")
        return retained_dim                                                    # Return the number of retained dimensions after slicing
    
    def _apply_combined_mask(self, data):
        """
        Apply the 2D combined lat and lon mask (for curvilinear grids).

        Args:
            data (np.ndarray): Sliced data.
            lat_mask, lon_mask (np.ndarray): 1D boolean mask arrays.
        
        Returns:
            np.ndarray: Data reshaped to separate spatial dimensions rather than as a flattened vector.
        """
        data = self._transpose_spatial_dims(data)                              # Ensure lat, lon are at the end in this order
        non_spatial_shape = data.shape[:-2]                                    # Capture non-spatial dimensions to retain
        data_flat = data.reshape(*non_spatial_shape, -1)                       # Recast to: (*non_spatial_shape, n_lat * n_lon)
        data = data_flat[..., self.bbox.combined_mask]                         # Apply combined lat/lon mask to the spatial axis
        self._update_dim_order_after_flattening(data)                          # Final updating of dimensions after lat/lon collapse to 'spatial'
        return data                                                            # return the updated data array
    
    # 5. Internal setters
    
    def _set_time_index(self, time_idx, validate = False):
        """
        Sets the active time index if different from the cached value.
        If the cached time index is updated, the cahed interpolator,
        which is specific to a time-index, is reset to None.

        Args:
            time_idx (int): The time index for a data variable snapshot.
            validate (bool): Verify time_idx is consistent with time_selector
            
        No validation needed if time is managed by netcdf_tamporal_subsetting
        """
        if time_idx is None:
            if self.active_time_idx is None:
                raise ValueError(f"SpatialQuery: _set_time_index: Active time index not set; call with a valid time index.")
        elif time_idx != self.active_time_idx:
            if validate:                                                       # Check is time_idx is consistent with time_selector
                self._validate_time_index(time_idx)

            self.interpolator = None                                           # Reset the interpolator (specific to a time index)
            self.active_time_idx = time_idx                                    # Update the active time index
             
            
    def _set_interpolator(self):
        """
        Create an interpolator function for the data variable for a single time snapshot.
        This method expects that the data_slice (obtained via set_sliced_data) contains a
        time dimension of length 1. It then squeezes the time dimension so that:
          - For rectilinear grids, the resulting array is 2D (lat, lon).
          - For curvilinear grids, the resulting array is 1D (flattened spatial data).
        
        Returns:
            function: An interpolator function that accepts a (lat, lon) coordinate pair.
        
        For rectilinear grids, it uses RegularGridInterpolator (with masked_lats and masked_lons).
        For curvilinear grids, it uses NearestNDInterpolator (with masked_points).

        Raises:
            ValueError: If data_slice is not set, active_time_idx is not set, or if the data_slice
                        does not collapse correctly to the expected dimensionality.

        """
        single_slice = self.get_snapshot()                                     # Get snapshot at active_time_idx

        # Create and return the appropriate interpolator.
        try:
            if self.bbox.grid.is_rectilinear:                                  # For rectilinear grids, self.lats and self.lons are 1D.
                if single_slice.ndim != 2:
                    raise ValueError(f"SpatialQuery: _set_interpolator: For rectilinear grid, expected 2D data but got {single_slice.ndim}D data.")
                interpolator = RegularGridInterpolator(                        # Transpose data if dimensions are (lat, lon)
                    (self.bbox.masked_lats, self.bbox.masked_lons), 
                    single_slice,                                              # Enforce (lat, lon) order for the interpolator
                    bounds_error=True,
                    fill_value=np.nan
                )
            else:                                                              # For curvilinear grids, use the 2D coordinate arrays.
                if single_slice.ndim != 1:
                    raise ValueError(f"SpatialQuery: _set_interpolator: For curvilinear grid, expected 1D data but got {single_slice.ndim}D data.")
                interpolator = NearestNDInterpolator(
                    self.bbox.masked_points,                                   # Subsetted grid points
                    single_slice                                               # Already subsetted data (1D)
                )
        except Exception as e:
            raise type(e)(f"SpatialQuery: _set_interpolator: Failed to set the interpolator\n   {e}")
        
        return interpolator
    
    # 5. Interpolation
           
    def _interpolate(self, lat, lon, method='nearest'):
        """
        Performs interpolation to retrieve a value at a given latitude and longitude,
        at the point in time corresponding to the cached active time index.

        Args:
            lat (float): Latitude coordinate in degrees.
            lon (float): Longitude coordinate in degrees.
            method (str, optional): Interpolation method ('nearest' or 'linear'). Defaults to 'nearest'.

        Returns:
            float: Interpolated data value.

        Raises:
            ValueError: If an invalid interpolation method is specified for curvilinear grids, or if an error occurs during interpolation.
        """
        uses_interpolator = self.bbox.grid.is_rectilinear or self.low_curvilinear_precision
        lon_norm = self.bbox.grid.normalize_longitudes(lon)
        
        try:
            if uses_interpolator:
                if self.interpolator is None:                                  # No interpolator present
                    self.interpolator = self._set_interpolator()               # Create and cache interpolator to use

                return self.interpolator(
                    # For rectilinear grids, the interpolator was built with masked_lats and masked_lons in degrees
                    np.array([lat, lon_norm]) if self.bbox.grid.is_rectilinear
                    
                    # For curvilinear grids, the interpolator was built using points in radians
                    else np.array([radians(lat), radians(lon_norm)])
                )
            elif method in ['nearest', 'linear']:                               # Check method label for curvilinear grids
                # For the non-cached (on-the-fly) method for curvilinear grids, use griddata. This
                # method first constructs a Delaunay triangulation and then interpolates. It is not
                # amenable to caching. While smoother and more accurate, it is computationally expensive.
                return griddata(self.bbox.masked_points, self.get_snapshot(), (radians(lat), radians(lon_norm)), method=method)
            raise ValueError(f"SpatialQuery: _interpolate: Call with a time index to set up an Interpolator")

        except Exception as e:
            raise RuntimeError(f"SpatialQuery: _interpolate: Error during interpolation: {e}")
            
    # Public interface______________________________________________________

    # 1. Setters

    def set(self, var_name, bbox : GeoBoundingBox):                            # Sets or resets a class instance
        """
        Sets or resets the SpatialQuery instance with a new variable name and bounding box.

        This method initializes or resets all internal attributes, validates the input,
        determines the dimension order of the data variable, and creates spatial masks.

        Args:
            var_name (str): Name of the variable to query.
            bbox (GeoBoundingBox): The geographic bounding box defining the query region.

        Raises:
            ValueError: If the bounding box is invalid or the variable name is not found in the dataset.
        """
        self._init_state()                                                     # Reset attributes
        if not isinstance(bbox, GeoBoundingBox):
            raise ValueError(f"SpatialQuery: set: Invalid bounding box")
        if not is_observable(bbox.grid.dataset, var_name):                     # Validate data variable
            raise ValueError(f"SpatialQuery: set: Invalid variable name {var_name}")
        self.bbox = bbox                                                       # Set the bounding box
        self.data_var = bbox.grid.dataset.variables[var_name]                  # Set the data variable for tne analysis
        self._set_dim_order(var_name = var_name)                               # Detect the order of the variable dimensions
        
    # 2. Validators
    
    def are_lat_lon_contiguous(self):
        """
        Returns True if the positions of the latitude and longitude coordinates
        are contiguous in the variable of interest, else False.
        
        This is of relevance for curvilinear grids, because slicing in the
        latitude and longitude dimensions is applied via a vombined index,
        requiring contiguity.
        """
        lat_idx = self.ex_post_order['lat']
        lon_idx = self.ex_post_order['lon']
        return bool(abs(lat_idx - lon_idx) == 1)
    
    # 3. Setters

    def set_sliced_data(self, time_selector=None, **dim_slices):
        """
        Derives a subset of the data variable based on a time selector and spatial masks derived
        from a bounding box. The method builds slices for all dimensions (time plus any additional
        dimensions specified via dim_slices) and applies spatial masking for rectilinear grids.
        For curvilinear grids, spatial slicing is applied via a combined mask that collapses the
        spatial dimensions into one.

        Args:
            time_selector (int or numpy.ndarray): A global time index (or array of indices). The
                method forces this to be a NumPy array to preserve the time dimension.
            **dim_slices: Additional slices for other dimensions (for example, depth=0).

        Sets:
            self.data_slice: The sliced data array. For a single time index in a rectilinear grid,
            data_slice has shape (time, lat, lon) (with time preserved as a singleton dimension),
            and further processing (in _set_interpolator) will squeeze the time axis.
            For a curvilinear grid, after applying the combined mask, data_slice is reshaped to
            have one (flattened) spatial dimension.

        Raises:
            ValueError, IndexError, or TypeError if inputs are invalid or if the resulting
            dimensionality of the data_slice is not as expected.

        Note:
            This method relies on the bounding box having built its masks and masked coordinates.
        """
        # Verify spatial configuration
        if not self._is_ready():
            raise ValueError("SpatialQuery: set_sliced_data: Instance not ready for data retrieval.")
        time_selector = self._validate_time_selector(time_selector)            # Validate the time selector to use
        
        # Initialize slices and the time axis
        slices = [slice(None)] * self.data_var.ndim                            # Initialize slice list for all dimensions
        time_axis = self.ex_post_order['time']                                 # Identify time, lat, and lon positions
        slices[time_axis] = time_selector                                      # Set the time slice
        
        # Slicing by an index array retains the respective dimension,
        # whereas slicing by a single integer index eliminates it.
        retained_dim = not is_int(time_selector)                               # Using Numpy array for time retains the dimensionality
        retained_dim += self._set_other_slices(slices, **dim_slices)           # Set masks for other dimensions and track retained

        if self.bbox.grid.is_rectilinear:                                      # For rectilinear grids:
            try:                                                               # Attempt to set up the slices
                lat_axis = self.ex_post_order['lat']                           # Position of latitude in variable coordinates
                lon_axis = self.ex_post_order['lon']                           # Position of longitude in variable coordinates
                slices[lat_axis] = self.bbox.lat_mask                          # Set separate 1D lat/lon slices
                slices[lon_axis] = self.bbox.lon_mask
            except IndexError:                                                 # If indexing is off
                raise IndexError("SpatialQuery: set_sliced_data: Spatial indices out of range.")

        # Execute pre-slicing, including spatial for rectilinear grids.
        # For curvilinear grids, spatial slicing is applied later.
        data = self.data_var[tuple(slices)]                                    # Apply partial slicing
        self._update_dim_order(slices)                                         # Update the dimension positions post-slicing

        # Verify dimensionality is as expected
        expected_ndim = 2 + retained_dim                                       # Expected dimensionality based on slicing
        if data.ndim != expected_ndim:                                         # Verify dimensionality is as expected
            raise ValueError(f"SpatialQuery: set_sliced_data: Expected {expected_ndim}D data after slicing, but got {data.ndim} dimensions.")
        
        # Post-process if curvilinear grid
        if not self.bbox.grid.is_rectilinear:                                  # Grid is curvilkinear
            data = self._apply_combined_mask(data)                             # Combined lat/lon into 2D mask, and apply
            if data.ndim != expected_ndim - 1:                                 # Verify dimensionality is as expected
                raise ValueError(f"SpatialQuery: set_sliced_data: For curvilinear grid expected {expected_ndim - 1}D data, got {data.ndim} dimensions.")

        # Replace masked values with NaN if applicable
        if hasattr(data, 'mask') and isinstance(data.mask, np.ndarray) and np.any(data.mask): # Determine if data containes masked entries
            data = np.ma.filled(data, np.nan)                                  # If so replace by NaN

        self.interpolator = None                                               # Reset any cached interpolator
        self.data_slice = data                                                 # rectilinear: (lat, lon) or (time, lat, lon); curvilinear: spatial slices

    # 3. Getters

    def get_snapshot(self, time_idx = None, validate = False):
        """
        Returns a snapshot of the data variable for a single time index.

        Expects the time dimension of data_slice (created by set_sliced_data) to be
        at least of length 1. It then retrieves the data at the requested time
        index and squeezes the data to collapse the time dimension, so that:
          - For rectilinear grids, the snapshot is 2D in spatial dimensions (lat, lon).
          - For curvilinear grids, the snapshot is 1D in spatial dimensions (flattened lat, lon).
        
        Args:
            time_idx (int): The time index for the snapshot
            validate (bool): Verify time_idx is consistent with time_selector

        Returns:
            single_slice (np.ndarray): The variable snapshot at time_idx
        
        Raises:
            ValueError: If data_slice is not set, active_time_idx is not set, or if the data_slice
                        does not collapse correctly to the expected time dimensionality.
        """
        if self.data_slice is None or len(self.data_slice) == 0:
            raise ValueError("SpatialQuery: get_snapshot: data_slice is not set.")
        if time_idx is not None:
            self._set_time_index(time_idx, validate)                           # Prepare for interpolations
        if self.active_time_idx is None:                                       # Extract the active time-index slice 
            raise ValueError("SpatialQuery: get_snapshot: active_time_idx is not set.")
        try:                                                                   # Identify the time axis post-slicing
            time_axis = self.ex_post_order['time']
        except KeyError:
            raise ValueError("SpatialQuery: get_snapshot: Time axis not present in the dimension order.")
        
        time_dim = self.data_slice.shape[time_axis]                            # Time axis dimensionality of data_slice
        if time_dim >  1:                                                      # Time axis dimensionality > 1
            single_slice = np.take(self.data_slice, indices=self.active_time_idx, axis=time_axis) # Set the time
            if single_slice.shape[time_axis] != 1:                             # Ensure the time axis has length 1.
                raise ValueError("SpatialQuery: get_snapshot: Expected the time axis to have length 1 after extraction.")
        elif time_dim == 0:                                                    # Time axis dimensionality 0
            raise ValueError("SpatialQuery: get_snapshot: Expected the time axis to have at least length 1 before extraction.")
        else:
            single_slice = self.data_slice                                     # Time already fixed
        return np.squeeze(single_slice, axis=time_axis)                        # Collapse the time dimension and return the snapshot

    def get_value(self, lat, lon, time_idx = None, validate = False, method='nearest'):
        """
        Retrieves the interpolated value at a specified latitude and longitude.

        Args:
            lat (float): Latitude coordinate.
            lon (float): Longitude coordinate.
            time_idx (int, optional): Time index. If None, uses the cached active time index.
            method (str, optional): Interpolation method ('nearest' or 'linear'). Defaults to 'nearest'.
            validate (bool): If True, verify time_idx is consistent with time_selector

        Returns:
            float: Interpolated data value.

        Raises:
            ValueError: If the SpatialQuery instance is not ready or if an error occurs during interpolation.
        """
        self._set_time_index(time_idx, validate)                               # Prepare for interpolations
        return self._interpolate(lat, lon, method)                             # Return interpolated value

    def get_values(self, lats, lons, time_idx=None, validate=False, method='nearest'):
        """
        Vectorized retrieval of interpolated values at multiple (lat, lon) points.

        Args:
            lats (array-like): Array of latitudes in degrees.
            lons (array-like): Array of longitudes in degrees.
            time_idx (int, optional): Time index. If None, uses cached active time index.
            method (str): For curvilinear grids without cached interpolator, either 'nearest' or 'linear'.
            validate (bool): If True, validate time_idx against time_selector.
        Returns:
            np.ndarray: Array of interpolated values, same shape as input lats/lons.
        Raises:
            RuntimeError or ValueError on interpolation or input errors.
        """
        self._set_time_index(time_idx, validate)                               # Prepare interpolator for the requested time
        uses_interp = self.bbox.grid.is_rectilinear or self.low_curvilinear_precision
        lats_arr = np.asarray(lats).ravel()                                    # Flatten inputs and normalize longitudes
        lons_norm = self.bbox.grid.normalize_longitudes(np.asarray(lons).ravel())
        try:
            if uses_interp:
                if self.interpolator is None:                                  # ensure we have a cached interpolator
                    self.interpolator = self._set_interpolator()
                if not self.bbox.grid.is_rectilinear:                          # curvilinear, low‐precision nearest
                    lats_arr = np.radians(lats_arr)                            # form the query points in radians
                    lons_norm = np.radians(lons_norm)
                pts = np.column_stack((lats_arr, lons_norm))                   # build (N,2) query array
                vals = self.interpolator(pts)
            else:                                                              # on-the-fly griddata for curvilinear high-precision
                snapshot = self.get_snapshot(time_idx, validate)               # get a 1-D array by collapsing the singleton time axis
                pts = (np.radians(lats_arr), np.radians(lons_norm))            # build the query pts
                vals = griddata(                                               # call griddata with snapshot
                    self.bbox.masked_points,
                    snapshot,
                    pts,
                    method=method
                )
        except Exception as e:
            raise RuntimeError(f"SpatialQuery: get_values: interpolation failed: {e}")
        return np.reshape(vals, np.shape(lats))                               # Restore original shape


    def get_pixel_value(self, lat_idx, lon_idx, data):
        """
        Retrieves the value at original grid indices (lat_idx, lon_idx) for both
        rectilinear and curvilinear grids.
        
        Args:
            lat_idx (int): Original latitude or y index in the full grid.
            lon_idx (int): Original longitude or x index in the full grid.
            data (np.ndarray): Subsetted data from `data_slice` or a snapshot.
        
        Returns:
            Union[float, np.ndarray, None]: 
                - `float` if `data` is a snapshot (single time step).
                - `np.ndarray` if `data` has a time dimension.
                - `None` if the pixel is not in the subset.
        """
        val = None                                                              # Initialize pixel value
        if self.bbox.grid.is_rectilinear:                                       # For rectilinear grids     
            # Check if indices are within subset
            in_lat = self.bbox.lat_mask[lat_idx] if lat_idx < len(self.bbox.lat_mask) else False
            in_lon = self.bbox.lon_mask[lon_idx] if lon_idx < len(self.bbox.lon_mask) else False
            if in_lat and in_lon:                                              # If indices in range find positions in data
                lat_pos = np.where(self.bbox.lat_mask)[0].tolist().index(lat_idx)
                lon_pos = np.where(self.bbox.lon_mask)[0].tolist().index(lon_idx)
                val = data[..., lat_pos, lon_pos]                              # Set the rectilinear pixel value
        else:                                                                  # For curvilinear grids
            # Calculate flat index and check if masked
            flat_idx = np.ravel_multi_index((lat_idx, lon_idx), self.bbox.grid.lats.shape)
            if flat_idx in self.bbox.combined_mask:                            # If in range
                pos = np.where(self.bbox.combined_mask == flat_idx)[0][0]      # Find position in subsetted data
                val = data[..., pos]                                           # Set the curvilinear pixel value
        return val                                                             # Return the pixel value

    def reshape_to_spatial_grid(self, data):
        """
        Reshapes curvilinear data (1D or 2D) into a 2D/3D array matching the original grid's
        spatial dimensions. Unmasked points are filled with `np.nan`.
        
        Args:
            data (np.ndarray): Subsetted data from `data_slice` (shape: `(time, num_points)`) 
                               or a snapshot (shape: `(num_points,)`).
        Returns:
            np.ndarray: 
                - If `data` is 1D: 2D array of shape `(y_dim, x_dim)` with values at masked points.
                - If `data` is 2D: 3D array of shape `(time, y_dim, x_dim)`.
        """
        if self.bbox.grid.is_rectilinear:
            raise ValueError("SpatialQuery: reshape_to_spatial_grid: Use direct indexing for "
                             "rectilinear grids; this method is for curvilinear grids only.")
        
        # Get original grid shape and initialize output with NaNs
        grid_shape = self.bbox.grid.lats.shape
        if data.ndim == 1:
            output = np.full(grid_shape, np.nan, dtype=data.dtype)
        else:
            output = np.full((data.shape[0], *grid_shape), np.nan, dtype=data.dtype)
        
        # Convert flat indices to 2D grid indices
        y_indices, x_indices = np.unravel_index(self.bbox.combined_mask, grid_shape)
        
        # Fill values
        if data.ndim == 1:
            output[y_indices, x_indices] = data
        else:
            output[:, y_indices, x_indices] = data
        
        return output

    def get_info(self, verbosity=0):
        """
        Returns information about the SpatialQuery instance.
        
        Args:
            verbosity (int): Level of detail (0: summary, 1: detailed).
        
        Returns:
            str: A formatted string with information about the spatial query attributes, including the 
                 variable name, bounding box details, dimension order, and current subsetting state.
        """
        info_str = f"SpatialQuery instance:\n"
        if self.data_var is not None:
            info_str += f"  Variable: {self.data_var.name}\n"
        else:
            info_str += "  Variable: Not set\n"
        if self.bbox is not None:
            info_str += (f"  Bounding Box: lat[{self.bbox.lat_min}, {self.bbox.lat_max}], "
                         f"lon[{self.bbox.lon_min}, {self.bbox.lon_max}]\n")
        else:
            info_str += "  Bounding Box: Not set\n"
        if self.time_selector is not None:
            info_str += f"  Time selector: Type ({type(self.time_selector)})\n"
        else:
            info_str += f"  Time selector: Not set\n"
        if self.active_time_idx is not None:
            info_str += f"  Active time index: ({self.active_time_idx})\n"
        else:
            info_str += f"  Active time index: Not set\n"

        if verbosity == 1:
            info_str += f"  Initial Dimension Order: {self.ex_ante_order}\n"
            info_str += f"  Final Dimension Order: {self.ex_post_order}\n"
            if self.time_selector is not None:
                if is_int(self.time_selector) or len(self.time_selector) <= 6:
                    info_str += f"  Time selector: {self.time_selector}\n"
                else:
                    info_str += f"  Time selector: [{self.time_selector[0]}, \
                        {self.time_selector[1]}, ..., {self.time_selector[-2]}, {self.time_selector[-1]}]\n"
            grid_type = 'Rectilinear' if self.bbox.grid.is_rectilinear else 'Curvilinear'
            info_str += f"  Grid type: {grid_type}\n"
            if not self.bbox.grid.is_rectilinear:
                info_str += f"  Interpolator Low Precision flag: {self.low_curvilinear_precision}\n"
            if self.data_slice is not None:
                info_str += f"  Data Slice shape: {self.data_slice.shape}\n"
            interpolator_state = "Not set\n" if self.interpolator is None else f"Set, of type {type(self.interpolator)}\n"
            info_str += f"  Interpolator: {interpolator_state}\n"

        return info_str