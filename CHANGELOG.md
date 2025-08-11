# CHANGELOG

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