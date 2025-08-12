# DICOM Echocardiography Classification Project

This project provides automated classification of echocardiography DICOM files into specific categories based on header information analysis.

## Project Overview

This directory contains scripts for analyzing and classifying DICOM echocardiography images from the 2023Examples dataset. The classification is performed by examining DICOM header tags without modifying the original files.

## Classification Categories

The system classifies DICOM files into 10 categories with exclusion criteria, tissue doppler detection, side-by-side layout detection, and frame count/ImageType[3] vendor codes:

**Exclusion Category:**
1. **Excluded Images** - Invalid images (ImageType[10]=="I1" or ImageType[2]=="INVALID")

**Special Categories (HIGH PRIORITY):**
2. **Tissue Doppler (0019,0003)** - Tissue Doppler imaging modes (overrides other categories)
3. **Side-by-side B-mode + Color Doppler** - Adjacent B-mode and Color Doppler regions in same image

**Multi-frame Categories:**
4. **Multi-frame with Color Doppler (0011)** - Cine loops with color flow mapping (excluding side-by-side)
5. **Multi-frame without Color Doppler (0001)** - Grayscale cine loops

**Single-frame Categories (by ImageType[3]):**
6. **2D Single-frame without Color Doppler (0001)** - Standard 2D echocardiography images
7. **2D Single-frame with Color Doppler (0011)** - Static images with color flow mapping
8. **CW Doppler (0002,0004,0005,0015)** - Continuous Wave Doppler and M-Mode spectrograms
9. **PW Doppler (0008,0009)** - Pulsed Wave Doppler spectrograms
10. **Color M-Mode (0020)** - M-Mode with color flow overlay

## Files

- `dicom_echo_classifier.py` - Main classification script
- `test_classifier.py` - Test script with visualization capabilities
- `test_side_by_side.py` - Test script for side-by-side detection functionality
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

### Test Side-by-side Detection
Test the side-by-side B-mode + Color Doppler detection:
```bash
python test_side_by_side.py
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

### Classification Logic (v2.4 - Final):

#### Step 1: Exclusion Check (HIGHEST PRIORITY)
- **ImageType[10] == "I1"** or **ImageType[2] == "INVALID"** → Excluded category

#### Step 2: Tissue Doppler Detection (SECOND PRIORITY)
- **Primary: ImageType[3] Vendor Codes**
  - `'0019'`: Tissue Doppler imaging (measurement overlays)
  - `'0003'`: Tissue Doppler imaging (CW variant) ✅ (moved from CW Doppler)
- **Fallback: Standard DICOM tags** (rarely used)
  - **Graphic Annotation Sequence** (0070,0001)
  - **Text Object Sequence** (0070,0008) 
  - **Overlay Data** (60xx,3000)

#### Step 3: Side-by-side Layout Detection (THIRD PRIORITY)
- **SequenceOfUltrasoundRegions Analysis**
  - Exactly 2 regions: 1 B-mode (RegionDataType=1) + 1 Color Doppler (RegionDataType=2)
  - **Horizontal layout**: Adjacent regions with vertical overlap (gap < 100px)
  - **Vertical layout**: Stacked regions with horizontal overlap (gap < 100px)
  - **Clinical use**: Combined anatomical and hemodynamic assessment

#### Step 4: Frame Count Detection (FOURTH PRIORITY)
- **NumberOfFrames** (0028,0008) - Determines multi-frame vs single-frame
  - `> 1`: Multi-frame (cine loops)
  - `= 1` or missing: Single-frame (static images)

#### Step 5: ImageType[3] Classification (FIFTH PRIORITY)
- **Specific vendor codes** determine final category based on imaging mode
- **CW Doppler codes**: 0002,0004,0005,0015 → cw_doppler category (0003 moved to tissue doppler)
- **PW Doppler codes**: 0008,0009 → pw_doppler category
- **Color M-Mode code**: 0020 → color_m_mode category
- **2D imaging codes**: 0001,0011 → frame-based classification with Color Doppler detection

#### Step 6: Color Doppler Detection (For frame-based categories)
- **Primary: UltrasoundColorDataPresent** (0018,9070) - Definitive indicator (0 or 1)
- **Applied to**: Multi-frame and 2D single-frame categories only

#### Secondary Tags (Lower Priority):
- **Modality** (0008,0060) - Confirms ultrasound imaging (always "US")
- **Image Type** (0008,0008) - General image type info
- **Overlay Data** (60xx,3000) - Detects overlay annotations

#### Final Classification Approach (v2.4):
- ✅ **Exclusion check**: ImageType[10]=="I1" or ImageType[2]=="INVALID" (HIGHEST PRIORITY)
- ✅ **Tissue Doppler detection**: ImageType[3] in ["0019","0003"] (SECOND PRIORITY)
- ✅ **Side-by-side layout detection**: B-mode + Color Doppler regions analysis (THIRD PRIORITY)
- ✅ **Frame count split**: Multi-frame vs Single-frame (based on NumberOfFrames)
- ✅ **ImageType[3] classification**: Specific vendor codes determine category
- ✅ **Color Doppler detection**: UltrasoundColorDataPresent for frame-based categories
- ✅ **Priority order**: Exclusion → Tissue Doppler → Side-by-side → Frame count → ImageType[3] codes

#### Key Algorithm Additions (v2.4):

**Side-by-side Layout Detection Algorithm:**
- **Input analysis**: SequenceOfUltrasoundRegions with exactly 2 regions
- **Region type identification**: RegionDataType=1 (B-mode) and RegionDataType=2 (Color Doppler)
- **Spatial relationship analysis**:
  - **Horizontal layout**: Regions side-by-side with <100px gap and vertical overlap
  - **Vertical layout**: Regions top-bottom with <100px gap and horizontal overlap
- **Clinical significance**: Separates comparative displays from standard cine loops
- **Priority**: Takes precedence over multi_frame_with_doppler classification

**Example detection**:
```
File: 1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm
- 73 frames (cine loop)
- Region 1: B-mode (0,50) to (456,686) - 456x636px 
- Region 2: Color Doppler (497,50) to (954,686) - 457x636px
- Layout: Side-by-side with 41px gap
- Classification: side_by_side_doppler (not multi_frame_with_doppler)
```

#### Key Discoveries:

**Complete ImageType[3] Vendor Code List:**
- **0001**: 2D Imaging (Multi-frame without Color Doppler OR 2D Single-frame without Color Doppler)
- **0002**: M-Mode → **Classified as CW Doppler** (expanded definition)
- **0003**: CW Doppler (Continuous Wave) → **Classified as Tissue Doppler** (moved from CW Doppler)
- **0004**: CW Doppler variant → **Classified as CW Doppler**
- **0005**: CW Doppler variant → **Classified as CW Doppler**
- **0008**: PW Doppler (Pulsed Wave) → **Classified as PW Doppler** (expanded definition)
- **0009**: PW Doppler variant → **Classified as PW Doppler**
- **0010**: Color Doppler
- **0011**: Multi-frame with Color Doppler OR 2D Single-frame with Color Doppler (unless side-by-side detected)
- **0015**: CW Doppler variant → **Classified as CW Doppler**
- **0019**: *Tissue Doppler/Measurements* → **TISSUE DOPPLER category** (HIGH PRIORITY)
- **0020**: Color M-Mode → **Classified as Color M-Mode**
- **0040**: 3D Rendering
- **0100**: Color Power Mode
- **0200**: Tissue Characterization
- **0400**: Spatially-related frames

**Updated Classification Logic (v2.4):**
- **Exclusion**: ImageType[10]=="I1" or ImageType[2]=="INVALID" → excluded category
- **Tissue Doppler detection**: Codes '0019','0003' → tissue_doppler category (renamed from annotations)
- **Side-by-side detection**: SequenceOfUltrasoundRegions analysis → side_by_side_doppler category
- **CW Doppler**: Codes '0002','0004','0005','0015' → cw_doppler category (0003 moved to tissue doppler)
- **PW Doppler**: Codes '0008','0009' → pw_doppler category (expanded)
- **Color Doppler detection**: UltrasoundColorDataPresent for frame-based categories
- **Measurement data**: Embedded in image pixels (e.g., "TR Vmax 2.92 m/s"), not extractable from DICOM headers
- **SequenceOfUltrasoundRegions**: Contains spatial layout data for side-by-side detection and calibration data

#### Removed Classifications:
- ❌ **M-mode specific categories** - M-mode now falls into single-frame categories
- ❌ **Side-by-side comparisons** - Multi-frame files are cine loops
- ❌ **Misleading color indicators** - SamplesPerPixel, PhotometricInterpretation unreliable

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