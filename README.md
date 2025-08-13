# DICOM Echocardiography Classification & Measurement System

Comprehensive automated classification and measurement parameter extraction system for echocardiography DICOM files using advanced header analysis.

## Overview

This project provides intelligent classification of echocardiography DICOM images into 10 categories and extracts precise measurement parameters for clinical analysis:

### 📊 **Classification Categories:**
1. **Excluded Images** - Invalid images (ImageType[10]=="I1" or ImageType[2]=="INVALID")
2. **Tissue Doppler (0019,0003)** - Tissue Doppler imaging modes (HIGH PRIORITY)
3. **Side-by-side B-mode + Color Doppler** - Adjacent B-mode and Color Doppler regions (HIGH PRIORITY)
4. **Multi-frame with Color Doppler (0011)** - Cine loops with color flow mapping (excluding side-by-side)
5. **Multi-frame without Color Doppler (0001)** - Grayscale cine loops
6. **2D Single-frame without Color Doppler (0001)** - Standard 2D echocardiography images
7. **2D Single-frame with Color Doppler (0011)** - Static images with color flow mapping
8. **CW Doppler (0002,0004,0005,0015)** - Continuous Wave Doppler and M-Mode spectrograms
9. **PW Doppler (0008,0009)** - Pulsed Wave Doppler spectrograms
10. **Color M-Mode (0020)** - M-Mode with color flow overlay

### 📏 **Measurement Parameter Extraction:**
- **Linear Measurements**: Scale parameters for 2D single-frame images
- **Velocity Measurements**: Doppler scale parameters for CW/PW/Tissue Doppler
- **Cardiac Phase Detection**: End-systolic/End-diastolic frame identification
- **Spatial Analysis**: Side-by-side region detection and bounds

## Key Features

### 🎯 **Core Classification**
- ✅ **Read-only processing** - Original DICOM files are never modified
- ✅ **Intelligent classification** using vendor-specific DICOM header patterns
- ✅ **Advanced spatial analysis** with side-by-side detection (v2.4)
- ✅ **Tissue Doppler classification** using ImageType[3] vendor codes
- ✅ **Side-by-side layout detection** using SequenceOfUltrasoundRegions analysis
- ✅ **Enhanced progress tracking** with tqdm progress bars for large datasets
- ✅ **Confidence scoring** with detailed reasoning for each classification

### 📏 **Measurement Systems**
- ✅ **Linear measurement parameters** for 2D anatomical measurements
- ✅ **Velocity measurement parameters** for Doppler velocity calculations
- ✅ **Cardiac phase detection** with ES0 + conventional cycle numbering
- ✅ **Image dimension tracking** for resizing adjustments
- ✅ **Multiple coordinate systems** support (reference pixels, physical coordinates)
- ✅ **Unit conversion** and validation

### 💾 **Output & Integration**
- ✅ **Multiple output formats** - CSV summaries, detailed JSON results, statistics
- ✅ **Ready-to-use calculation scripts** for measurements
- ✅ **Image saving capabilities** for visual validation
- ✅ **Robust error handling** and comprehensive logging

## Quick Start

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd DICOM_classification

# Setup virtual environment and install dependencies
./setup_env.sh
source dicom_env/bin/activate
```

### 2. Classification & Analysis
```bash
# Run sample classification (non-interactive)
python run_classification.py

# Test side-by-side detection on specific files
python test_side_by_side.py

# Process all DICOM files in your dataset (full classification)
python run_classification.py --full

# Or use the main classifier directly
python dicom_echo_classifier.py /path/to/dicom/files
```

### 3. Measurement Parameter Extraction
```bash
# Extract linear measurement parameters from 2D images
python extract_measurement_parameters.py /path/to/dicom/files

# Extract velocity parameters from Doppler images
python extract_velocity_parameters.py /path/to/dicom/files

# Extract cardiac phases from multi-frame images
python extract_cardiac_phases.py /path/to/dicom/files

# Test cardiac phase extraction on sample files
python test_cardiac_extraction.py /path/to/dicom/directory
```

### 4. Visualization & Validation
```bash
# Save sample images as PNG files for visual validation
python save_images.py --max-per-category 3
```

## Files Structure

```
DICOM_classification/
├── 🎯 Core Classification
│   ├── dicom_echo_classifier.py    # Main classification engine (v2.4)
│   ├── run_classification.py       # Non-interactive batch processing
│   └── test_side_by_side.py        # Side-by-side detection validation
│
├── 📏 Measurement Parameter Extraction
│   ├── extract_measurement_parameters.py  # Linear measurements (2D images)
│   ├── extract_velocity_parameters.py     # Velocity measurements (Doppler)
│   ├── cardiac_phase_detector.py          # Cardiac phase detection core
│   ├── extract_cardiac_phases.py          # Cardiac phase batch extraction
│   └── test_cardiac_extraction.py         # Test cardiac phase extraction
│
├── 🔧 Utilities & Validation
│   └── save_images.py              # Save DICOM images as PNG files
│
├── 📁 Configuration & Documentation
│   ├── requirements.txt            # Python dependencies
│   ├── setup_env.sh               # Environment setup script
│   ├── README.md                  # This file
│   ├── CLAUDE.md                  # Detailed documentation
│   └── CHANGELOG.md               # Version history
│
├── 🛠️ Utils Directory
│   ├── create_v2_4_flowchart.py   # Generate classification flowchart
│   └── examine_headers.py         # DICOM header analysis
│
└── 📊 Analysis Directory
    ├── v2_4_classification_flowchart.png
    └── header_analysis.txt
```

## Classification Logic (Updated v2.4)

**Advanced 5-step priority hierarchy with spatial analysis:**

### Step 1: Exclusion Check (HIGHEST PRIORITY)
- **ImageType[10] == "I1"** or **ImageType[2] == "INVALID"** → Excluded category

### Step 2: Tissue Doppler Detection (2ND PRIORITY)
- **ImageType[3] codes**: `"0019"`, `"0003"` → Tissue Doppler category

### Step 3: Side-by-side Layout Detection (3RD PRIORITY)
- **SequenceOfUltrasoundRegions analysis**:
  - Exactly 2 regions: 1 B-mode (RegionDataType=1) + 1 Color Doppler (RegionDataType=2)
  - Adjacent layout with gap < 100px and overlap detection
  - Separates comparative displays from standard cine loops

### Step 4: Frame Count Detection (4TH PRIORITY)
- **NumberOfFrames** (0028,0008) - Determines multi-frame vs single-frame

### Step 5: ImageType[3] Classification (5TH PRIORITY)
- **Vendor-specific codes**:
  - `0001`, `0011`: Frame-based classification with Color Doppler detection
  - `0002,0004,0005,0015`: CW Doppler (0003 moved to Tissue Doppler)
  - `0008,0009`: PW Doppler
  - `0020`: Color M-Mode

### Key Algorithm Features (v2.4):
- ✅ **Side-by-side detection** using spatial region analysis
- ✅ **Tissue Doppler classification** (renamed from annotations)
- ✅ **Enhanced clinical accuracy** by separating display types
- ✅ **10-category system** with proper priority hierarchy

## Output Files

### Sample Classification (`run_classification.py`)
- `sample_results/classification_results.json` - Detailed results with metadata
- `sample_results/classification_summary.csv` - Summary table  
- `sample_results/classification_stats.json` - Statistics by category
- `sample_results/classification.log` - Processing log

### Full Classification (`run_classification.py --full`)
- `full_results/classification_results.json` - Complete detailed results
- `full_results/classification_summary.csv` - Complete summary table
- `full_results/classification_stats.json` - Complete statistics
- `full_results/classification.log` - Complete processing log

## Requirements

- Python 3.8+
- pydicom >= 2.3.0
- matplotlib >= 3.5.0 (for visualization)
- numpy >= 1.21.0
- tqdm >= 4.64.0 (for progress bars)

## Usage Examples

### 🎯 **Basic Classification**
```python
from dicom_echo_classifier import EchoCardiographyClassifier

# Initialize classifier
classifier = EchoCardiographyClassifier('/path/to/dicom/files', '/path/to/output')
classifier.process_directory()
classifier.save_results()

# Single file classification
classification = classifier.classify_dicom('/path/to/file.dcm')
print(f"Category: {classification.category}")
print(f"Description: {classifier.CATEGORIES[classification.category]}")
print(f"Confidence: {classification.confidence}")
print(f"Reasoning: {classification.reasoning}")
```

### 📏 **Linear Measurement Parameters**
```python
from extract_measurement_parameters import MeasurementParameterExtractor

# Extract linear measurement scales for 2D images
extractor = MeasurementParameterExtractor('/path/to/dicom/files')
extractor.process_all_files()
extractor.save_results()

# Calculate distance between two pixels
params = extractor.results['/path/to/2d_image.dcm']
distance, unit = extractor.calculate_pixel_distance((100, 200), (250, 350), params)
print(f"Distance: {distance:.3f} {unit}")
```

### 🌊 **Velocity Measurement Parameters**
```python
from extract_velocity_parameters import VelocityParameterExtractor

# Extract velocity scales for Doppler images
extractor = VelocityParameterExtractor('/path/to/dicom/files')
extractor.process_all_files()
extractor.save_results()

# Calculate velocity at specific pixel coordinate
params = extractor.results['/path/to/doppler.dcm']
velocity, unit = extractor.calculate_velocity_at_pixel(200, params)
print(f"Velocity at pixel Y=200: {velocity:.3f} {unit}")
```

### 🫀 **Cardiac Phase Detection**
```python
from extract_cardiac_phases import CardiacPhaseExtractor

# Extract cardiac phases from multi-frame images
extractor = CardiacPhaseExtractor('/path/to/dicom/files')
extractor.process_all_files()
extractor.save_results()

# Results: ES0: 5, ED1: 21, ES1: 9, ED2: 43, ES2: 32
```

### 🔍 **Advanced Detection Examples**
```python
# Side-by-side detection test
ds = pydicom.dcmread('/path/to/file.dcm')
metadata = classifier.extract_metadata(ds)
is_side_by_side = classifier.is_side_by_side_doppler(ds, metadata)
print(f"Side-by-side layout detected: {is_side_by_side}")

# Cardiac phase detection for single file
from cardiac_phase_detector import detect_cardiac_phases_for_multiframe
cardiac_info = detect_cardiac_phases_for_multiframe('/path/to/multiframe.dcm')
if cardiac_info:
    print(f"End-systolic frames: {cardiac_info['end_systolic_frames']}")
    print(f"End-diastolic frames: {cardiac_info['end_diastolic_frames']}")
```

## Performance

- **Processing Speed**: ~6-10 files per second
- **Memory Usage**: Low (processes files individually)  
- **Accuracy**: High confidence scoring based on multiple DICOM tags
- **Scalability**: Handles datasets with thousands of files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

Private repository - All rights reserved.

## Support

For questions or issues, please create an issue in this repository.

---

---

## Version 2.4.0 Major Release Highlights

### 🎯 **Advanced Classification System**
- **Side-by-side Detection**: Advanced spatial analysis using SequenceOfUltrasoundRegions
- **Tissue Doppler Classification**: ImageType[3] codes 0019 and 0003 high-priority detection
- **10-category System**: Expanded from 9 to 10 classification categories
- **5-step Priority Hierarchy**: Improved accuracy with intelligent decision flow

### 📏 **NEW: Comprehensive Measurement Parameter Extraction**
- **Linear Measurements**: Scale parameters for 2D single-frame images (mm/pixel)
- **Velocity Measurements**: Doppler scale parameters for CW/PW/Tissue Doppler (m/s per pixel)
- **Multi-region Support**: Handles complex Doppler displays with multiple regions
- **Image Dimension Tracking**: Essential for resizing adjustments
- **Reference Pixel Coordinates**: Both X and Y coordinates for time and velocity calculations

### 🫀 **Cardiac Phase Detection System** *(NEW)*
- **Automatic ES/ED Detection**: End-systolic and end-diastolic frame identification
- **Conventional Cycle Numbering**: ES0 → ED1,ES1 → ED2,ES2 following cardiac cycle convention
- **Multi-frame Processing**: R-wave timing analysis for precise cardiac timing
- **Multiple Output Formats**: JSON, CSV, TXT, and ready-to-use calculation scripts
- **Batch Processing**: Handles large datasets with progress tracking

### 🔧 **Technical Improvements**
- **PW Doppler Fix**: Resolved Region Data Type 3 detection for proper velocity extraction
- **Enhanced Progress Tracking**: tqdm integration for large dataset processing
- **Robust Error Handling**: Comprehensive validation and debugging tools
- **Multiple Output Formats**: CSV, JSON, calculation examples for each measurement type

### 💡 **New Calculation Capabilities**
- **Distance Calculations**: `distance = √[(Δx × scale_x)² + (Δy × scale_y)²]`
- **Velocity Calculations**: `velocity = ref_velocity + (pixel_y - ref_pixel_y) × delta_y`
- **Time Calculations**: `time = ref_time + (pixel_x - ref_pixel_x) × delta_x`
- **Cardiac Phase Mapping**: Frame-to-phase correspondence for temporal analysis

**Example Classification Results:**
```
File: 1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm
- Layout: B-mode (left) + Color Doppler (right) with 41px gap
- 73 frames cine loop → side_by_side_doppler (not multi_frame_with_doppler)
- Clinical use: Combined anatomical and hemodynamic assessment
```

**Example Measurement Parameter Extraction:**
```bash
# Linear measurements for 2D images
python extract_measurement_parameters.py /path/to/dicom/dataset
# Output: measurement_parameters/measurement_scales.csv
# Sample: image_001.dcm, True, 0.058594, 0.058594, mm, mm, 1024x768, (512, 384)

# Velocity measurements for Doppler images  
python extract_velocity_parameters.py /path/to/dicom/dataset
# Output: velocity_parameters/velocity_measurements.csv
# Sample: doppler_001.dcm, pw_doppler, True, True, -0.351, 0.00231, 0.0, 864, 90, 1, 1016x758
```

**Example Cardiac Phase Detection:**
```bash
python extract_cardiac_phases.py /path/to/dicom/dataset

# Output files:
# cardiac_phases/cardiac_phases.csv - Summary with frame numbers
# cardiac_phases/frame_mapping.txt - Simple mapping format
# cardiac_phases/multiple_access_formats.txt - Complete analysis

# Sample output format (conventional cardiac cycle):
# multiframe_file_001.dcm: ES0: 5, ED1: 21, ES1: 9, ED2: 43, ES2: 32
# multiframe_file_002.dcm: ES0: 3, ED1: 18, ES1: 7, ED2: 35, ES2: 25
```

**Example Measurement Calculations:**
```python
# Linear distance calculation
distance, unit = calculate_pixel_distance((100, 200), (250, 350), linear_params)
# Result: 12.845 mm

# Velocity calculation  
velocity, unit = calculate_velocity_at_pixel(200, velocity_params)
# Result: -38.583 m/s (using: velocity = 0.0 + (200 - 90) × -0.351)

# Time calculation
time, unit = calculate_time_at_pixel(500, velocity_params)  
# Result: 1.157 s (using: time = 0.0 + (500 - 864) × 0.00231)
```

---

**Note**: This system performs read-only analysis of DICOM files. Original files are never modified or moved.