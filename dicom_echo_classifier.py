#!/usr/bin/env python3
"""
DICOM Echocardiography Classification Script

This script loads DICOM files from the 2023Examples directory and classifies them into 10 categories:
1. Multi-frame with Color Doppler (0011)
2. Multi-frame without Color Doppler (0001) 
3. 2D Single-frame without Color Doppler (0001)
4. 2D Single-frame with Color Doppler (0011)
5. CW Doppler (0002,0004,0005,0015)
6. PW Doppler (0008,0009)
7. Color M-Mode (0020)
8. Tissue Doppler (0019,0003)
9. Side-by-side B-mode + Color Doppler
10. Excluded images (ImageType[10]=="I1" or ImageType[2]=="INVALID")

Author: Claude Code Assistant
"""

import os
import sys
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    import pydicom
    from pydicom import dcmread
    from pydicom.errors import InvalidDicomError
except ImportError:
    print("Error: pydicom library not found. Please install with: pip install pydicom")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# Import cardiac phase detection functionality
try:
    from cardiac_phase_detector import detect_cardiac_phases_for_multiframe, CardiacPhaseDetector
except ImportError:
    print("Warning: cardiac_phase_detector.py not found. Cardiac phase detection will be disabled.")
    detect_cardiac_phases_for_multiframe = None
    CardiacPhaseDetector = None


@dataclass
class DicomClassification:
    """Data class to store classification results"""
    file_path: str
    category: str
    confidence: float
    reasoning: str
    metadata: Dict


class EchoCardiographyClassifier:
    """DICOM Echocardiography Image Classifier"""
    
    CATEGORIES = {
        'excluded': 'Excluded (ImageType[10]==I1 or ImageType[2]==INVALID)',
        'multi_frame_with_doppler': 'Multi-frame with Color Doppler (0011)',
        'multi_frame_no_doppler': 'Multi-frame without Color Doppler (0001)',
        '2d_single_no_doppler': '2D Single-frame without Color Doppler (0001)',
        '2d_single_with_doppler': '2D Single-frame with Color Doppler (0011)',
        'cw_doppler': 'CW Doppler (0002,0004,0005,0015)', 
        'pw_doppler': 'PW Doppler (0008,0009)',
        'color_m_mode': 'Color M-Mode (0020)',
        'tissue_doppler': 'Tissue Doppler (0019,0003)',
        'side_by_side_doppler': 'Side-by-side B-mode + Color Doppler OR B-mode + B-mode'
    }
    
    def __init__(self, root_dir: str, output_dir: str = None):
        """
        Initialize the classifier
        
        Args:
            root_dir: Root directory containing DICOM files
            output_dir: Directory to save classification results
        """
        self.root_dir = Path(root_dir)
        self.output_dir = Path(output_dir) if output_dir else self.root_dir / "classification_results"
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'classification.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.classifications = []
        self.stats = defaultdict(int)
    
    def read_dicom_headers(self, file_path: str) -> Optional[pydicom.Dataset]:
        """
        Read DICOM file and extract headers
        
        Args:
            file_path: Path to DICOM file
            
        Returns:
            pydicom.Dataset or None if file cannot be read
        """
        try:
            ds = dcmread(file_path, force=True)
            return ds
        except (InvalidDicomError, Exception) as e:
            self.logger.warning(f"Cannot read DICOM file {file_path}: {e}")
            return None
    
    def extract_metadata(self, ds: pydicom.Dataset) -> Dict:
        """
        Extract relevant metadata from DICOM dataset
        
        Args:
            ds: pydicom Dataset
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Basic image information
        metadata['modality'] = getattr(ds, 'Modality', '')
        metadata['image_type'] = getattr(ds, 'ImageType', [])
        metadata['series_description'] = getattr(ds, 'SeriesDescription', '')
        metadata['study_description'] = getattr(ds, 'StudyDescription', '')
        metadata['acquisition_type'] = getattr(ds, 'AcquisitionType', '')
        
        # Extract manufacturer information
        manufacturer = getattr(ds, 'Manufacturer', '').strip() if hasattr(ds, 'Manufacturer') else ''
        metadata['manufacturer'] = manufacturer
        
        # Extract Philips-specific tags
        if 'PHILIPS' in manufacturer.upper():
            # Philips US Imaging DD tags
            metadata['philips_dd_041'] = getattr(ds, 'get((0x200D, 0x0038), None)', None)  # Color Doppler indicator
            metadata['philips_dd_066'] = getattr(ds, 'get((0x200D, 0x0051), None)', None)  # Non-color indicator
            
            # Try to get the tags directly
            try:
                if (0x200D, 0x0038) in ds:
                    metadata['philips_dd_041'] = str(ds[0x200D, 0x0038].value)
                else:
                    metadata['philips_dd_041'] = None
            except:
                metadata['philips_dd_041'] = None
                
            try:
                if (0x200D, 0x0051) in ds:
                    metadata['philips_dd_066'] = str(ds[0x200D, 0x0051].value)
                else:
                    metadata['philips_dd_066'] = None
            except:
                metadata['philips_dd_066'] = None
        
        # Image dimensions and properties
        metadata['rows'] = getattr(ds, 'Rows', 0)
        metadata['columns'] = getattr(ds, 'Columns', 0)
        # Ensure number_of_frames is always an integer
        num_frames = getattr(ds, 'NumberOfFrames', 1)
        if isinstance(num_frames, str):
            try:
                num_frames = int(num_frames)
            except ValueError:
                num_frames = 1
        metadata['number_of_frames'] = num_frames
        metadata['samples_per_pixel'] = getattr(ds, 'SamplesPerPixel', 1)
        metadata['photometric_interpretation'] = getattr(ds, 'PhotometricInterpretation', '')
        metadata['color_space'] = getattr(ds, 'ColorSpace', '')
        
        # Check for annotations and overlays
        metadata['has_graphic_annotation'] = hasattr(ds, 'GraphicAnnotationSequence')
        metadata['has_text_object'] = hasattr(ds, 'TextObjectSequence')
        metadata['has_overlay'] = any(hasattr(ds, f'OverlayData{i:04X}') for i in range(0x6000, 0x60FF, 2))
        
        # Ultrasound specific tags
        metadata['ultrasound_color_data_present'] = getattr(ds, 'UltrasoundColorDataPresent', 0)
        metadata['frame_type'] = getattr(ds, 'FrameType', [])
        
        return metadata
    
    def is_multi_frame(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if DICOM file is multi-frame (cine loop)
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if multi-frame
        """
        num_frames = metadata.get('number_of_frames', 1)
        # Convert to int if it's a string
        if isinstance(num_frames, str):
            try:
                num_frames = int(num_frames)
            except ValueError:
                num_frames = 1
        return num_frames > 1
    
    def has_annotations(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if DICOM file contains annotations or measurements
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if annotations are present
        """
        # Primary vendor-specific annotation indicators (ImageType[3])
        # Updated: Only 0019 is used for tissue doppler detection
        # 0003 is now also part of tissue doppler detection
        # This method is now used only for fallback detection
        image_type = metadata.get('image_type', [])
        if len(image_type) >= 4:
            vendor_code = image_type[3]
            # Fallback annotation codes (not used in main classification)
            annotation_codes = ['0005']  # Fallback annotation indicator
            if vendor_code in annotation_codes:
                return True
        
        # Fallback: Standard DICOM annotation indicators
        standard_indicators = [
            metadata.get('has_graphic_annotation', False),
            metadata.get('has_text_object', False),
            metadata.get('has_overlay', False),
            'ANNOTATION' in str(metadata.get('image_type', [])).upper(),
            'MEASUREMENT' in str(metadata.get('series_description', '')).upper(),
            'CALIBRATION' in str(metadata.get('series_description', '')).upper(),
            'REPORT' in str(metadata.get('series_description', '')).upper()
        ]
        
        return any(standard_indicators)
    
    def has_color_doppler(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains Color Doppler information
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if Color Doppler is present
        """
        # Primary and most reliable indicator for Color Doppler
        if metadata.get('ultrasound_color_data_present', 0) == 1:
            return True
        
        # Secondary: Check ImageType[3] vendor codes for Color Doppler modes
        image_type = metadata.get('image_type', [])
        if len(image_type) >= 4:
            vendor_code = image_type[3]
            # Color Doppler related codes from comprehensive list
            color_doppler_codes = ['0010', '0020', '0100']  # Color Doppler, Color M-Mode, Color Power Mode
            if vendor_code in color_doppler_codes:
                return True
        
        # Fallback indicators (less reliable)
        fallback_indicators = [
            'COLOR' in str(metadata.get('image_type', [])).upper(),
            'DOPPLER' in str(metadata.get('series_description', '')).upper() and 'COLOR' in str(metadata.get('series_description', '')).upper(),
            'CFM' in str(metadata.get('series_description', '')).upper(),  # Color Flow Mapping
        ]
        
        return any(fallback_indicators)
    
    def has_doppler_spectrum_regions(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains Doppler spectrum regions (RegionDataType = 4)
        Enhanced logic: Exactly 2 regions where region 2 has RegionDataType = 4
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if Doppler spectrum regions are detected (2 regions, region 2 = RegionDataType 4)
        """
        # Check if SequenceOfUltrasoundRegions exists
        if not hasattr(ds, 'SequenceOfUltrasoundRegions'):
            return False
        
        regions = ds.SequenceOfUltrasoundRegions
        
        # Must have exactly 2 regions for two-region CW Doppler
        if len(regions) != 2:
            return False
        
        # Check if region 2 (index 1) has RegionDataType = 4 (Doppler spectrum)
        region2 = regions[1]
        data_type_2 = getattr(region2, 'RegionDataType', 0)
        
        if data_type_2 == 4:  # Doppler spectrum in region 2
            return True
        
        return False
    
    def get_primary_region_type(self, ds: pydicom.Dataset, metadata: Dict) -> Optional[int]:
        """
        Get the primary region data type for single-region images
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            RegionDataType value or None if not available
        """
        # Check if SequenceOfUltrasoundRegions exists
        if not hasattr(ds, 'SequenceOfUltrasoundRegions'):
            return None
        
        regions = ds.SequenceOfUltrasoundRegions
        
        # For single-region images, return the first region's data type
        if len(regions) == 1:
            region = regions[0]
            return getattr(region, 'RegionDataType', None)
        
        return None
    
    def is_side_by_side_doppler(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains side-by-side regions (B-mode + Color Doppler OR B-mode + B-mode)
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if side-by-side layout is detected (B-mode + Color Doppler OR B-mode + B-mode)
        """
        # Check if SequenceOfUltrasoundRegions exists
        if not hasattr(ds, 'SequenceOfUltrasoundRegions'):
            return False
        
        regions = ds.SequenceOfUltrasoundRegions
        
        # Need exactly 2 regions for side-by-side comparison
        if len(regions) != 2:
            return False
        
        manufacturer = metadata.get('manufacturer', '').upper()
        
        if 'PHILIPS' in manufacturer:
            # For Philips: Enhanced logic for both B-mode + Color Doppler and B-mode + B-mode
            region1 = regions[0]
            region2 = regions[1]
            
            data_type_1 = getattr(region1, 'RegionDataType', 0)
            data_type_2 = getattr(region2, 'RegionDataType', 0)
            
            # Exclude combinations with Doppler spectrum (RegionDataType = 4)
            if data_type_1 == 4 or data_type_2 == 4:
                return False  # This is 2D + Doppler spectrum combination, not side-by-side
            
            # Accept these combinations as side-by-side:
            # 1. B-mode + B-mode (RegionDataType = 1, 1)
            # 2. B-mode + Color Doppler (RegionDataType = 1, 2 with DD 066)
            
            # Case 1: B-mode + B-mode (both regions are B-mode)
            if data_type_1 == 1 and data_type_2 == 1:
                # Both are B-mode regions - check spatial layout only
                pass  # Continue to spatial analysis below
            
            # Case 2: B-mode + Color Doppler (original logic with DD 066 requirement)
            elif (data_type_1 == 1 and data_type_2 == 2) or (data_type_1 == 2 and data_type_2 == 1):
                # Must have DD 066 tag for B-mode + Color Doppler
                dd_066 = metadata.get('philips_dd_066')
                has_dd_066 = dd_066 is not None and 'Philips US Imaging DD 066' in str(dd_066)
                
                if not has_dd_066:
                    return False  # Missing DD 066, so not side-by-side B-mode + Color Doppler
            else:
                # Other combinations not supported
                return False
        else:
            # For GE/TOSHIBA: Use original logic with RegionDataType requirement
            # Count B-mode and Doppler regions
            b_mode_regions = []
            doppler_regions = []
            
            for region in regions:
                data_type = getattr(region, 'RegionDataType', 0)
                if data_type == 1:  # B-mode (grayscale)
                    b_mode_regions.append(region)
                elif data_type == 2:  # Color Doppler
                    doppler_regions.append(region)
            
            # Must have exactly 1 B-mode and 1 Color Doppler region
            if len(b_mode_regions) != 1 or len(doppler_regions) != 1:
                return False
            
            region1 = b_mode_regions[0]
            region2 = doppler_regions[0]
        
        # Get coordinates for both regions
        r1_x1 = getattr(region1, 'RegionLocationMinX0', 0)
        r1_x2 = getattr(region1, 'RegionLocationMaxX1', 0)
        r1_y1 = getattr(region1, 'RegionLocationMinY0', 0)
        r1_y2 = getattr(region1, 'RegionLocationMaxY1', 0)
        
        r2_x1 = getattr(region2, 'RegionLocationMinX0', 0)
        r2_x2 = getattr(region2, 'RegionLocationMaxX1', 0)
        r2_y1 = getattr(region2, 'RegionLocationMinY0', 0)
        r2_y2 = getattr(region2, 'RegionLocationMaxY1', 0)
        
        # Check if horizontally adjacent (side-by-side)
        horizontal_gap = min(abs(r1_x2 - r2_x1), abs(r2_x2 - r1_x1))
        
        # Check for vertical overlap (needed for side-by-side layout)
        y_overlap = not (r1_y2 < r2_y1 or r2_y2 < r1_y1)
        
        # Side-by-side criteria: close horizontal gap + vertical overlap
        if horizontal_gap < 100 and y_overlap:
            return True
        
        # Check if vertically adjacent (top-bottom) as alternative layout
        vertical_gap = min(abs(r1_y2 - r2_y1), abs(r2_y2 - r1_y1))
        x_overlap = not (r1_x2 < r2_x1 or r2_x2 < r1_x1)
        
        # Top-bottom criteria: close vertical gap + horizontal overlap
        if vertical_gap < 100 and x_overlap:
            return True
        
        return False
    
    def detect_cardiac_phases(self, file_path: str, ds: Optional[pydicom.Dataset] = None) -> Optional[Dict]:
        """
        Detect cardiac phases (end-systolic and end-diastolic frames) for multi-frame images.
        
        Args:
            file_path: Path to DICOM file
            ds: Optional pre-loaded pydicom Dataset
            
        Returns:
            Dictionary containing cardiac phase information, or None if detection fails
        """
        if detect_cardiac_phases_for_multiframe is None:
            self.logger.warning("Cardiac phase detection not available (cardiac_phase_detector.py not found)")
            return None
        
        try:
            # Use pre-loaded dataset if available
            if ds is not None:
                # Check if multi-frame
                num_frames = getattr(ds, 'NumberOfFrames', 1)
                # Convert to int if it's a string
                if isinstance(num_frames, str):
                    try:
                        num_frames = int(num_frames)
                    except ValueError:
                        num_frames = 1
                if num_frames <= 1:
                    return None
                
                # Use CardiacPhaseDetector directly with dataset
                detector = CardiacPhaseDetector(end_systole_percent=0.35, end_diastole_percent=0.95)
                
                # Check for required timing information
                required_tags = [(0x0018, 0x6060), (0x0018, 0x1063)]  # R Wave Times, Frame Time
                missing_tags = [tag for tag in required_tags if tag not in ds]
                
                if missing_tags:
                    self.logger.debug(f"Missing cardiac timing tags in {os.path.basename(file_path)}: {missing_tags}")
                    return None
                
                cardiac_phases = detector.process_dicom_dataset(ds)
                return detector.get_key_frames(cardiac_phases)
            else:
                # Use file path
                return detect_cardiac_phases_for_multiframe(file_path, verbose=False)
                
        except Exception as e:
            self.logger.debug(f"Cardiac phase detection failed for {os.path.basename(file_path)}: {e}")
            return None
    
    
    def classify_dicom(self, file_path: str) -> Optional[DicomClassification]:
        """
        Classify a single DICOM file
        
        Args:
            file_path: Path to DICOM file
            
        Returns:
            DicomClassification object or None if classification fails
        """
        ds = self.read_dicom_headers(file_path)
        if ds is None:
            return None
        
        metadata = self.extract_metadata(ds)
        
        # Route to manufacturer-specific classification
        manufacturer = metadata.get('manufacturer', '').upper()
        
        if 'PHILIPS' in manufacturer:
            return self._classify_philips(ds, metadata, file_path)
        elif 'GE' in manufacturer or 'TOSHIBA' in manufacturer:
            return self._classify_ge_toshiba(ds, metadata, file_path)
        else:
            # Default to GE/TOSHIBA flow for unknown manufacturers
            self.logger.warning(f"Unknown manufacturer '{manufacturer}' in {os.path.basename(file_path)}, using GE/TOSHIBA flow")
            return self._classify_ge_toshiba(ds, metadata, file_path)
        
    def _classify_ge_toshiba(self, ds: pydicom.Dataset, metadata: Dict, file_path: str) -> DicomClassification:
        """
        Classification logic for GE and TOSHIBA manufacturers (original flow)
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            file_path: Path to DICOM file
            
        Returns:
            DicomClassification object
        """
        # Detect cardiac phases for multi-frame images
        cardiac_phases = None
        is_multi = self.is_multi_frame(ds, metadata)
        if is_multi:
            cardiac_phases = self.detect_cardiac_phases(file_path, ds)
            if cardiac_phases:
                metadata['cardiac_phases'] = cardiac_phases
                metadata['has_cardiac_timing'] = True
                metadata['end_systolic_frames'] = cardiac_phases.get('end_systolic_frames', [])
                metadata['end_diastolic_frames'] = cardiac_phases.get('end_diastolic_frames', [])
            else:
                metadata['has_cardiac_timing'] = False
        
        # Classification logic: Exclusion → Annotations → Frame count + ImageType[3]
        reasoning_parts = []
        confidence = 0.8  # Base confidence
        image_type = metadata.get('image_type', [])
        
        # Step 1: Check for exclusion criteria first (highest priority)
        if (len(image_type) > 10 and image_type[10] == 'I1') or (len(image_type) > 2 and image_type[2] == 'INVALID'):
            category = 'excluded'
            reasoning_parts.append(f"Excluded image (ImageType: {image_type})")
            confidence = 0.95
        # Step 2: Check for tissue doppler (0019, 0003)
        elif len(image_type) >= 4 and image_type[3] in ['0019', '0003']:
            category = 'tissue_doppler'
            reasoning_parts.append(f"Tissue Doppler (ImageType {image_type[3]})")
            confidence = 0.95
        # Step 3: Check for side-by-side B-mode + Color Doppler layout
        elif self.is_side_by_side_doppler(ds, metadata):
            category = 'side_by_side_doppler'
            reasoning_parts.append("Side-by-side B-mode + Color Doppler layout detected")
            confidence = 0.9
        else:
            # Step 4: Classify by frame count and ImageType[3]
            is_multi = self.is_multi_frame(ds, metadata)
            vendor_code = image_type[3] if len(image_type) >= 4 else None
            
            if is_multi:
                # Multi-frame classification
                if vendor_code == '0011':
                    category = 'multi_frame_with_doppler'
                    reasoning_parts.append(f"Multi-frame with Color Doppler (ImageType 0011, {metadata.get('number_of_frames', 1)} frames)")
                    confidence = 0.9
                elif vendor_code == '0001':
                    category = 'multi_frame_no_doppler'
                    reasoning_parts.append(f"Multi-frame without Color Doppler (ImageType 0001, {metadata.get('number_of_frames', 1)} frames)")
                    confidence = 0.9
                else:
                    # Fallback for unrecognized multi-frame codes
                    category = 'multi_frame_no_doppler'
                    reasoning_parts.append(f"Multi-frame (ImageType {vendor_code or 'unknown'}, {metadata.get('number_of_frames', 1)} frames)")
                    confidence = 0.7
            else:
                # Single-frame classification by ImageType[3]
                if vendor_code == '0001':
                    category = '2d_single_no_doppler'
                    reasoning_parts.append("2D Single-frame without Color Doppler (ImageType 0001)")
                    confidence = 0.9
                elif vendor_code == '0011':
                    category = '2d_single_with_doppler'
                    reasoning_parts.append("2D Single-frame with Color Doppler (ImageType 0011)")
                    confidence = 0.9
                elif vendor_code in ['0002', '0004', '0005', '0015']:
                    category = 'cw_doppler'
                    reasoning_parts.append(f"CW Doppler (ImageType {vendor_code})")
                    confidence = 0.9
                elif vendor_code in ['0008', '0009']:
                    category = 'pw_doppler'
                    reasoning_parts.append(f"PW Doppler (ImageType {vendor_code})")
                    confidence = 0.9
                elif vendor_code == '0020':
                    category = 'color_m_mode'
                    reasoning_parts.append("Color M-Mode (ImageType 0020)")
                    confidence = 0.9
                else:
                    # Default for unrecognized single-frame codes
                    category = '2d_single_no_doppler'
                    reasoning_parts.append(f"Single-frame (ImageType {vendor_code or 'unknown'}) - defaulted to 2D")
                    confidence = 0.6
        
        # Add additional reasoning based on metadata
        if metadata.get('modality') == 'US':
            reasoning_parts.append("Ultrasound modality")
            confidence += 0.1
        
        if 'ECHO' in str(metadata.get('study_description', '')).upper():
            reasoning_parts.append("Echocardiography study")
            confidence += 0.05
        
        reasoning = "; ".join(reasoning_parts)
        confidence = min(confidence, 1.0)  # Cap at 1.0
        
        return DicomClassification(
            file_path=file_path,
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
    
    def _classify_philips(self, ds: pydicom.Dataset, metadata: Dict, file_path: str) -> DicomClassification:
        """
        Classification logic for Philips manufacturers
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            file_path: Path to DICOM file
            
        Returns:
            DicomClassification object
        """
        # Detect cardiac phases for multi-frame images
        cardiac_phases = None
        is_multi = self.is_multi_frame(ds, metadata)
        if is_multi:
            cardiac_phases = self.detect_cardiac_phases(file_path, ds)
            if cardiac_phases:
                metadata['cardiac_phases'] = cardiac_phases
                metadata['has_cardiac_timing'] = True
                metadata['end_systolic_frames'] = cardiac_phases.get('end_systolic_frames', [])
                metadata['end_diastolic_frames'] = cardiac_phases.get('end_diastolic_frames', [])
            else:
                metadata['has_cardiac_timing'] = False
        
        # Philips-specific classification logic
        reasoning_parts = ["Philips manufacturer detected"]
        confidence = 0.8  # Base confidence
        image_type = metadata.get('image_type', [])
        
        # Step 1: Check for exclusion criteria first (highest priority)
        if (len(image_type) > 10 and image_type[10] == 'I1') or (len(image_type) > 2 and image_type[2] == 'INVALID'):
            category = 'excluded'
            reasoning_parts.append(f"Excluded image (ImageType: {image_type})")
            confidence = 0.95
        # Step 2: Check for side-by-side layout first (before DD tag analysis)
        elif self.is_side_by_side_doppler(ds, metadata):
            category = 'side_by_side_doppler'
            reasoning_parts.append("Philips side-by-side layout detected (B-mode + Color Doppler OR B-mode + B-mode)")
            confidence = 0.9
        # Step 3: Check for Doppler spectrum regions (exactly 2 regions, region 2 = RegionDataType 4)
        elif self.has_doppler_spectrum_regions(ds, metadata):
            category = 'cw_doppler'
            reasoning_parts.append("Philips two-region CW Doppler detected (2 regions, region 2 RegionDataType = 4)")
            confidence = 0.95
        else:
            # Step 4: Philips-specific classification using frame count and DD tags
            
            # Get frame count (Philips stores as string)
            num_frames = metadata.get('number_of_frames', 1)
            if isinstance(num_frames, str):
                try:
                    num_frames = int(num_frames)
                except ValueError:
                    num_frames = 1
            
            is_multi_frame = num_frames > 1
            
            # Get Philips DD tags
            dd_041 = metadata.get('philips_dd_041')  # Color Doppler indicator
            dd_066 = metadata.get('philips_dd_066')  # Non-color indicator
            
            # Determine if it's color doppler or non-color
            has_color_doppler = dd_041 is not None and 'Philips US Imaging DD 041' in str(dd_041)
            has_non_color = dd_066 is not None and 'Philips US Imaging DD 066' in str(dd_066)
            
            if is_multi_frame:
                # Multi-frame classification
                if has_color_doppler:
                    category = 'multi_frame_with_doppler'
                    reasoning_parts.append(f"Philips multi-frame with Color Doppler (DD 041, {num_frames} frames)")
                    confidence = 0.95
                elif has_non_color:
                    category = 'multi_frame_no_doppler'
                    reasoning_parts.append(f"Philips multi-frame without Color Doppler (DD 066, {num_frames} frames)")
                    confidence = 0.95
                else:
                    # Fallback for multi-frame without clear DD tags
                    category = 'multi_frame_no_doppler'
                    reasoning_parts.append(f"Philips multi-frame (no DD tags, {num_frames} frames)")
                    confidence = 0.7
            else:
                # Single-frame classification with enhanced region type analysis
                if has_color_doppler:
                    category = '2d_single_with_doppler'
                    reasoning_parts.append("Philips 2D Single-frame with Color Doppler (DD 041)")
                    confidence = 0.95
                elif has_non_color:
                    category = '2d_single_no_doppler'
                    reasoning_parts.append("Philips 2D Single-frame without Color Doppler (DD 066)")
                    confidence = 0.95
                elif not has_non_color and dd_066 is None:
                    # Enhanced logic: Check region type for images without DD 066 tag
                    primary_region_type = self.get_primary_region_type(ds, metadata)
                    
                    if primary_region_type == 1:  # B-mode region
                        category = '2d_single_no_doppler'
                        reasoning_parts.append("Philips 2D Single-frame B-mode (no DD 066 tag, RegionDataType = 1)")
                        confidence = 0.85
                    elif primary_region_type == 4:  # Doppler spectrum region
                        category = 'cw_doppler'
                        reasoning_parts.append("Philips CW Doppler spectrum (no DD 066 tag, RegionDataType = 4)")
                        confidence = 0.9
                    else:
                        # Fallback for unknown region types without DD tags
                        category = 'cw_doppler'  # Keep original fallback for other spectrum types
                        reasoning_parts.append(f"Philips Doppler spectrum (no DD 066 tag, RegionDataType = {primary_region_type})")
                        confidence = 0.8
                else:
                    # Final fallback for single-frame without clear DD tags
                    category = '2d_single_no_doppler'
                    reasoning_parts.append("Philips single-frame (unclear DD tags)")
                    confidence = 0.6
        
        # Add additional reasoning based on metadata
        if metadata.get('modality') == 'US':
            reasoning_parts.append("Ultrasound modality")
            confidence += 0.1
        
        if 'ECHO' in str(metadata.get('study_description', '')).upper():
            reasoning_parts.append("Echocardiography study")
            confidence += 0.05
        
        reasoning = "; ".join(reasoning_parts)
        confidence = min(confidence, 1.0)  # Cap at 1.0
        
        return DicomClassification(
            file_path=file_path,
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
    
    def _philips_fallback_classification(self, ds: pydicom.Dataset, metadata: Dict, vendor_code: str) -> str:
        """
        Fallback classification for Philips files when vendor codes are not recognized
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            vendor_code: ImageType[3] vendor code
            
        Returns:
            Category string
        """
        # Try alternative Philips-specific detection methods
        
        # Check for Philips-specific tags that might indicate image type
        # These are placeholder checks - would need actual Philips DICOM samples to determine real tags
        
        # Check for color doppler using Philips-specific methods
        if self.has_color_doppler(ds, metadata):
            if self.is_multi_frame(ds, metadata):
                return 'multi_frame_with_doppler'
            else:
                return '2d_single_with_doppler'
        else:
            if self.is_multi_frame(ds, metadata):
                return 'multi_frame_no_doppler'
            else:
                return '2d_single_no_doppler'
    
    def process_directory(self, progress_callback=None, show_progress=True) -> None:
        """
        Process all DICOM files in the directory tree
        
        Args:
            progress_callback: Optional callback function for progress updates
            show_progress: Whether to show tqdm progress bar (default: True)
        """
        self.logger.info(f"Starting DICOM classification in directory: {self.root_dir}")
        
        # Find all DICOM files with progress bar
        print("🔍 Scanning for DICOM files...")
        dicom_files = []
        
        # First pass: count directories for progress estimation
        total_dirs = sum([len(dirs) for root, dirs, files in os.walk(self.root_dir)])
        
        # Second pass: collect files with progress
        if show_progress and total_dirs > 0:
            pbar_scan = tqdm(total=total_dirs, desc="Scanning directories", unit="dirs")
        
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                if file.lower().endswith('.dcm') or not '.' in file:  # DICOM files often have no extension
                    dicom_files.append(os.path.join(root, file))
            
            if show_progress and total_dirs > 0:
                pbar_scan.update(1)
        
        if show_progress and total_dirs > 0:
            pbar_scan.close()
        
        self.logger.info(f"Found {len(dicom_files)} potential DICOM files")
        
        if len(dicom_files) == 0:
            self.logger.warning("No DICOM files found!")
            return
        
        # Process each file with enhanced progress bar
        print(f"📊 Processing {len(dicom_files)} DICOM files...")
        
        if show_progress:
            pbar = tqdm(dicom_files, desc="Classifying", unit="files")
        else:
            pbar = dicom_files
        
        for i, file_path in enumerate(pbar):
            if progress_callback:
                progress_callback(i, len(dicom_files))
            
            classification = self.classify_dicom(file_path)
            if classification:
                self.classifications.append(classification)
                self.stats[classification.category] += 1
                
                # Update progress bar with current stats
                if show_progress and hasattr(pbar, 'set_postfix'):
                    # Show top 3 categories in progress bar
                    top_categories = sorted(self.stats.items(), key=lambda x: x[1], reverse=True)[:3]
                    postfix_dict = {cat[:12]: count for cat, count in top_categories}
                    pbar.set_postfix(postfix_dict)
            
            # Log progress every 1000 files for large datasets
            if (i + 1) % 1000 == 0:
                self.logger.info(f"Processed {i+1}/{len(dicom_files)} files")
        
        if show_progress and hasattr(pbar, 'close'):
            pbar.close()
        
        print("✅ Classification complete!")
        self.logger.info("Classification complete!")
        self.logger.info("Statistics:")
        for category, count in self.stats.items():
            self.logger.info(f"  {self.CATEGORIES[category]}: {count}")
        
        # Print summary statistics
        print(f"\n📈 Classification Summary ({len(self.classifications)} files processed):")
        for category, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.classifications) * 100) if self.classifications else 0
            print(f"  {self.CATEGORIES[category]}: {count} ({percentage:.1f}%)")
    
    def save_results(self) -> None:
        """Save classification results to CSV and JSON files"""
        
        # Save detailed results to JSON
        json_results = []
        for classification in self.classifications:
            json_results.append({
                'file_path': classification.file_path,
                'category': classification.category,
                'category_description': self.CATEGORIES[classification.category],
                'confidence': classification.confidence,
                'reasoning': classification.reasoning,
                'metadata': classification.metadata
            })
        
        json_file = self.output_dir / 'classification_results.json'
        with open(json_file, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        
        # Save summary to CSV
        csv_file = self.output_dir / 'classification_summary.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File Path', 'Category', 'Category Description', 'Confidence', 'Reasoning'])
            
            for classification in self.classifications:
                writer.writerow([
                    classification.file_path,
                    classification.category,
                    self.CATEGORIES[classification.category],
                    f"{classification.confidence:.2f}",
                    classification.reasoning
                ])
        
        # Save statistics
        stats_file = self.output_dir / 'classification_stats.json'
        with open(stats_file, 'w') as f:
            stats_data = {
                'total_files': len(self.classifications),
                'categories': {
                    category: {
                        'count': count,
                        'description': self.CATEGORIES[category],
                        'percentage': (count / len(self.classifications) * 100) if self.classifications else 0
                    }
                    for category, count in self.stats.items()
                }
            }
            json.dump(stats_data, f, indent=2)
        
        self.logger.info(f"Results saved to:")
        self.logger.info(f"  Detailed results: {json_file}")
        self.logger.info(f"  Summary: {csv_file}")
        self.logger.info(f"  Statistics: {stats_file}")


def main():
    """Main function to run the classifier"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Classify DICOM echocardiography images')
    parser.add_argument('input_dir', help='Input directory containing DICOM files')
    parser.add_argument('--output-dir', help='Output directory for results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize classifier
    classifier = EchoCardiographyClassifier(args.input_dir, args.output_dir)
    
    try:
        # Process with enhanced tqdm progress bars
        classifier.process_directory(show_progress=True)
        classifier.save_results()
        
    except KeyboardInterrupt:
        print("\n⚠️  Classification interrupted by user")
    except Exception as e:
        print(f"❌ Error during classification: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()