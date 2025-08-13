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
        'side_by_side_doppler': 'Side-by-side B-mode + Color Doppler'
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
        
        # Image dimensions and properties
        metadata['rows'] = getattr(ds, 'Rows', 0)
        metadata['columns'] = getattr(ds, 'Columns', 0)
        metadata['number_of_frames'] = getattr(ds, 'NumberOfFrames', 1)
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
        return metadata.get('number_of_frames', 1) > 1
    
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
    
    def is_side_by_side_doppler(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains side-by-side B-mode + Color Doppler regions
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if side-by-side B-mode + Color Doppler layout is detected
        """
        # Check if SequenceOfUltrasoundRegions exists
        if not hasattr(ds, 'SequenceOfUltrasoundRegions'):
            return False
        
        regions = ds.SequenceOfUltrasoundRegions
        
        # Need exactly 2 regions for side-by-side comparison
        if len(regions) != 2:
            return False
        
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
        
        b_region = b_mode_regions[0]
        d_region = doppler_regions[0]
        
        # Get coordinates
        b_x1 = getattr(b_region, 'RegionLocationMinX0', 0)
        b_x2 = getattr(b_region, 'RegionLocationMaxX1', 0)
        b_y1 = getattr(b_region, 'RegionLocationMinY0', 0)
        b_y2 = getattr(b_region, 'RegionLocationMaxY1', 0)
        
        d_x1 = getattr(d_region, 'RegionLocationMinX0', 0)
        d_x2 = getattr(d_region, 'RegionLocationMaxX1', 0)
        d_y1 = getattr(d_region, 'RegionLocationMinY0', 0)
        d_y2 = getattr(d_region, 'RegionLocationMaxY1', 0)
        
        # Check if horizontally adjacent (side-by-side)
        horizontal_gap = min(abs(b_x2 - d_x1), abs(d_x2 - b_x1))
        
        # Check for vertical overlap (needed for side-by-side layout)
        y_overlap = not (b_y2 < d_y1 or d_y2 < b_y1)
        
        # Side-by-side criteria: close horizontal gap + vertical overlap
        if horizontal_gap < 100 and y_overlap:
            return True
        
        # Check if vertically adjacent (top-bottom) as alternative layout
        vertical_gap = min(abs(b_y2 - d_y1), abs(d_y2 - b_y1))
        x_overlap = not (b_x2 < d_x1 or d_x2 < b_x1)
        
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