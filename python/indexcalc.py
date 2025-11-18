import numpy as np
import scipy.stats as stats

# Historical seasonal rainfall (mm)
rainfall_data = np.array([...])  # e.g., 20 years of July rainfall

# Fit Gamma distribution
shape, loc, scale = stats.gamma.fit(rainfall_data)

# Calculate percentiles
p20 = stats.gamma.ppf(0.2, shape, loc, scale)
p90 = stats.gamma.ppf(0.9, shape, loc, scale)
pmax = rainfall_data.max()

# Current season rainfall
X = 45  # mm

# Calculate Natural Hazard Index (NHI)
if X < p20:
    nhi = 1 - (X / p20)
elif X > p90:
    nhi = (X - p90) / (pmax - p90)
else:
    nhi = 0

print(f"NHI Score: {nhi:.2f}")
