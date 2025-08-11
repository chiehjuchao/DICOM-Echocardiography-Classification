#!/usr/bin/env python3
"""
Examine actual DICOM headers to understand classification issues
"""

import os
import sys
from pathlib import Path

# Add the current directory to path to import the classifier
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pydicom
    from pydicom import dcmread
except ImportError:
    print("Error: pydicom library not found. Please install with: pip install pydicom")
    sys.exit(1)

def examine_dicom_headers(max_files=10):
    """Examine DICOM headers from sample files"""
    
    root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    
    print("DICOM Header Analysis")
    print("="*60)
    print(f"Examining headers from: {root_dir}")
    print()
    
    # Find sample DICOM files
    sample_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.dcm'):
                sample_files.append(os.path.join(root, file))
                if len(sample_files) >= max_files:
                    break
        if len(sample_files) >= max_files:
            break
    
    if not sample_files:
        print("No DICOM files found")
        return
    
    print(f"Examining {len(sample_files)} sample DICOM files...")
    print()
    
    # Collect all unique values for key fields
    field_values = {
        'Modality': set(),
        'ImageType': set(),
        'SeriesDescription': set(),
        'StudyDescription': set(),
        'AcquisitionType': set(),
        'SamplesPerPixel': set(),
        'PhotometricInterpretation': set(),
        'ColorSpace': set(),
        'NumberOfFrames': set(),
        'UltrasoundColorDataPresent': set()
    }
    
    # Detailed analysis per file
    file_details = []
    
    for i, file_path in enumerate(sample_files):
        print(f"File {i+1}/{len(sample_files)}: {os.path.basename(file_path)}")
        
        try:
            ds = dcmread(file_path, force=True)
            
            # Extract key fields
            details = {
                'filename': os.path.basename(file_path),
                'modality': getattr(ds, 'Modality', 'N/A'),
                'image_type': str(getattr(ds, 'ImageType', 'N/A')),
                'series_description': getattr(ds, 'SeriesDescription', 'N/A'),
                'study_description': getattr(ds, 'StudyDescription', 'N/A'),
                'acquisition_type': getattr(ds, 'AcquisitionType', 'N/A'),
                'samples_per_pixel': getattr(ds, 'SamplesPerPixel', 'N/A'),
                'photometric_interpretation': getattr(ds, 'PhotometricInterpretation', 'N/A'),
                'color_space': getattr(ds, 'ColorSpace', 'N/A'),
                'number_of_frames': getattr(ds, 'NumberOfFrames', 1),
                'ultrasound_color_data': getattr(ds, 'UltrasoundColorDataPresent', 'N/A'),
                'rows': getattr(ds, 'Rows', 'N/A'),
                'columns': getattr(ds, 'Columns', 'N/A')
            }
            
            file_details.append(details)
            
            # Collect unique values
            for field, value_set in field_values.items():
                key_map = {
                    'Modality': 'modality',
                    'ImageType': 'image_type', 
                    'SeriesDescription': 'series_description',
                    'StudyDescription': 'study_description',
                    'AcquisitionType': 'acquisition_type',
                    'SamplesPerPixel': 'samples_per_pixel',
                    'PhotometricInterpretation': 'photometric_interpretation',
                    'ColorSpace': 'color_space',
                    'NumberOfFrames': 'number_of_frames',
                    'UltrasoundColorDataPresent': 'ultrasound_color_data'
                }
                if field in key_map:
                    value_set.add(str(details[key_map[field]]))
            
            # Print key info for this file
            print(f"  Modality: {details['modality']}")
            print(f"  ImageType: {details['image_type']}")
            print(f"  SeriesDescription: '{details['series_description']}'")
            print(f"  SamplesPerPixel: {details['samples_per_pixel']}")
            print(f"  PhotometricInterpretation: {details['photometric_interpretation']}")
            print(f"  NumberOfFrames: {details['number_of_frames']}")
            print(f"  Dimensions: {details['rows']}x{details['columns']}")
            print()
            
        except Exception as e:
            print(f"  Error reading file: {e}")
            print()
    
    # Summary of unique values
    print("\n" + "="*60)
    print("SUMMARY OF UNIQUE VALUES FOUND")
    print("="*60)
    
    for field, values in field_values.items():
        print(f"\n{field}:")
        for value in sorted(values):
            print(f"  - {value}")
    
    # Analysis and recommendations
    print("\n" + "="*60)
    print("CLASSIFICATION ANALYSIS")
    print("="*60)
    
    # Check for patterns that might indicate misclassification
    analysis = []
    
    # Analyze NumberOfFrames
    frame_counts = [int(d['number_of_frames']) for d in file_details if str(d['number_of_frames']).isdigit()]
    if frame_counts:
        analysis.append(f"NumberOfFrames range: {min(frame_counts)} to {max(frame_counts)}")
        multi_frame = len([f for f in frame_counts if f > 1])
        analysis.append(f"Multi-frame files: {multi_frame}/{len(file_details)} ({multi_frame/len(file_details)*100:.1f}%)")
    
    # Analyze SamplesPerPixel 
    pixel_samples = [int(d['samples_per_pixel']) for d in file_details if str(d['samples_per_pixel']).isdigit()]
    if pixel_samples:
        rgb_files = len([s for s in pixel_samples if s > 1])
        analysis.append(f"RGB/Color files (SamplesPerPixel > 1): {rgb_files}/{len(file_details)} ({rgb_files/len(file_details)*100:.1f}%)")
    
    # Check for aspect ratios (potential side-by-side)
    aspect_ratios = []
    for d in file_details:
        if str(d['rows']).isdigit() and str(d['columns']).isdigit():
            rows, cols = int(d['rows']), int(d['columns'])
            if rows > 0:
                ratio = cols / rows
                aspect_ratios.append(ratio)
                if ratio > 1.5:
                    analysis.append(f"Wide aspect ratio file: {d['filename']} ({cols}x{rows}, ratio: {ratio:.2f})")
    
    for item in analysis:
        print(f"• {item}")
    
    # Save detailed results
    output_file = '/research/projects/Chao/Echo-preprocessing/DICOM_classification/header_analysis.txt'
    with open(output_file, 'w') as f:
        f.write("DETAILED DICOM HEADER ANALYSIS\n")
        f.write("="*50 + "\n\n")
        
        for details in file_details:
            f.write(f"File: {details['filename']}\n")
            for key, value in details.items():
                if key != 'filename':
                    f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        f.write("\nUNIQUE VALUES SUMMARY:\n")
        f.write("-"*30 + "\n")
        for field, values in field_values.items():
            f.write(f"\n{field}:\n")
            for value in sorted(values):
                f.write(f"  - {value}\n")
        
        f.write("\nANALYSIS:\n")
        f.write("-"*10 + "\n")
        for item in analysis:
            f.write(f"• {item}\n")
    
    print(f"\n✅ Detailed analysis saved to: {output_file}")
    
    # Provide specific recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS FOR IMPROVING CLASSIFICATION")
    print("="*60)
    
    recommendations = [
        "1. Review the actual ImageType values to understand vendor-specific patterns",
        "2. Check if SeriesDescription contains meaningful information for classification", 
        "3. Verify if multi-frame files are truly side-by-side or just cine loops",
        "4. Consider using image dimensions and aspect ratios more carefully",
        "5. Look for vendor-specific DICOM tags that might indicate image types",
        "6. Consider pixel-level analysis for color detection if header tags are insufficient"
    ]
    
    for rec in recommendations:
        print(rec)

if __name__ == '__main__':
    examine_dicom_headers(15)  # Examine 15 sample files