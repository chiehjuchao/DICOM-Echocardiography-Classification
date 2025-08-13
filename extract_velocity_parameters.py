#!/usr/bin/env python3
"""
Extract Velocity Measurement Parameters from DICOM Echocardiography Images

This module extracts essential reference and scale parameters for velocity measurements
from echocardiography DICOM files, specifically targeting CW Doppler, PW Doppler, 
and Tissue Doppler images.

Integration with DICOM Classification System v2.4
"""

import os
import sys
import csv
import json
import pydicom
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# Import classification system
try:
    from dicom_echo_classifier import EchoCardiographyClassifier
except ImportError:
    print("Warning: dicom_echo_classifier.py not found. Classification integration will be limited.")
    EchoCardiographyClassifier = None


class VelocityParameterExtractor:
    """
    Extract velocity measurement parameters from Doppler DICOM echocardiography images.
    """
    
    # Target categories for velocity measurements
    VELOCITY_CATEGORIES = ['cw_doppler', 'pw_doppler', 'tissue_doppler']
    
    def __init__(self, input_dir: str, output_dir: str = None):
        """
        Initialize the velocity parameter extractor.
        
        Args:
            input_dir: Directory containing DICOM files
            output_dir: Directory to save results (default: input_dir/velocity_parameters)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "velocity_parameters"
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {}
        self.stats = {
            'total_files': 0,
            'cw_doppler_files': 0,
            'pw_doppler_files': 0,
            'tissue_doppler_files': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'files_with_velocity_params': 0,
            'spectral_doppler_regions_found': 0
        }
    
    def extract_velocity_reference_parameters(self, dicom_file_path: str) -> Optional[Dict]:
        """
        Extract essential reference and scale parameters for velocity measurements
        from echocardiography DICOM file.
        
        Args:
            dicom_file_path: Path to DICOM file
            
        Returns:
            Dictionary with velocity measurement parameters or None if extraction fails
        """
        try:
            ds = pydicom.dcmread(dicom_file_path)
            
            # Find the ultrasound regions
            ultrasound_regions = ds.get((0x0018, 0x6011))  # Sequence of Ultrasound Regions
            
            if not ultrasound_regions:
                return None
            
            # Extract parameters for each region
            regions_info = []
            spectral_doppler_regions = []
            
            for i, region in enumerate(ultrasound_regions):
                region_data_type = region.get((0x0018, 0x6014)).value if (0x0018, 0x6014) in region else None
                region_spatial_format = region.get((0x0018, 0x6012)).value if (0x0018, 0x6012) in region else None
                
                region_info = {
                    'region_index': i,
                    'data_type': region_data_type,
                    'spatial_format': region_spatial_format,
                    'region_bounds': {
                        'min_x': region.get((0x0018, 0x6018)).value if (0x0018, 0x6018) in region else None,
                        'min_y': region.get((0x0018, 0x601A)).value if (0x0018, 0x601A) in region else None,
                        'max_x': region.get((0x0018, 0x601C)).value if (0x0018, 0x601C) in region else None,
                        'max_y': region.get((0x0018, 0x601E)).value if (0x0018, 0x601E) in region else None
                    }
                }
                
                # Extract reference and scale parameters if available
                if (0x0018, 0x6020) in region:  # Reference Pixel X0
                    region_info['reference_pixel_x'] = region.get((0x0018, 0x6020)).value
                if (0x0018, 0x6022) in region:  # Reference Pixel Y0
                    region_info['reference_pixel_y'] = region.get((0x0018, 0x6022)).value
                    
                if (0x0018, 0x6028) in region:  # Reference Pixel Physical Value X
                    region_info['reference_physical_x'] = region.get((0x0018, 0x6028)).value
                if (0x0018, 0x602A) in region:  # Reference Pixel Physical Value Y
                    region_info['reference_physical_y'] = region.get((0x0018, 0x602A)).value
                    
                if (0x0018, 0x602C) in region:  # Physical Delta X
                    region_info['physical_delta_x'] = region.get((0x0018, 0x602C)).value
                if (0x0018, 0x602E) in region:  # Physical Delta Y
                    region_info['physical_delta_y'] = region.get((0x0018, 0x602E)).value
                    
                if (0x0018, 0x6024) in region:  # Physical Units X Direction
                    region_info['physical_units_x'] = region.get((0x0018, 0x6024)).value
                if (0x0018, 0x6026) in region:  # Physical Units Y Direction
                    region_info['physical_units_y'] = region.get((0x0018, 0x6026)).value
                
                # Identify region types
                if region_data_type == 1:  # Grayscale/B-mode region
                    region_info['type_description'] = 'Grayscale/B-mode Region'
                elif region_data_type == 2:  # Color Doppler
                    region_info['type_description'] = 'Color Doppler Region'
                elif region_data_type == 3:  # Spectral Doppler (PW/CW)
                    region_info['type_description'] = 'Spectral Doppler (PW/CW Velocity Data)'
                    spectral_doppler_regions.append(region_info)
                    self.stats['spectral_doppler_regions_found'] += 1
                elif region_data_type == 4:  # Alternative Spectral Doppler
                    region_info['type_description'] = 'Spectral Doppler (Alternative Format)'
                    spectral_doppler_regions.append(region_info)
                    self.stats['spectral_doppler_regions_found'] += 1
                else:
                    region_info['type_description'] = f'Unknown Type (Code: {region_data_type})'
                    
                if region_spatial_format == 1:
                    region_info['format_description'] = '2D Image Format'
                elif region_spatial_format == 3:
                    region_info['format_description'] = 'Spectral Doppler Format'
                else:
                    region_info['format_description'] = f'Unknown Format (Code: {region_spatial_format})'
                
                regions_info.append(region_info)
            
            # Create comprehensive result
            result = {
                'file_path': dicom_file_path,
                'all_regions': regions_info,
                'spectral_doppler_regions': spectral_doppler_regions,
                'has_velocity_data': len(spectral_doppler_regions) > 0,
                'image_dimensions': {
                    'rows': getattr(ds, 'Rows', 0),
                    'columns': getattr(ds, 'Columns', 0)
                },
                'modality': getattr(ds, 'Modality', ''),
                'image_type': getattr(ds, 'ImageType', [])
            }
            
            # Extract primary velocity measurement parameters from first spectral region
            if spectral_doppler_regions:
                primary_region = spectral_doppler_regions[0]
                result['primary_velocity_params'] = {
                    'reference_pixel': (
                        primary_region.get('reference_pixel_x'),
                        primary_region.get('reference_pixel_y')
                    ),
                    'reference_physical_values': (
                        primary_region.get('reference_physical_x'),
                        primary_region.get('reference_physical_y')
                    ),
                    'physical_deltas': (
                        primary_region.get('physical_delta_x'),
                        primary_region.get('physical_delta_y')
                    ),
                    'physical_units': (
                        self.get_unit_description(primary_region.get('physical_units_x')),
                        self.get_unit_description(primary_region.get('physical_units_y'))
                    ),
                    'velocity_scale_info': self._create_velocity_scale_info(primary_region)
                }
                
                result['has_valid_velocity_scale'] = self._validate_velocity_parameters(primary_region)
            else:
                result['primary_velocity_params'] = None
                result['has_valid_velocity_scale'] = False
            
            return result
            
        except Exception as e:
            print(f"Error extracting velocity parameters from {os.path.basename(dicom_file_path)}: {e}")
            return None
    
    def _create_velocity_scale_info(self, region: Dict) -> Dict:
        """
        Create comprehensive velocity scale information from region parameters.
        
        Args:
            region: Spectral Doppler region information
            
        Returns:
            Dictionary with velocity scale information
        """
        scale_info = {
            'has_velocity_scale': False,
            'velocity_per_pixel': None,
            'time_per_pixel': None,
            'reference_velocity': None,
            'velocity_unit': None,
            'time_unit': None,
            'calculation_formula': None
        }
        
        # Extract velocity scaling (Y-axis typically represents velocity)
        if (region.get('physical_delta_y') is not None and 
            region.get('reference_physical_y') is not None and
            region.get('reference_pixel_y') is not None):
            
            scale_info['has_velocity_scale'] = True
            scale_info['velocity_per_pixel'] = region['physical_delta_y']
            scale_info['reference_velocity'] = region['reference_physical_y']
            scale_info['velocity_unit'] = self.get_unit_name(region.get('physical_units_y', 7))  # Default to m/s
            
            # Create calculation formula
            ref_pixel_y = region['reference_pixel_y']
            ref_velocity = region['reference_physical_y']
            delta_y = region['physical_delta_y']
            
            scale_info['calculation_formula'] = (
                f"velocity = {ref_velocity} + (pixel_y - {ref_pixel_y}) × {delta_y} {scale_info['velocity_unit']}"
            )
        
        # Extract time scaling (X-axis typically represents time)
        if (region.get('physical_delta_x') is not None and
            region.get('reference_physical_x') is not None):
            
            scale_info['time_per_pixel'] = region['physical_delta_x']
            scale_info['time_unit'] = self.get_unit_name(region.get('physical_units_x', 4))  # Default to seconds
        
        return scale_info
    
    def _validate_velocity_parameters(self, region: Dict) -> bool:
        """
        Validate that essential velocity measurement parameters are present.
        
        Args:
            region: Spectral Doppler region information
            
        Returns:
            True if valid velocity parameters are available
        """
        # Essential parameters for velocity calculation
        required_params = [
            'reference_pixel_y',
            'physical_delta_y'
        ]
        
        # Check if all required parameters are present and not None
        has_required = all(region.get(param) is not None for param in required_params)
        
        # Reference physical Y can be 0.0, so check if it exists (even if 0)
        has_ref_physical_y = 'reference_physical_y' in region
        
        return has_required and has_ref_physical_y
    
    def get_unit_name(self, unit_code: int) -> str:
        """
        Get unit abbreviation from unit code.
        
        Args:
            unit_code: DICOM unit code
            
        Returns:
            Unit abbreviation string
        """
        units = {
            1: "units",
            2: "%", 
            3: "mm",
            4: "s",
            5: "Hz",
            6: "dB",
            7: "m/s",
            8: "m/s²"
        }
        return units.get(unit_code, "units")
    
    def get_unit_description(self, unit_code: int) -> str:
        """
        Convert unit codes to descriptions.
        
        Args:
            unit_code: DICOM unit code
            
        Returns:
            Unit description string
        """
        unit_map = {
            1: "Unspecified",
            2: "Percent", 
            3: "Millimeters",
            4: "Seconds",
            5: "Hertz",
            6: "dB",
            7: "Meters/Second",
            8: "Meters/Second²"
        }
        return f"{unit_map.get(unit_code, 'Unknown')} (Code: {unit_code})"
    
    def calculate_velocity_at_pixel(self, pixel_y: int, velocity_params: Dict) -> Tuple[float, str]:
        """
        Calculate velocity at a specific pixel Y coordinate.
        
        Args:
            pixel_y: Y coordinate of the pixel
            velocity_params: Velocity parameters from extraction
            
        Returns:
            Tuple of (velocity_value, unit)
        """
        if not velocity_params or not velocity_params.get('has_valid_velocity_scale', False):
            raise ValueError("No valid velocity parameters available")
        
        primary_params = velocity_params['primary_velocity_params']
        ref_pixel_y = primary_params['reference_pixel'][1]
        ref_velocity = primary_params['reference_physical_values'][1]
        delta_y = primary_params['physical_deltas'][1]
        
        velocity = ref_velocity + (pixel_y - ref_pixel_y) * delta_y
        unit = primary_params['velocity_scale_info']['velocity_unit']
        
        return velocity, unit
    
    def find_velocity_measurement_files(self) -> Dict[str, List[str]]:
        """
        Find all DICOM files classified as velocity measurement categories.
        
        Returns:
            Dictionary with files grouped by category
        """
        if EchoCardiographyClassifier is None:
            print("⚠️  Classification system not available. Processing all DICOM files...")
            # Fallback: find all DICOM files
            all_files = []
            for root, dirs, files in os.walk(self.input_dir):
                for file in files:
                    if file.lower().endswith('.dcm') or not '.' in file:
                        all_files.append(os.path.join(root, file))
            return {'unknown': all_files}
        
        print("🔍 Classifying DICOM files to find velocity measurement images...")
        
        # Use classifier to find target files
        classifier = EchoCardiographyClassifier(self.input_dir)
        classifier.process_directory(show_progress=True)
        
        # Group files by velocity measurement categories
        velocity_files = {category: [] for category in self.VELOCITY_CATEGORIES}
        
        for classification in classifier.classifications:
            if classification.category in self.VELOCITY_CATEGORIES:
                velocity_files[classification.category].append(classification.file_path)
        
        # Update statistics
        self.stats['cw_doppler_files'] = len(velocity_files['cw_doppler'])
        self.stats['pw_doppler_files'] = len(velocity_files['pw_doppler']) 
        self.stats['tissue_doppler_files'] = len(velocity_files['tissue_doppler'])
        
        total_velocity_files = sum(len(files) for files in velocity_files.values())
        print(f"📊 Found velocity measurement files:")
        print(f"  CW Doppler: {self.stats['cw_doppler_files']}")
        print(f"  PW Doppler: {self.stats['pw_doppler_files']}")
        print(f"  Tissue Doppler: {self.stats['tissue_doppler_files']}")
        print(f"  Total: {total_velocity_files}")
        
        return velocity_files
    
    def process_all_files(self) -> None:
        """
        Process all velocity measurement files and extract parameters.
        """
        velocity_files = self.find_velocity_measurement_files()
        
        # Flatten all velocity files
        all_velocity_files = []
        for category, files in velocity_files.items():
            all_velocity_files.extend(files)
        
        if not all_velocity_files:
            print("⚠️  No velocity measurement files found!")
            return
        
        print(f"🌊 Extracting velocity parameters from {len(all_velocity_files)} files...")
        
        for file_path in tqdm(all_velocity_files, desc="Extracting velocity params"):
            params = self.extract_velocity_reference_parameters(file_path)
            
            if params:
                # Add category information
                for category, files in velocity_files.items():
                    if file_path in files:
                        params['doppler_category'] = category
                        break
                
                self.results[file_path] = params
                self.stats['successful_extractions'] += 1
                
                if params.get('has_valid_velocity_scale', False):
                    self.stats['files_with_velocity_params'] += 1
            else:
                self.stats['failed_extractions'] += 1
        
        self.stats['total_files'] = len(all_velocity_files)
    
    def save_results(self) -> None:
        """
        Save velocity parameter extraction results to multiple formats.
        """
        if not self.results:
            print("⚠️  No results to save!")
            return
        
        print(f"💾 Saving velocity parameter results to {self.output_dir}")
        
        # 1. Save detailed JSON results
        json_file = self.output_dir / 'velocity_parameters_detailed.json'
        with open(json_file, 'w') as f:
            # Make results JSON serializable
            json_results = {}
            for file_path, params in self.results.items():
                relative_path = os.path.relpath(file_path, self.input_dir)
                json_results[relative_path] = params
            json.dump(json_results, f, indent=2, default=str)
        
        # 2. Save velocity parameters CSV
        csv_file = self.output_dir / 'velocity_measurements.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File Path', 'Doppler Category', 'Has Velocity Data', 'Has Valid Scale', 
                           'Velocity per Pixel', 'Time per Pixel', 'Reference Velocity', 'Reference Pixel X', 'Reference Pixel Y',
                           'Spectral Regions Count', 'Image Dimensions'])
            
            for file_path, params in self.results.items():
                relative_path = os.path.relpath(file_path, self.input_dir)
                primary_params = params.get('primary_velocity_params')
                
                if primary_params and primary_params['velocity_scale_info']:
                    scale_info = primary_params['velocity_scale_info']
                    velocity_per_pixel = scale_info.get('velocity_per_pixel', 'N/A')
                    time_per_pixel = scale_info.get('time_per_pixel', 'N/A')
                    reference_velocity = scale_info.get('reference_velocity', 'N/A')
                    reference_pixel = primary_params.get('reference_pixel', (None, None))
                else:
                    velocity_per_pixel = time_per_pixel = reference_velocity = 'N/A'
                    reference_pixel = (None, None)
                
                writer.writerow([
                    relative_path,
                    params.get('doppler_category', 'unknown'),
                    params.get('has_velocity_data', False),
                    params.get('has_valid_velocity_scale', False),
                    velocity_per_pixel,
                    time_per_pixel,
                    reference_velocity,
                    reference_pixel[0] if reference_pixel[0] is not None else 'N/A',
                    reference_pixel[1] if reference_pixel[1] is not None else 'N/A',
                    len(params.get('spectral_doppler_regions', [])),
                    f"{params['image_dimensions']['columns']}x{params['image_dimensions']['rows']}"
                ])
        
        # 3. Save velocity calculation reference
        calc_file = self.output_dir / 'velocity_calculation_reference.txt'
        with open(calc_file, 'w') as f:
            f.write("VELOCITY MEASUREMENT CALCULATION REFERENCE\n")
            f.write("=" * 50 + "\n\n")
            
            valid_files = [(path, params) for path, params in self.results.items() 
                         if params.get('has_valid_velocity_scale', False)]
            
            f.write(f"Files with valid velocity measurement parameters: {len(valid_files)}\n")
            f.write("-" * 50 + "\n\n")
            
            for file_path, params in valid_files:
                relative_path = os.path.relpath(file_path, self.input_dir)
                primary_params = params['primary_velocity_params']
                scale_info = primary_params['velocity_scale_info']
                
                f.write(f"File: {relative_path}\n")
                f.write(f"Category: {params.get('doppler_category', 'unknown').upper()}\n")
                f.write(f"Calculation Formula: {scale_info['calculation_formula']}\n")
                f.write(f"Velocity Scale: {scale_info['velocity_per_pixel']} {scale_info['velocity_unit']}/pixel\n")
                if scale_info.get('time_per_pixel'):
                    f.write(f"Time Scale: {scale_info['time_per_pixel']} {scale_info['time_unit']}/pixel\n")
                f.write(f"Reference Pixel X: {primary_params['reference_pixel'][0]}\n")
                f.write(f"Reference Pixel Y: {primary_params['reference_pixel'][1]}\n")
                f.write(f"Reference Velocity: {scale_info['reference_velocity']} {scale_info['velocity_unit']}\n")
                f.write("-" * 30 + "\n\n")
        
        # 4. Save velocity calculation example
        example_file = self.output_dir / 'velocity_calculation_example.py'
        with open(example_file, 'w') as f:
            f.write('''#!/usr/bin/env python3
"""
Example: How to use extracted velocity parameters for Doppler measurements

This script demonstrates how to calculate velocities from pixel coordinates
using the extracted velocity parameters from CW/PW/Tissue Doppler images.
"""

import json
import math

def load_velocity_parameters(json_file_path):
    """Load velocity parameters from JSON file"""
    with open(json_file_path, 'r') as f:
        return json.load(f)

def calculate_velocity_at_pixel(pixel_y, params):
    """
    Calculate velocity at a specific pixel Y coordinate
    
    Args:
        pixel_y: Y coordinate of the measurement pixel
        params: Velocity parameters for the image
        
    Returns:
        (velocity, unit) tuple
    """
    if not params.get('has_valid_velocity_scale', False):
        raise ValueError("No valid velocity parameters available")
    
    primary_params = params['primary_velocity_params']
    velocity_scale = primary_params['velocity_scale_info']
    
    ref_pixel_y = primary_params['reference_pixel'][1]
    ref_velocity = velocity_scale['reference_velocity']
    delta_y = velocity_scale['velocity_per_pixel']
    unit = velocity_scale['velocity_unit']
    
    velocity = ref_velocity + (pixel_y - ref_pixel_y) * delta_y
    
    return velocity, unit

def calculate_peak_velocities(spectral_trace_pixels, params):
    """
    Calculate velocities for multiple points along a spectral trace
    
    Args:
        spectral_trace_pixels: List of (x, y) pixel coordinates
        params: Velocity parameters for the image
        
    Returns:
        List of (velocity, unit) values
    """
    velocities = []
    
    for x, y in spectral_trace_pixels:
        velocity, unit = calculate_velocity_at_pixel(y, params)
        velocities.append((velocity, unit))
    
    return velocities

# Example usage
if __name__ == "__main__":
    # Load parameters
    params = load_velocity_parameters('velocity_parameters_detailed.json')
    
    # Get first file with valid velocity scale as example
    example_file = None
    example_params = None
    
    for file_path, file_params in params.items():
        if file_params.get('has_valid_velocity_scale', False):
            example_file = file_path
            example_params = file_params
            break
    
    if example_params:
        print(f"Example velocity measurement using: {example_file}")
        category = example_params.get('doppler_category', 'unknown')
        scale_info = example_params['primary_velocity_params']['velocity_scale_info']
        
        print(f"Category: {category.upper()}")
        print(f"Calculation: {scale_info['calculation_formula']}")
        
        # Example velocity calculation at specific pixels
        test_pixels = [100, 200, 300, 400]  # Y coordinates along spectral trace
        
        print(f"\\nExample velocity calculations:")
        for pixel_y in test_pixels:
            velocity, unit = calculate_velocity_at_pixel(pixel_y, example_params)
            print(f"  Pixel Y={pixel_y}: {velocity:.3f} {unit}")
        
        # Peak velocity example
        print(f"\\nPeak velocity analysis:")
        spectral_trace = [(150, 120), (200, 80), (250, 60), (300, 90)]  # Example trace points
        velocities = calculate_peak_velocities(spectral_trace, example_params)
        
        peak_velocity = max(abs(v[0]) for v in velocities)
        print(f"Peak velocity: {peak_velocity:.3f} {velocities[0][1]}")
        
    else:
        print("No files with valid velocity measurement scales found")
''')
        
        # 5. Save statistics
        stats_file = self.output_dir / 'extraction_stats.json'
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        print(f"✅ Results saved:")
        print(f"  📄 Detailed parameters: {json_file}")
        print(f"  📊 Velocity measurements CSV: {csv_file}")
        print(f"  📝 Calculation reference: {calc_file}")
        print(f"  🧮 Calculation example: {example_file}")
        print(f"  📈 Statistics: {stats_file}")
    
    def print_summary(self) -> None:
        """
        Print summary of velocity parameter extraction results.
        """
        print(f"\n🌊 Velocity Parameter Extraction Summary:")
        print(f"{'='*60}")
        print(f"CW Doppler files: {self.stats['cw_doppler_files']}")
        print(f"PW Doppler files: {self.stats['pw_doppler_files']}")
        print(f"Tissue Doppler files: {self.stats['tissue_doppler_files']}")
        print(f"Total velocity files: {self.stats['total_files']}")
        print(f"Successful parameter extractions: {self.stats['successful_extractions']}")
        print(f"Files with valid velocity scales: {self.stats['files_with_velocity_params']}")
        print(f"Spectral Doppler regions found: {self.stats['spectral_doppler_regions_found']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        
        if self.stats['successful_extractions'] > 0:
            success_rate = (self.stats['files_with_velocity_params'] / self.stats['successful_extractions']) * 100
            print(f"Velocity parameter availability: {success_rate:.1f}%")
            
            # Show sample velocity information
            valid_files = [(path, params) for path, params in self.results.items() 
                         if params.get('has_valid_velocity_scale', False)]
            
            if valid_files:
                print(f"\n🌊 Sample Velocity Parameters:")
                for i, (file_path, params) in enumerate(valid_files[:3]):  # Show first 3
                    relative_path = os.path.relpath(file_path, self.input_dir)
                    category = params.get('doppler_category', 'unknown')
                    scale_info = params['primary_velocity_params']['velocity_scale_info']
                    print(f"  {relative_path} ({category.upper()}):")
                    print(f"    {scale_info['calculation_formula']}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract velocity measurement parameters from Doppler DICOM echocardiography images')
    parser.add_argument('input_dir', help='Input directory containing DICOM files')
    parser.add_argument('--output-dir', help='Output directory for results (default: input_dir/velocity_parameters)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = VelocityParameterExtractor(args.input_dir, args.output_dir)
    
    try:
        # Process all files
        extractor.process_all_files()
        
        # Save results
        extractor.save_results()
        
        # Print summary
        extractor.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()