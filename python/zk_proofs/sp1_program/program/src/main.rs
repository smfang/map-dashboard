use sp1_sdk::{SP1PublicValues, SP1Stdin, SP1Stdout};

// SP1 program that will be proven
// This is the actual program that gets compiled to RISC-V and proven

#[derive(Debug, Clone)]
struct CarbonIndexResult {
    nhi_score: f64,
    p20_percentile: f64,
    p90_percentile: f64,
    gamma_shape: f64,
    gamma_scale: f64,
    gamma_loc: f64,
    carbon_index_value: u64,
}

fn main() {
    // Read input data
    let mut stdin = SP1Stdin::new();
    let rainfall_data: Vec<f64> = stdin.read();
    let current_rainfall: f64 = stdin.read();
    let lat_min: f64 = stdin.read();
    let lat_max: f64 = stdin.read();
    let lon_min: f64 = stdin.read();
    let lon_max: f64 = stdin.read();
    let timestamp: u64 = stdin.read();

    // Execute the carbon index calculation
    let result = calculate_carbon_index(&rainfall_data, current_rainfall);
    
    // Write outputs
    let mut stdout = SP1Stdout::new();
    stdout.write(&result.nhi_score);
    stdout.write(&result.p20_percentile);
    stdout.write(&result.p90_percentile);
    stdout.write(&result.gamma_shape);
    stdout.write(&result.gamma_scale);
    stdout.write(&result.gamma_loc);
    stdout.write(&result.carbon_index_value);
    stdout.write(&timestamp);
    stdout.write(&lat_min);
    stdout.write(&lat_max);
    stdout.write(&lon_min);
    stdout.write(&lon_max);
}

fn calculate_carbon_index(rainfall_data: &[f64], current_rainfall: f64) -> CarbonIndexResult {
    // Ensure we have enough data points
    assert!(rainfall_data.len() >= 10, "Insufficient rainfall data");
    
    // Convert to array for statistical calculations
    let data_array: Vec<f64> = rainfall_data.to_vec();
    
    // Fit Gamma distribution to historical data
    let (shape, loc, scale) = fit_gamma_distribution(&data_array);
    
    // Calculate percentiles
    let p20 = gamma_percentile(0.2, shape, loc, scale);
    let p90 = gamma_percentile(0.9, shape, loc, scale);
    let pmax = data_array.iter().fold(0.0, |a, &b| a.max(b));
    
    // Calculate Natural Hazard Index (NHI)
    let nhi_score = if current_rainfall < p20 {
        1.0 - (current_rainfall / p20)
    } else if current_rainfall > p90 {
        (current_rainfall - p90) / (pmax - p90)
    } else {
        0.0
    };
    
    // Convert NHI to carbon index value (scaled by 1e18)
    let carbon_index_value = (nhi_score * 1e18) as u64;
    
    CarbonIndexResult {
        nhi_score,
        p20_percentile: p20,
        p90_percentile: p90,
        gamma_shape: shape,
        gamma_scale: scale,
        gamma_loc: loc,
        carbon_index_value,
    }
}

fn fit_gamma_distribution(data: &[f64]) -> (f64, f64, f64) {
    // Method of moments estimation for Gamma distribution
    let n = data.len() as f64;
    let mean = data.iter().sum::<f64>() / n;
    let variance = data.iter()
        .map(|x| (x - mean).powi(2))
        .sum::<f64>() / (n - 1.0);
    
    // Gamma distribution parameters
    let shape = mean.powi(2) / variance;
    let scale = variance / mean;
    let loc = 0.0; // Assuming location parameter is 0
    
    (shape, loc, scale)
}

fn gamma_percentile(percentile: f64, shape: f64, loc: f64, scale: f64) -> f64 {
    // Approximate Gamma distribution inverse CDF using Newton-Raphson method
    let mut x = shape * scale; // Start with mean
    let target = percentile;
    
    for _ in 0..100 { // Max iterations
        let cdf = gamma_cdf(x, shape, loc, scale);
        let pdf = gamma_pdf(x, shape, loc, scale);
        
        if pdf.abs() < 1e-10 {
            break;
        }
        
        let new_x = x - (cdf - target) / pdf;
        
        if (new_x - x).abs() < 1e-10 {
            break;
        }
        
        x = new_x.max(0.0); // Ensure non-negative
    }
    
    x
}

fn gamma_cdf(x: f64, shape: f64, _loc: f64, scale: f64) -> f64 {
    // Regularized incomplete gamma function approximation
    if x <= 0.0 {
        return 0.0;
    }
    
    let t = x / scale;
    let mut sum = 0.0;
    let mut term = 1.0;
    
    for k in 0..100 {
        if k > 0 {
            term *= t / (shape + k as f64 - 1.0);
        }
        sum += term;
        
        if term.abs() < 1e-10 {
            break;
        }
    }
    
    let gamma_ratio = gamma_function(shape);
    sum * (t.powf(shape) * (-t).exp()) / (gamma_ratio * scale)
}

fn gamma_pdf(x: f64, shape: f64, _loc: f64, scale: f64) -> f64 {
    if x <= 0.0 {
        return 0.0;
    }
    
    let gamma_ratio = gamma_function(shape);
    (x / scale).powf(shape - 1.0) * (-x / scale).exp() / (gamma_ratio * scale)
}

fn gamma_function(z: f64) -> f64 {
    // Stirling's approximation for Gamma function
    if z <= 0.0 {
        return 0.0;
    }
    
    let c = (2.0 * std::f64::consts::PI / z).sqrt();
    let d = (z / std::f64::consts::E).powf(z);
    c * d
}

