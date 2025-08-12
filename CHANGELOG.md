# CHANGELOG

## [2.4.0] - 2025-08-12

### Major Enhancement - Side-by-side Detection & Tissue Doppler Classification
- **🎯 Added side-by-side B-mode + Color Doppler detection** using SequenceOfUltrasoundRegions analysis
- **🔬 Renamed annotations to Tissue Doppler classification** (ImageType[3] = 0019, 0003)
- **📊 Expanded to 10 classification categories** with enhanced spatial analysis
- **🏥 Improved clinical accuracy** by separating comparative displays from cine loops

### New Features
- **Side-by-side detection algorithm**: Analyzes ultrasound regions for adjacent B-mode and Color Doppler layouts
- **Tissue Doppler classification**: ImageType[3] codes 0019 and 0003 now classified as tissue doppler
- **Enhanced spatial analysis**: Detects horizontal/vertical layouts with gap and overlap calculations
- **New test script**: `test_side_by_side.py` for validating side-by-side detection

### Classification Categories (v2.4 - 10 categories)
1. **Excluded Images** - Invalid images (ImageType[10]=="I1" or ImageType[2]=="INVALID")
2. **Tissue Doppler (0019,0003)** - Tissue Doppler imaging modes (HIGH PRIORITY)
3. **Side-by-side B-mode + Color Doppler** - Adjacent regions in same image (HIGH PRIORITY)
4. **Multi-frame with Color Doppler (0011)** - Cine loops with color flow (excluding side-by-side)
5. **Multi-frame without Color Doppler (0001)** - Grayscale cine loops
6. **2D Single-frame without Color Doppler (0001)** - Standard 2D images
7. **2D Single-frame with Color Doppler (0011)** - Static color flow images
8. **CW Doppler (0002,0004,0005,0015)** - Continuous Wave Doppler (0003 moved to tissue doppler)
9. **PW Doppler (0008,0009)** - Pulsed Wave Doppler spectrograms
10. **Color M-Mode (0020)** - M-Mode with color flow overlay

### Changed
- **Classification priority**: Exclusion → Tissue Doppler → Side-by-side → Frame count → ImageType[3]
- **ImageType[3] code 0003**: Moved from CW Doppler to Tissue Doppler category
- **Side-by-side detection**: Takes precedence over multi_frame_with_doppler classification
- **Documentation**: Updated to v2.4 with comprehensive algorithm descriptions

### Example Side-by-side Detection
```
File: 1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm
- Layout: B-mode (left) + Color Doppler (right) with 41px gap
- 73 frames cine loop → side_by_side_doppler (not multi_frame_with_doppler)
- Clinical use: Combined anatomical and hemodynamic assessment
```

## [2.2.0] - 2025-08-11

### Major Simplification - Frame-Based Classification
- **🎯 Primary classification**: Multi-frame vs Single-frame (based on NumberOfFrames)
- **🎨 Secondary classification**: Color Doppler vs No Color Doppler
- **📝 Annotations as override**: Lowest priority special case
- **🔧 M-mode handling**: Automatically falls into single-frame categories
- **📊 Simplified to 5 clear categories** with intuitive logic

### Classification Categories (Final)
1. Multi-frame with Color Doppler
2. Multi-frame without Color Doppler  
3. Single-frame with Color Doppler
4. Single-frame without Color Doppler
5. Images with annotations/measurements (lowest priority override)

### Changed
- **Classification logic**: Frame count → Color Doppler → Annotations
- **Removed M-mode specific detection** - M-mode images now classified as single-frame
- **Simplified priority system** - much cleaner decision tree
- **Lower annotation confidence** (0.75) as it's now lowest priority

### Removed
- `is_mmode()` and `has_doppler_signals()` methods
- Complex M-mode and Doppler-specific classification logic
- Multi-step priority hierarchies

## [2.1.0] - 2025-08-11

### Major Classification Updates
- **🎯 Prioritized annotation detection** as the primary classification step (highest priority)
- **🗑️ Removed side-by-side comparison category** - these were typically multi-frame cine loops
- **📊 Reduced to 5 categories** with clearer priority hierarchy
- **🔍 Enhanced annotation detection** with improved confidence scoring

### Changed
- **Classification priority order**: Annotations → Color Doppler → M-mode+Doppler → M-mode → 2D
- **Higher confidence scores** for annotation detection (0.95)
- **Removed `is_side_by_side()` method** and related logic
- Updated documentation to reflect 5-category system

### Classification Categories (New Order)
1. Images with annotations/measurements (priority 1)
2. 2D echo images with Color Doppler (priority 2)  
3. M-mode Doppler signals images (priority 3)
4. M-mode 2D images (priority 4)
5. 2D echo images without Color Doppler (default)

## [2.0.0] - 2025-01-11

### Major Updates - Corrected Classification Logic
- **🔧 Fixed classification logic** based on actual DICOM header analysis
- **📊 Analyzed actual dataset** to understand vendor-specific patterns
- **🎯 Corrected Color Doppler detection** using `UltrasoundColorDataPresent` instead of `SamplesPerPixel`
- **📹 Fixed multi-frame classification** - identified as cine loops, not side-by-side comparisons

### Added
- `save_images.py` - Save DICOM images as PNG files for visual validation
- `utils/examine_headers.py` - Analyze DICOM headers from dataset
- `utils/create_corrected_flowchart.py` - Generate corrected classification flowchart
- `analysis/` directory with header analysis and corrected flowchart
- Detailed header analysis documentation

### Changed
- **Classification priority**: Now uses `ImageType[3]` vendor codes as primary classifier
- **Color Doppler detection**: Uses `UltrasoundColorDataPresent` (0018,9070) instead of color space
- **Multi-frame handling**: Correctly identifies cine loops vs true side-by-side
- Updated documentation with dataset-specific findings
- Reorganized file structure with `utils/` and `analysis/` directories

### Removed
- `test_classifier.py` - Outdated interactive test script
- `view_images.py` - Replaced by `save_images.py`
- `create_flowchart.py` - Replaced by corrected version
- Outdated analysis files and flowcharts

### Dataset Findings
- **ImageType codes found**:
  - `0001`, `0011`: Multi-frame cine loops (60% of sample)  
  - `0005`, `0009`, `0015`, `0019`: Static single images (40% of sample)
- **All files**: 758x1016 pixels, Modality=US, SamplesPerPixel=3
- **SeriesDescription**: Empty for all files
- **UltrasoundColorDataPresent**: 0 or 1 (true Color Doppler indicator)

## [1.0.0] - 2025-01-11

### Initial Release
- Basic DICOM classification system
- 6 classification categories
- Interactive and non-interactive testing
- CSV/JSON output formats
- Virtual environment setup