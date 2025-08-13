#!/usr/bin/env python3
"""
Extract Linear Measurement Parameters from DICOM Echocardiography Images

This module extracts essential parameters for linear measurements from DICOM files,
specifically targeting 2D single-frame images without Color Doppler for precise
measurement calculations.

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


class MeasurementParameterExtractor:
    """
    Extract measurement parameters from 2D single-frame DICOM echocardiography images.
    """
    
    def __init__(self, input_dir: str, output_dir: str = None):
        """
        Initialize the measurement parameter extractor.
        
        Args:
            input_dir: Directory containing DICOM files
            output_dir: Directory to save results (default: input_dir/measurement_parameters)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "measurement_parameters"
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {}
        self.stats = {
            'total_files': 0,
            '2d_single_no_doppler_files': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'files_with_measurement_params': 0
        }
    
    def extract_measurement_parameters(self, dicom_file_path: str) -> Optional[Dict]:
        """
        Extract essential parameters for linear measurements from DICOM file.
        
        Args:
            dicom_file_path: Path to DICOM file
            
        Returns:
            Dictionary with key measurement parameters or None if extraction fails
        """
        try:
            ds = pydicom.dcmread(dicom_file_path)
            
            # Check for SequenceOfUltrasoundRegions
            ultrasound_regions = ds.get((0x0018, 0x6011))
            if not ultrasound_regions:
                return None
            
            # Extract parameters from first region (typically the measurement region)
            region = ultrasound_regions[0]
            
            params = {
                'file_path': dicom_file_path,
                'reference_pixel_x': region.get((0x0018, 0x6020)).value if (0x0018, 0x6020) in region else None,
                'reference_pixel_y': region.get((0x0018, 0x6022)).value if (0x0018, 0x6022) in region else None,
                'physical_delta_x': region.get((0x0018, 0x602C)).value if (0x0018, 0x602C) in region else None,
                'physical_delta_y': region.get((0x0018, 0x602E)).value if (0x0018, 0x602E) in region else None,
                'unit_code_x': region.get((0x0018, 0x6024)).value if (0x0018, 0x6024) in region else 1,
                'unit_code_y': region.get((0x0018, 0x6026)).value if (0x0018, 0x6026) in region else 1,
                'region_bounds': {
                    'min_x': region.get((0x0018, 0x6018)).value if (0x0018, 0x6018) in region else None,
                    'min_y': region.get((0x0018, 0x601A)).value if (0x0018, 0x601A) in region else None,
                    'max_x': region.get((0x0018, 0x601C)).value if (0x0018, 0x601C) in region else None,
                    'max_y': region.get((0x0018, 0x601E)).value if (0x0018, 0x601E) in region else None
                },
                # Additional metadata for validation
                'image_dimensions': {
                    'rows': getattr(ds, 'Rows', 0),
                    'columns': getattr(ds, 'Columns', 0)
                },
                'modality': getattr(ds, 'Modality', ''),
                'image_type': getattr(ds, 'ImageType', [])
            }
            
            # Validate that we have the essential scaling parameters
            if params['physical_delta_x'] is not None and params['physical_delta_y'] is not None:
                params['has_valid_scale'] = True
                # Calculate scale information
                params['scale_info'] = {
                    'x_scale': params['physical_delta_x'],
                    'y_scale': params['physical_delta_y'],
                    'x_unit': self.get_unit_name(params['unit_code_x']),
                    'y_unit': self.get_unit_name(params['unit_code_y']),
                    'scale_string_x': f"{params['physical_delta_x']:.6f} {self.get_unit_name(params['unit_code_x'])}/pixel",
                    'scale_string_y': f"{params['physical_delta_y']:.6f} {self.get_unit_name(params['unit_code_y'])}/pixel"
                }
            else:
                params['has_valid_scale'] = False
                params['scale_info'] = None
            
            return params
            
        except Exception as e:
            print(f"Error extracting measurement parameters from {os.path.basename(dicom_file_path)}: {e}")
            return None
    
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
    
    def calculate_pixel_distance(self, pixel1: Tuple[int, int], pixel2: Tuple[int, int], 
                               params: Dict) -> Tuple[float, str]:
        """
        Calculate physical distance between two pixels.
        
        Args:
            pixel1: First pixel coordinates (x, y)
            pixel2: Second pixel coordinates (x, y)
            params: Measurement parameters dictionary
            
        Returns:
            Tuple of (distance, unit_name)
        """
        if not params.get('has_valid_scale', False):
            raise ValueError("No valid scale parameters available")
        
        x1, y1 = pixel1
        x2, y2 = pixel2
        
        # Convert pixel differences to physical distance
        dx_physical = (x2 - x1) * params['physical_delta_x']
        dy_physical = (y2 - y1) * params['physical_delta_y']
        
        distance = math.sqrt(dx_physical**2 + dy_physical**2)
        unit = self.get_unit_name(params['unit_code_x'])
        
        return distance, unit
    
    def find_2d_single_no_doppler_files(self) -> List[str]:
        """
        Find all DICOM files classified as '2d_single_no_doppler'.
        
        Returns:
            List of file paths for 2D single-frame images without Color Doppler
        """
        if EchoCardiographyClassifier is None:
            print("⚠️  Classification system not available. Processing all DICOM files...")
            # Fallback: find all DICOM files
            all_files = []
            for root, dirs, files in os.walk(self.input_dir):
                for file in files:
                    if file.lower().endswith('.dcm') or not '.' in file:
                        all_files.append(os.path.join(root, file))
            return all_files
        
        print("🔍 Classifying DICOM files to find 2D single-frame images without Color Doppler...")
        
        # Use classifier to find target files
        classifier = EchoCardiographyClassifier(self.input_dir)
        classifier.process_directory(show_progress=True)
        
        # Extract files classified as '2d_single_no_doppler'
        target_files = []
        for classification in classifier.classifications:
            if classification.category == '2d_single_no_doppler':
                target_files.append(classification.file_path)
        
        self.stats['2d_single_no_doppler_files'] = len(target_files)
        print(f"📊 Found {len(target_files)} files classified as '2D single-frame without Color Doppler'")
        
        return target_files
    
    def process_all_files(self) -> None:
        """
        Process all 2D single-frame files and extract measurement parameters.
        """
        target_files = self.find_2d_single_no_doppler_files()
        
        if not target_files:
            print("⚠️  No 2D single-frame files without Color Doppler found!")
            return
        
        print(f"📏 Extracting measurement parameters from {len(target_files)} files...")
        
        for file_path in tqdm(target_files, desc="Extracting parameters"):
            params = self.extract_measurement_parameters(file_path)
            
            if params:
                self.results[file_path] = params
                self.stats['successful_extractions'] += 1
                
                if params.get('has_valid_scale', False):
                    self.stats['files_with_measurement_params'] += 1
            else:
                self.stats['failed_extractions'] += 1
        
        self.stats['total_files'] = len(target_files)
    
    def save_results(self) -> None:
        """
        Save measurement parameter extraction results to multiple formats.
        """
        if not self.results:
            print("⚠️  No results to save!")
            return
        
        print(f"💾 Saving measurement parameter results to {self.output_dir}")
        
        # 1. Save detailed JSON results
        json_file = self.output_dir / 'measurement_parameters_detailed.json'
        with open(json_file, 'w') as f:
            # Make results JSON serializable
            json_results = {}
            for file_path, params in self.results.items():
                relative_path = os.path.relpath(file_path, self.input_dir)
                json_results[relative_path] = params
            json.dump(json_results, f, indent=2, default=str)
        
        # 2. Save scale parameters CSV
        csv_file = self.output_dir / 'measurement_scales.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File Path', 'Has Valid Scale', 'X Scale (unit/pixel)', 'Y Scale (unit/pixel)', 
                           'X Unit', 'Y Unit', 'Image Dimensions', 'Reference Pixel'])
            
            for file_path, params in self.results.items():
                relative_path = os.path.relpath(file_path, self.input_dir)
                scale_info = params.get('scale_info', {})
                
                writer.writerow([
                    relative_path,
                    params.get('has_valid_scale', False),
                    params.get('physical_delta_x', 'N/A'),
                    params.get('physical_delta_y', 'N/A'),
                    scale_info.get('x_unit', 'N/A'),
                    scale_info.get('y_unit', 'N/A'),
                    f"{params['image_dimensions']['columns']}x{params['image_dimensions']['rows']}",
                    f"({params.get('reference_pixel_x', 'N/A')}, {params.get('reference_pixel_y', 'N/A')})"
                ])
        
        # 3. Save scale summary for files with valid parameters
        summary_file = self.output_dir / 'valid_scales_summary.txt'
        with open(summary_file, 'w') as f:
            f.write("MEASUREMENT SCALE PARAMETERS SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            valid_files = [(path, params) for path, params in self.results.items() 
                         if params.get('has_valid_scale', False)]
            
            f.write(f"Files with valid measurement scales: {len(valid_files)}\n")
            f.write("-" * 40 + "\n\n")
            
            for file_path, params in valid_files:
                relative_path = os.path.relpath(file_path, self.input_dir)
                scale_info = params['scale_info']
                f.write(f"File: {relative_path}\n")
                f.write(f"  X Scale: {scale_info['scale_string_x']}\n")
                f.write(f"  Y Scale: {scale_info['scale_string_y']}\n")
                f.write(f"  Image: {params['image_dimensions']['columns']}x{params['image_dimensions']['rows']}\n")
                f.write(f"  Reference: ({params.get('reference_pixel_x', 'N/A')}, {params.get('reference_pixel_y', 'N/A')})\n")
                f.write("\n")
        
        # 4. Save measurement calculation example
        example_file = self.output_dir / 'measurement_example.py'
        with open(example_file, 'w') as f:
            f.write('''#!/usr/bin/env python3
"""
Example: How to use extracted measurement parameters for distance calculations

This script demonstrates how to calculate physical distances between pixels
using the extracted measurement parameters.
"""

import json
import math

def load_measurement_parameters(json_file_path):
    """Load measurement parameters from JSON file"""
    with open(json_file_path, 'r') as f:
        return json.load(f)

def calculate_distance(pixel1, pixel2, params):
    """
    Calculate physical distance between two pixels
    
    Args:
        pixel1: (x, y) coordinates of first pixel
        pixel2: (x, y) coordinates of second pixel  
        params: Measurement parameters for the image
        
    Returns:
        (distance, unit) tuple
    """
    if not params.get('has_valid_scale', False):
        raise ValueError("No valid scale parameters available")
    
    x1, y1 = pixel1
    x2, y2 = pixel2
    
    # Convert pixel differences to physical distance
    dx_physical = (x2 - x1) * params['physical_delta_x']
    dy_physical = (y2 - y1) * params['physical_delta_y']
    
    distance = math.sqrt(dx_physical**2 + dy_physical**2)
    unit = params['scale_info']['x_unit']
    
    return distance, unit

# Example usage
if __name__ == "__main__":
    # Load parameters
    params = load_measurement_parameters('measurement_parameters_detailed.json')
    
    # Get first file with valid scale as example
    example_file = None
    example_params = None
    
    for file_path, file_params in params.items():
        if file_params.get('has_valid_scale', False):
            example_file = file_path
            example_params = file_params
            break
    
    if example_params:
        print(f"Example measurement using: {example_file}")
        print(f"Scale: {example_params['scale_info']['scale_string_x']}")
        
        # Example distance calculation between two points
        pixel1 = (100, 200)  # First measurement point
        pixel2 = (250, 350)  # Second measurement point
        
        distance, unit = calculate_distance(pixel1, pixel2, example_params)
        print(f"Distance from {pixel1} to {pixel2}: {distance:.3f} {unit}")
    else:
        print("No files with valid measurement scales found")
''')
        
        # 5. Save statistics
        stats_file = self.output_dir / 'extraction_stats.json'
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        print(f"✅ Results saved:")
        print(f"  📄 Detailed parameters: {json_file}")
        print(f"  📊 Scale summary CSV: {csv_file}")
        print(f"  📝 Valid scales summary: {summary_file}")
        print(f"  🧮 Calculation example: {example_file}")
        print(f"  📈 Statistics: {stats_file}")
    
    def print_summary(self) -> None:
        """
        Print summary of measurement parameter extraction results.
        """
        print(f"\n📈 Measurement Parameter Extraction Summary:")
        print(f"{'='*60}")
        print(f"2D single-frame files (no doppler): {self.stats['2d_single_no_doppler_files']}")
        print(f"Successful parameter extractions: {self.stats['successful_extractions']}")
        print(f"Files with valid measurement scales: {self.stats['files_with_measurement_params']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        
        if self.stats['successful_extractions'] > 0:
            success_rate = (self.stats['files_with_measurement_params'] / self.stats['successful_extractions']) * 100
            print(f"Scale parameter availability: {success_rate:.1f}%")
            
            # Show sample scale information
            valid_files = [(path, params) for path, params in self.results.items() 
                         if params.get('has_valid_scale', False)]
            
            if valid_files:
                print(f"\n📏 Sample Scale Parameters:")
                for i, (file_path, params) in enumerate(valid_files[:3]):  # Show first 3
                    relative_path = os.path.relpath(file_path, self.input_dir)
                    scale_info = params['scale_info']
                    print(f"  {relative_path}:")
                    print(f"    Scale: {scale_info['scale_string_x']}, {scale_info['scale_string_y']}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract measurement parameters from 2D single-frame DICOM echocardiography images')
    parser.add_argument('input_dir', help='Input directory containing DICOM files')
    parser.add_argument('--output-dir', help='Output directory for results (default: input_dir/measurement_parameters)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = MeasurementParameterExtractor(args.input_dir, args.output_dir)
    
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