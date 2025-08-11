# DICOM Echocardiography Classification

Automated classification system for echocardiography DICOM files using header analysis.

## Overview

This project provides intelligent classification of echocardiography DICOM images into 6 categories based on DICOM header information analysis:

1. **2D echo images without Color Doppler** - Standard grayscale 2D echocardiography images
2. **2D echo images with Color Doppler** - 2D images with color flow mapping overlay  
3. **M-mode Doppler signals images** - Time-motion displays with Doppler signal information
4. **M-mode 2D images** - Standard M-mode time-motion displays
5. **Images with side-by-side comparison** - Multi-frame or tiled comparison layouts
6. **Images with annotations/measurements** - DICOM files containing graphic annotations, measurements, or calibration markers

## Key Features

- ✅ **Read-only processing** - Original DICOM files are never modified
- ✅ **Intelligent classification** using DICOM header tags
- ✅ **Confidence scoring** with detailed reasoning for each classification
- ✅ **Multiple output formats** - CSV summaries, detailed JSON results, statistics
- ✅ **Interactive visualization** capabilities for result validation
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
# Test on sample files with interactive visualization
python test_classifier.py

# Or run non-interactive sample classification
python run_classification.py
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
├── dicom_echo_classifier.py    # Main classification engine
├── test_classifier.py          # Interactive test with visualization
├── run_classification.py       # Non-interactive batch processing
├── requirements.txt            # Python dependencies
├── setup_env.sh               # Environment setup script
├── CLAUDE.md                  # Detailed documentation
└── README.md                  # This file
```

## Classification Logic

The system analyzes multiple DICOM header tags:

- **Modality** (0008,0060) - Confirms ultrasound imaging
- **Image Type** (0008,0008) - Identifies imaging modes and annotations
- **Series Description** (0008,103E) - Contains detailed imaging information
- **Color Space** (0028,0004) - Detects color Doppler presence  
- **Samples Per Pixel** (0028,0002) - Identifies RGB color images
- **Number of Frames** (0028,0008) - Detects multi-frame comparisons
- **Graphic Annotation Sequence** (0070,0001) - Detects annotations
- **Text Object Sequence** (0070,0008) - Detects measurements
- **Overlay Data** (60xx,3000) - Detects overlay annotations

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
print(f"Confidence: {classification.confidence}")
print(f"Reasoning: {classification.reasoning}")
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

**Note**: This system performs read-only analysis of DICOM files. Original files are never modified or moved.