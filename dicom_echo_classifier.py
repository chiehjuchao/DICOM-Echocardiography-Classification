#!/usr/bin/env python3
"""
DICOM Echocardiography Classification Script

This script loads DICOM files from the 2023Examples directory and classifies them into categories:
1. 2D echo images without Color Doppler
2. 2D echo images with Color Doppler  
3. M-mode Doppler signals images
4. M-mode 2D images
5. Images with side-by-side comparison
6. Images with annotations/measurements

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
        '2d_no_doppler': '2D echo images without Color Doppler',
        '2d_with_doppler': '2D echo images with Color Doppler',
        'mmode_doppler': 'M-mode Doppler signals images',
        'mmode_2d': 'M-mode 2D images',
        'side_by_side': 'Images with side-by-side comparison',
        'with_annotations': 'Images with annotations/measurements'
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
    
    def has_annotations(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if DICOM file contains annotations or measurements
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if annotations are present
        """
        # Check for various annotation indicators
        annotation_indicators = [
            metadata.get('has_graphic_annotation', False),
            metadata.get('has_text_object', False),
            metadata.get('has_overlay', False),
            'ANNOTATION' in str(metadata.get('image_type', [])).upper(),
            'MEASUREMENT' in str(metadata.get('series_description', '')).upper(),
            'CALIBRATION' in str(metadata.get('series_description', '')).upper(),
            'REPORT' in str(metadata.get('series_description', '')).upper()
        ]
        
        return any(annotation_indicators)
    
    def has_color_doppler(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains Color Doppler information
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if Color Doppler is present
        """
        color_indicators = [
            metadata.get('samples_per_pixel', 1) > 1,
            metadata.get('photometric_interpretation', '') in ['RGB', 'YBR_FULL', 'YBR_PARTIAL_420'],
            metadata.get('ultrasound_color_data_present', 0) == 1,
            'COLOR' in str(metadata.get('image_type', [])).upper(),
            'DOPPLER' in str(metadata.get('series_description', '')).upper() and 'COLOR' in str(metadata.get('series_description', '')).upper(),
            'CFM' in str(metadata.get('series_description', '')).upper(),  # Color Flow Mapping
        ]
        
        return any(color_indicators)
    
    def is_mmode(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image is M-mode
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if M-mode
        """
        mmode_indicators = [
            'M_MODE' in str(metadata.get('image_type', [])).upper(),
            'M-MODE' in str(metadata.get('series_description', '')).upper(),
            'MMODE' in str(metadata.get('series_description', '')).upper(),
            'TM' in str(metadata.get('image_type', [])).upper(),  # Time Motion
            metadata.get('acquisition_type', '') == 'M_MODE'
        ]
        
        return any(mmode_indicators)
    
    def has_doppler_signals(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains Doppler signal information
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if Doppler signals are present
        """
        doppler_indicators = [
            'DOPPLER' in str(metadata.get('image_type', [])).upper(),
            'DOPPLER' in str(metadata.get('series_description', '')).upper(),
            'PW' in str(metadata.get('series_description', '')).upper(),  # Pulsed Wave
            'CW' in str(metadata.get('series_description', '')).upper(),  # Continuous Wave
            'SPECTRAL' in str(metadata.get('series_description', '')).upper(),
        ]
        
        return any(doppler_indicators)
    
    def is_side_by_side(self, ds: pydicom.Dataset, metadata: Dict) -> bool:
        """
        Check if image contains side-by-side comparison
        
        Args:
            ds: pydicom Dataset
            metadata: Extracted metadata
            
        Returns:
            True if side-by-side comparison
        """
        comparison_indicators = [
            metadata.get('number_of_frames', 1) > 1,
            'COMPARE' in str(metadata.get('series_description', '')).upper(),
            'DUAL' in str(metadata.get('series_description', '')).upper(),
            'SPLIT' in str(metadata.get('series_description', '')).upper(),
            'SIDE' in str(metadata.get('series_description', '')).upper(),
            # Check for unusually wide images that might indicate side-by-side
            metadata.get('columns', 0) > metadata.get('rows', 0) * 1.5 if metadata.get('rows', 0) > 0 else False
        ]
        
        return any(comparison_indicators)
    
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
        
        # Classification logic with priority order
        reasoning_parts = []
        confidence = 0.5  # Base confidence
        
        # Priority 1: Check for annotations (highest priority)
        if self.has_annotations(ds, metadata):
            category = 'with_annotations'
            reasoning_parts.append("Contains annotations/measurements")
            confidence = 0.9
        
        # Priority 2: Check for M-mode with Doppler
        elif self.is_mmode(ds, metadata) and self.has_doppler_signals(ds, metadata):
            category = 'mmode_doppler'
            reasoning_parts.append("M-mode with Doppler signals")
            confidence = 0.85
        
        # Priority 3: Check for M-mode 2D
        elif self.is_mmode(ds, metadata):
            category = 'mmode_2d'
            reasoning_parts.append("M-mode imaging")
            confidence = 0.8
        
        # Priority 4: Check for side-by-side comparison
        elif self.is_side_by_side(ds, metadata):
            category = 'side_by_side'
            reasoning_parts.append("Side-by-side comparison layout")
            confidence = 0.75
        
        # Priority 5: Check for 2D with Color Doppler
        elif self.has_color_doppler(ds, metadata):
            category = '2d_with_doppler'
            reasoning_parts.append("2D imaging with Color Doppler")
            confidence = 0.8
        
        # Default: 2D without Color Doppler
        else:
            category = '2d_no_doppler'
            reasoning_parts.append("Standard 2D echo imaging")
            confidence = 0.7
        
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
    
    def process_directory(self, progress_callback=None) -> None:
        """
        Process all DICOM files in the directory tree
        
        Args:
            progress_callback: Optional callback function for progress updates
        """
        self.logger.info(f"Starting DICOM classification in directory: {self.root_dir}")
        
        # Find all DICOM files
        dicom_files = []
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                if file.lower().endswith('.dcm') or not '.' in file:  # DICOM files often have no extension
                    dicom_files.append(os.path.join(root, file))
        
        self.logger.info(f"Found {len(dicom_files)} potential DICOM files")
        
        # Process each file
        for i, file_path in enumerate(dicom_files):
            if progress_callback:
                progress_callback(i, len(dicom_files))
            
            classification = self.classify_dicom(file_path)
            if classification:
                self.classifications.append(classification)
                self.stats[classification.category] += 1
                
                if i % 100 == 0:  # Log progress every 100 files
                    self.logger.info(f"Processed {i}/{len(dicom_files)} files")
        
        self.logger.info("Classification complete!")
        self.logger.info("Statistics:")
        for category, count in self.stats.items():
            self.logger.info(f"  {self.CATEGORIES[category]}: {count}")
    
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
    
    # Process files with progress indicator
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end='', flush=True)
    
    try:
        classifier.process_directory(progress_callback)
        print()  # New line after progress
        classifier.save_results()
        
        print("\nClassification Summary:")
        for category, count in classifier.stats.items():
            print(f"  {classifier.CATEGORIES[category]}: {count}")
        
    except KeyboardInterrupt:
        print("\nClassification interrupted by user")
    except Exception as e:
        print(f"Error during classification: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()