# DICOM Echocardiography Classification Project

This project provides automated classification of echocardiography DICOM files into specific categories based on header information analysis.

## Project Overview

This directory contains scripts for analyzing and classifying DICOM echocardiography images from the 2023Examples dataset. The classification is performed by examining DICOM header tags without modifying the original files.

## Classification Categories

The system classifies DICOM files into 6 categories:

1. **2D echo images without Color Doppler** - Standard grayscale 2D echocardiography images
2. **2D echo images with Color Doppler** - 2D images with color flow mapping overlay
3. **M-mode Doppler signals images** - Time-motion displays with Doppler signal information
4. **M-mode 2D images** - Standard M-mode time-motion displays
5. **Images with side-by-side comparison** - Multi-frame or tiled comparison layouts
6. **Images with annotations/measurements** - DICOM files containing graphic annotations, measurements, or calibration markers

## Files

- `dicom_echo_classifier.py` - Main classification script
- `test_classifier.py` - Test script with visualization capabilities
- `CLAUDE.md` - This documentation file

## Dependencies

Required Python packages:
```bash
pip install pydicom matplotlib numpy
```

## Usage

### Quick Test (Recommended First)
Test the classifier on a sample of files with interactive visualization:
```bash
cd /research/projects/Chao/Echo-preprocessing/DICOM_classification
python test_classifier.py
```

### Full Classification
Run classification on all DICOM files in the 2023Examples directory:
```bash
python dicom_echo_classifier.py /research/projects/Chao/Echo-preprocessing/2023Examples
```

### Full Classification with Visualization
Run full classification and generate summary plots:
```bash
python test_classifier.py --full
```

## Output Files

The classification generates several output files (all read-only, original files unchanged):

### Test Results (test_classifier.py)
- `test_results/classification.log` - Processing log
- Interactive visualization of sample images from each category

### Full Classification Results 
- `classification_results/classification_results.json` - Detailed results with metadata
- `classification_results/classification_summary.csv` - Summary table
- `classification_results/classification_stats.json` - Statistics by category
- `classification_results/classification.log` - Processing log
- `classification_results/classification_summary.png` - Bar chart of results
- `classification_results/classification_distribution.png` - Pie chart distribution

## Classification Logic (Updated v2.0)

**⚠️ IMPORTANT: Classification logic updated based on actual dataset analysis**

### Key Findings from Dataset Analysis:
- **All files have SamplesPerPixel=3** (RGB format) - NOT indicative of Color Doppler
- **SeriesDescription is empty** for all files - no text-based classification possible  
- **Multi-frame files are cine loops**, not side-by-side comparisons
- **ImageType[3] contains vendor codes** that distinguish image types

### Corrected Classification Tags:

#### Primary Tags (High Priority):
- **ImageType[3]** - Vendor-specific codes:
  - `0001`, `0011`: Multi-frame cine loops
  - `0005`, `0009`, `0015`, `0019`: Static single images
- **UltrasoundColorDataPresent** (0018,9070) - True Color Doppler indicator (0 or 1)
- **NumberOfFrames** (0028,0008) - Confirms cine vs static
- **Graphic Annotation Sequence** (0070,0001) - Detects annotations
- **Text Object Sequence** (0070,0008) - Detects measurements

#### Secondary Tags (Lower Priority):
- **Modality** (0008,0060) - Confirms ultrasound imaging (always "US")
- **Image Type** (0008,0008) - General image type info
- **Overlay Data** (60xx,3000) - Detects overlay annotations

#### Tags to IGNORE (Misleading):
- ❌ **Samples Per Pixel** (0028,0002) - Always 3 (misleading)
- ❌ **Color Space** (0028,0004) - Not reliable for Color Doppler
- ❌ **Series Description** (0008,103E) - Empty for all files

## Testing

1. **Sample Test**: Run `python run_classification.py` to test on sample files
2. **Image Validation**: Run `python save_images.py` to save images as PNG files for visual verification
3. **Full Processing**: Run `python run_classification.py --full` for complete dataset
4. **Header Analysis**: Run `python utils/examine_headers.py` to analyze DICOM headers

## Notes

- All processing is **read-only** - original DICOM files are never modified
- Classification confidence scores range from 0.0 to 1.0
- Each classification includes reasoning based on detected DICOM tags
- Progress tracking is provided for large datasets
- Error handling for corrupted or non-DICOM files