# DICOM Echocardiography Classification

Automated classification system for echocardiography DICOM files using header analysis.

## Overview

This project provides intelligent classification of echocardiography DICOM images into 10 categories based on DICOM header information analysis:

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

## Key Features

- ✅ **Read-only processing** - Original DICOM files are never modified
- ✅ **Intelligent classification** using vendor-specific DICOM header patterns
- ✅ **Advanced spatial analysis** with side-by-side detection (v2.4)
- ✅ **Tissue Doppler classification** using ImageType[3] vendor codes
- ✅ **Side-by-side layout detection** using SequenceOfUltrasoundRegions analysis
- ✅ **Confidence scoring** with detailed reasoning for each classification
- ✅ **Multiple output formats** - CSV summaries, detailed JSON results, statistics
- ✅ **Image saving capabilities** for visual validation
- ✅ **Progress tracking** for large datasets
- ✅ **Comprehensive logging** and error handling

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

### 2. Test Classification
```bash
# Run sample classification (non-interactive)
python run_classification.py

# Test side-by-side detection on specific files
python test_side_by_side.py

# Save sample images as PNG files for visual validation
python save_images.py --max-per-category 3
```

### 3. Full Classification
```bash
# Process all DICOM files in your dataset
python run_classification.py --full

# Or use the main classifier directly
python dicom_echo_classifier.py /path/to/dicom/files
```

## Files Structure

```
DICOM_classification/
├── dicom_echo_classifier.py    # Main classification engine (v2.4)
├── test_side_by_side.py        # Side-by-side detection validation
├── run_classification.py       # Non-interactive batch processing
├── save_images.py              # Save DICOM images as PNG files
├── requirements.txt            # Python dependencies
├── setup_env.sh               # Environment setup script
├── CLAUDE.md                  # Detailed documentation
├── CHANGELOG.md               # Version history
├── README.md                  # This file
├── utils/                     # Utility scripts
│   ├── create_v2_4_flowchart.py
│   ├── create_corrected_flowchart.py
│   └── examine_headers.py
└── analysis/                  # Analysis results
    ├── v2_4_classification_flowchart.png
    ├── corrected_classification_flowchart.png
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

## Usage Examples

### Basic Classification
```python
from dicom_echo_classifier import EchoCardiographyClassifier

classifier = EchoCardiographyClassifier('/path/to/dicom/files', '/path/to/output')
classifier.process_directory()
classifier.save_results()
```

### Single File Classification
```python
classification = classifier.classify_dicom('/path/to/file.dcm')
print(f"Category: {classification.category}")
print(f"Description: {classifier.CATEGORIES[classification.category]}")
print(f"Confidence: {classification.confidence}")
print(f"Reasoning: {classification.reasoning}")
```

### Side-by-side Detection Test
```python
ds = pydicom.dcmread('/path/to/file.dcm')
metadata = classifier.extract_metadata(ds)
is_side_by_side = classifier.is_side_by_side_doppler(ds, metadata)
print(f"Side-by-side layout detected: {is_side_by_side}")
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

## Version 2.4.0 Highlights

### 🎯 **New Side-by-side Detection**
- Advanced spatial analysis using SequenceOfUltrasoundRegions
- Detects adjacent B-mode + Color Doppler layouts
- Separates comparative displays from cine loops

### 🔬 **Tissue Doppler Classification**
- ImageType[3] codes 0019 and 0003 now classified as Tissue Doppler
- High-priority category for specialized imaging modes

### 📊 **Enhanced System**
- Expanded from 9 to 10 classification categories
- 5-step priority hierarchy for improved accuracy
- Updated documentation and flowchart

**Example Side-by-side Detection:**
```
File: 1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm
- Layout: B-mode (left) + Color Doppler (right) with 41px gap
- 73 frames cine loop → side_by_side_doppler (not multi_frame_with_doppler)
- Clinical use: Combined anatomical and hemodynamic assessment
```

---

**Note**: This system performs read-only analysis of DICOM files. Original files are never modified or moved.