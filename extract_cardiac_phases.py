#!/usr/bin/env python3
"""
Extract Cardiac Phase Frames from Multi-frame DICOM Files

This script processes multi-frame DICOM echocardiography images and extracts
end-diastolic (ED) and end-systolic (ES) frame numbers for each cardiac cycle.

Output format: ED1: 1, ES1: 15, ED2: 25, ES2: 39, etc.
"""

import os
import sys
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional
import pydicom

try:
    from tqdm import tqdm
except ImportError:
    print("Installing tqdm...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# Import cardiac phase detector
from cardiac_phase_detector import detect_cardiac_phases_for_multiframe, CardiacPhaseDetector


class CardiacPhaseExtractor:
    """
    Extract cardiac phase frames from multi-frame DICOM files and save to files.
    """
    
    def __init__(self, input_dir: str, output_dir: str = None):
        """
        Initialize the extractor.
        
        Args:
            input_dir: Directory containing DICOM files
            output_dir: Directory to save results (default: input_dir/cardiac_phases)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "cardiac_phases"
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {}
        self.stats = {
            'total_files': 0,
            'multiframe_files': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_cycles_detected': 0
        }
    
    def find_multiframe_dicoms(self) -> List[str]:
        """
        Find all multi-frame DICOM files in the input directory.
        
        Returns:
            List of multi-frame DICOM file paths
        """
        print("🔍 Scanning for DICOM files...")
        
        all_files = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith('.dcm') or not '.' in file:
                    all_files.append(os.path.join(root, file))
        
        self.stats['total_files'] = len(all_files)
        print(f"Found {len(all_files)} potential DICOM files")
        
        # Filter for multi-frame files
        print("📊 Checking for multi-frame files...")
        multiframe_files = []
        
        for file_path in tqdm(all_files, desc="Checking files"):
            try:
                ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                num_frames = getattr(ds, 'NumberOfFrames', 1)
                if num_frames > 1:
                    multiframe_files.append(file_path)
            except:
                continue
        
        self.stats['multiframe_files'] = len(multiframe_files)
        print(f"Found {len(multiframe_files)} multi-frame files")
        
        return multiframe_files
    
    def extract_cardiac_phases_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Extract cardiac phases from a single file.
        
        Args:
            file_path: Path to DICOM file
            
        Returns:
            Dictionary with cardiac phase information or None if failed
        """
        try:
            # Use CardiacPhaseDetector directly to get full results including frame_summary
            detector = CardiacPhaseDetector(end_systole_percent=0.35, end_diastole_percent=0.95)
            
            ds = pydicom.dcmread(file_path)
            num_frames = getattr(ds, 'NumberOfFrames', 1)
            
            if num_frames <= 1:
                self.stats['failed_extractions'] += 1
                return None
            
            # Check for required timing information
            required_tags = [(0x0018, 0x6060), (0x0018, 0x1063)]  # R Wave Times, Frame Time
            missing_tags = [tag for tag in required_tags if tag not in ds]
            
            if missing_tags:
                self.stats['failed_extractions'] += 1
                return None
            
            # Get full cardiac phase analysis
            cardiac_phases = detector.process_dicom_dataset(ds)
            
            if cardiac_phases and cardiac_phases.get('labeled_frames'):
                # Extract the multiple access formats
                labeled_frames = cardiac_phases['labeled_frames']
                frame_summary = cardiac_phases['frame_summary']
                
                result = {
                    'file_path': file_path,
                    'relative_path': os.path.relpath(file_path, self.input_dir),
                    
                    # Multiple Access Formats (as requested)
                    'simple_dictionary': labeled_frames,  # {'ED1': 21, 'ES1': 9, 'ED2': 43, 'ES2': 32, ...}
                    'by_cycle': frame_summary['by_cycle'],  # {'Cycle_1': {'R': 0, 'ED': 21, 'ES': 9}, 'Cycle_2': {...}}
                    'by_phase': frame_summary['by_phase'],  # {'end_diastoles': {'ED1': 21, 'ED2': 43}, 'end_systoles': {'ES1': 9, 'ES2': 32}}
                    
                    # Additional formats
                    'sequential_order': frame_summary['sequential_order'],  # [(frame, label), ...]
                    'formatted_string': self._format_frames_string(labeled_frames),  # "ED1: 21, ES1: 9, ..."
                    'summary': {
                        'total_cycles': frame_summary['total_cycles'],
                        'total_frames': cardiac_phases['timing_info']['num_frames'],
                        'frame_time_ms': cardiac_phases['timing_info']['frame_time']
                    },
                    
                    # Arrays for easy access
                    'end_systolic_frames': cardiac_phases['end_systolic_frames'],
                    'end_diastolic_frames': cardiac_phases['end_diastolic_frames'],
                }
                
                self.stats['successful_extractions'] += 1
                self.stats['total_cycles_detected'] += frame_summary['total_cycles']
                
                return result
            else:
                self.stats['failed_extractions'] += 1
                return None
                
        except Exception as e:
            self.stats['failed_extractions'] += 1
            print(f"Error processing {os.path.basename(file_path)}: {e}")
            return None
    
    def _format_frames_string(self, labeled_frames: Dict) -> str:
        """
        Format labeled frames as a string following cardiac cycle convention:
        ES0: 5, ED1: 21, ES1: 9, ED2: 43, ES2: 32
        
        Args:
            labeled_frames: Dictionary of labeled frames
            
        Returns:
            Formatted string in conventional cardiac cycle order
        """
        formatted_pairs = []
        
        # First add ES0 if it exists (pre-cycle end-systole)
        if 'ES0' in labeled_frames:
            formatted_pairs.append(f"ES0: {labeled_frames['ES0']}")
        
        # Sort cycles by number and add in conventional order: EDn, ESn
        ed_frames = []
        es_frames = []
        
        for label, frame in labeled_frames.items():
            if label.startswith('ED') and label != 'ES0':
                cycle_num = int(label[2:])
                ed_frames.append((cycle_num, label, frame))
            elif label.startswith('ES') and label != 'ES0':
                cycle_num = int(label[2:])
                es_frames.append((cycle_num, label, frame))
        
        # Sort by cycle number
        ed_frames.sort(key=lambda x: x[0])
        es_frames.sort(key=lambda x: x[0])
        
        # Create cycle dictionary for easy lookup
        ed_dict = {cycle_num: (label, frame) for cycle_num, label, frame in ed_frames}
        es_dict = {cycle_num: (label, frame) for cycle_num, label, frame in es_frames}
        
        # Get all cycle numbers
        all_cycles = sorted(set(list(ed_dict.keys()) + list(es_dict.keys())))
        
        # Add frames in conventional order: ED starts cycle, ES ends cycle
        for cycle_num in all_cycles:
            # Add ED first (cycle start)
            if cycle_num in ed_dict:
                label, frame = ed_dict[cycle_num]
                formatted_pairs.append(f"{label}: {frame}")
            
            # Add ES second (cycle end)
            if cycle_num in es_dict:
                label, frame = es_dict[cycle_num]
                formatted_pairs.append(f"{label}: {frame}")
        
        return ", ".join(formatted_pairs)
    
    def process_all_files(self) -> None:
        """
        Process all multi-frame DICOM files and extract cardiac phases.
        """
        multiframe_files = self.find_multiframe_dicoms()
        
        if not multiframe_files:
            print("⚠️  No multi-frame files found!")
            return
        
        print(f"🫀 Extracting cardiac phases from {len(multiframe_files)} files...")
        
        for file_path in tqdm(multiframe_files, desc="Processing"):
            result = self.extract_cardiac_phases_from_file(file_path)
            if result:
                self.results[file_path] = result
    
    def save_results(self) -> None:
        """
        Save cardiac phase extraction results to multiple formats.
        """
        if not self.results:
            print("⚠️  No results to save!")
            return
        
        print(f"💾 Saving results to {self.output_dir}")
        
        # 1. Save detailed JSON results with multiple access formats
        json_file = self.output_dir / 'cardiac_phases_detailed.json'
        with open(json_file, 'w') as f:
            # Make results JSON serializable
            json_results = {}
            for file_path, result in self.results.items():
                json_results[result['relative_path']] = {
                    # Multiple Access Formats
                    'simple_dictionary': result['simple_dictionary'],
                    'by_cycle': result['by_cycle'],
                    'by_phase': result['by_phase'],
                    
                    # Additional formats
                    'sequential_order': result['sequential_order'],
                    'formatted_string': result['formatted_string'],
                    'summary': result['summary'],
                    'end_systolic_frames': result['end_systolic_frames'],
                    'end_diastolic_frames': result['end_diastolic_frames']
                }
            json.dump(json_results, f, indent=2)
        
        # 2. Save simple CSV format
        csv_file = self.output_dir / 'cardiac_phases.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File Path', 'Cardiac Cycles', 'Cardiac Phase Frames'])
            
            for file_path, result in self.results.items():
                writer.writerow([
                    result['relative_path'],
                    result['summary']['total_cycles'],
                    result['formatted_string']
                ])
        
        # 3. Save simple text format (easy to read)
        txt_file = self.output_dir / 'cardiac_phases.txt'
        with open(txt_file, 'w') as f:
            f.write("CARDIAC PHASE FRAMES EXTRACTION RESULTS\n")
            f.write("=" * 50 + "\n\n")
            
            for file_path, result in self.results.items():
                f.write(f"File: {result['relative_path']}\n")
                f.write(f"Cycles: {result['summary']['total_cycles']}\n")
                f.write(f"Frames: {result['formatted_string']}\n")
                f.write("-" * 30 + "\n")
        
        # 4. Save frame mapping only (for easy parsing)
        mapping_file = self.output_dir / 'frame_mapping.txt'
        with open(mapping_file, 'w') as f:
            for file_path, result in self.results.items():
                f.write(f"{result['relative_path']}: {result['formatted_string']}\n")
        
        # 5. Save multiple access formats (as you requested)
        formats_file = self.output_dir / 'multiple_access_formats.txt'
        with open(formats_file, 'w') as f:
            f.write("MULTIPLE ACCESS FORMATS FOR CARDIAC PHASE FRAMES\n")
            f.write("=" * 60 + "\n\n")
            
            for file_path, result in self.results.items():
                f.write(f"File: {result['relative_path']}\n")
                f.write("-" * 40 + "\n")
                
                # Simple Dictionary Format
                f.write(f"Simple Dictionary: {result['simple_dictionary']}\n")
                
                # By Cycle Format
                f.write(f"By Cycle: {result['by_cycle']}\n")
                
                # By Phase Format
                f.write(f"By Phase: {result['by_phase']}\n")
                
                # Sequential Order
                sequential_str = ", ".join([f"{label}:{frame}" for frame, label in result['sequential_order']])
                f.write(f"Sequential Order: {sequential_str}\n")
                
                f.write("\n")
        
        # 6. Save statistics
        stats_file = self.output_dir / 'extraction_stats.json'
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        print(f"✅ Results saved:")
        print(f"  📄 Detailed results: {json_file}")
        print(f"  📊 CSV summary: {csv_file}")
        print(f"  📝 Text summary: {txt_file}")
        print(f"  🗂️  Frame mapping: {mapping_file}")
        print(f"  🔄 Multiple access formats: {formats_file}")
        print(f"  📈 Statistics: {stats_file}")
    
    def print_summary(self) -> None:
        """
        Print summary of extraction results.
        """
        print(f"\n📈 Cardiac Phase Extraction Summary:")
        print(f"{'='*50}")
        print(f"Total DICOM files scanned: {self.stats['total_files']}")
        print(f"Multi-frame files found: {self.stats['multiframe_files']}")
        print(f"Successful extractions: {self.stats['successful_extractions']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        print(f"Total cardiac cycles detected: {self.stats['total_cycles_detected']}")
        
        if self.stats['successful_extractions'] > 0:
            avg_cycles = self.stats['total_cycles_detected'] / self.stats['successful_extractions']
            print(f"Average cycles per file: {avg_cycles:.1f}")
            
            success_rate = (self.stats['successful_extractions'] / self.stats['multiframe_files']) * 100
            print(f"Success rate: {success_rate:.1f}%")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract cardiac phase frames from multi-frame DICOM files')
    parser.add_argument('input_dir', help='Input directory containing DICOM files')
    parser.add_argument('--output-dir', help='Output directory for results (default: input_dir/cardiac_phases)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = CardiacPhaseExtractor(args.input_dir, args.output_dir)
    
    try:
        # Process all files
        extractor.process_all_files()
        
        # Save results
        extractor.save_results()
        
        # Print summary
        extractor.print_summary()
        
        # Show sample results
        if extractor.results:
            print(f"\n📋 Sample Results:")
            for i, (file_path, result) in enumerate(extractor.results.items()):
                if i >= 3:  # Show first 3 results
                    break
                print(f"  {result['relative_path']}: {result['formatted_string']}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()