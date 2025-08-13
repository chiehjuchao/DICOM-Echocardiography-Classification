#!/usr/bin/env python3
"""
Cardiac Phase Detector for DICOM Echocardiography Images

This module provides functionality to identify end-systolic and end-diastolic frames
in multi-frame DICOM echocardiography images using timing information from DICOM headers.

Integration with DICOM Classification System v2.4
"""

import numpy as np
import matplotlib.pyplot as plt
import pydicom
import sys
import os
from typing import Dict, List, Tuple, Optional

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

class CardiacPhaseDetector:
    """
    Generic cardiac phase detector that extracts timing information from DICOM headers
    and identifies end-systolic and end-diastolic frames.
    """
    
    def __init__(self, end_systole_percent: float = 0.35, end_diastole_percent: float = 0.95):
        """
        Initialize the detector with cardiac timing parameters.
        
        Args:
            end_systole_percent: Percentage of RR interval for end-systole (default: 0.35, ~35% of cycle)
            end_diastole_percent: Percentage of RR interval for end-diastole (default: 0.95, ~95% of cycle)
        """
        self.end_systole_percent = end_systole_percent
        self.end_diastole_percent = end_diastole_percent
    
    def _create_frame_summary(self, cardiac_phases: Dict) -> Dict:
        """
        Create an organized summary of frame numbers by cycle and phase.
        Following conventional cardiac cycle: ES0 → Cycle1(ED1→ES1) → Cycle2(ED2→ES2)
        
        Args:
            cardiac_phases: Cardiac phase data
            
        Returns:
            Organized frame summary dictionary
        """
        summary = {
            'by_cycle': {},
            'by_phase': {
                'r_waves': {},
                'end_diastoles': {},
                'end_systoles': {}
            },
            'sequential_order': [],
            'total_cycles': len(cardiac_phases['cycle_info'])
        }
        
        # Add ES0 if it exists (pre-cycle end-systole)
        if 'ES0' in cardiac_phases['labeled_frames']:
            summary['by_cycle']['Cycle_0'] = {
                'ES': cardiac_phases['labeled_frames']['ES0']
            }
            summary['by_phase']['end_systoles']['ES0'] = cardiac_phases['labeled_frames']['ES0']
        
        # Organize complete cardiac cycles (starting from cycle 1)
        for cycle in cardiac_phases['cycle_info']:
            cycle_num = cycle['cycle_number']
            summary['by_cycle'][f"Cycle_{cycle_num}"] = {
                'R': cycle['r_wave_frame'],
                'ED': cycle['end_diastole_frame'],  # ED starts the cycle
                'ES': cycle['end_systole_frame']    # ES ends the cycle
            }
            
            # Organize by phase type
            summary['by_phase']['r_waves'][f"R{cycle_num}"] = cycle['r_wave_frame']
            summary['by_phase']['end_diastoles'][f"ED{cycle_num}"] = cycle['end_diastole_frame']
            summary['by_phase']['end_systoles'][f"ES{cycle_num}"] = cycle['end_systole_frame']
        
        # Create sequential order of all events (chronological by frame number)
        all_events = []
        
        # Add ES0 if exists
        if 'ES0' in cardiac_phases['labeled_frames']:
            all_events.append((cardiac_phases['labeled_frames']['ES0'], 'ES0'))
        
        # Add all cycle events
        for cycle in cardiac_phases['cycle_info']:
            cycle_num = cycle['cycle_number']
            all_events.extend([
                (cycle['r_wave_frame'], f"R{cycle_num}"),
                (cycle['end_systole_frame'], f"ES{cycle_num}"),
                (cycle['end_diastole_frame'], f"ED{cycle_num}")
            ])
        
        # Sort by frame number for chronological order
        all_events.sort(key=lambda x: x[0])
        summary['sequential_order'] = all_events
        
        return summary
    
    def extract_dicom_timing_info(self, dicom_path: str) -> Dict:
        """
        Extract relevant timing information from DICOM file.
        
        Args:
            dicom_path: Path to DICOM file
            
        Returns:
            Dictionary containing extracted DICOM timing information
        """
        ds = pydicom.dcmread(dicom_path)
        return self.extract_dicom_timing_from_dataset(ds)
    
    def extract_dicom_timing_from_dataset(self, ds) -> Dict:
        """
        Extract timing information from an already loaded pydicom dataset.
        
        Args:
            ds: pydicom Dataset object
            
        Returns:
            Dictionary containing extracted DICOM timing information
        """
        timing_info = {}
        
        # Required fields
        required_tags = {
            'r_wave_times': (0x0018, 0x6060),  # R Wave Time Vector
            'frame_time': (0x0018, 0x1063),    # Frame Time
            'num_frames': (0x0028, 0x0008),    # Number of Frames
        }
        
        # Optional fields
        optional_tags = {
            'heart_rate': (0x0018, 0x1088),           # Heart Rate
            'cine_rate': (0x0018, 0x0040),            # Cine Rate
            'effective_duration': (0x0018, 0x0072),   # Effective Duration
            'frame_delay': (0x0018, 0x1066),          # Frame Delay
            'actual_frame_duration': (0x0018, 0x1242), # Actual Frame Duration
        }
        
        # Extract required information
        for key, tag in required_tags.items():
            if tag in ds:
                value = ds[tag].value
                if key == 'r_wave_times' and isinstance(value, (list, tuple)):
                    timing_info[key] = list(value)
                else:
                    timing_info[key] = float(value) if isinstance(value, (int, float, str)) else value
            else:
                raise ValueError(f"Required DICOM tag {tag} ({key}) not found in dataset")
        
        # Extract optional information
        for key, tag in optional_tags.items():
            if tag in ds:
                value = ds[tag].value
                timing_info[key] = float(value) if isinstance(value, (int, float, str)) else value
            else:
                timing_info[key] = None
        
        return timing_info
    
    def calculate_cardiac_phases(self, timing_info: Dict) -> Dict:
        """
        Calculate cardiac phase frame indices from timing information.
        
        Args:
            timing_info: Dictionary containing DICOM timing information
            
        Returns:
            Dictionary containing cardiac phase information
        """
        r_wave_times = timing_info['r_wave_times']
        frame_time_ms = timing_info['frame_time']
        total_frames = int(timing_info['num_frames'])
        
        # Convert R wave times to frame indices
        r_wave_frames = [int(time / frame_time_ms) for time in r_wave_times]
        
        # Calculate cardiac cycle statistics
        rr_intervals = np.diff(r_wave_times) if len(r_wave_times) > 1 else []
        avg_rr_interval = np.mean(rr_intervals) if len(rr_intervals) > 0 else None
        
        cardiac_phases = {
            'timing_info': timing_info,
            'r_wave_frames': r_wave_frames,
            'r_wave_times': r_wave_times,
            'end_systolic_frames': [],
            'end_diastolic_frames': [],
            'end_systolic_times': [],
            'end_diastolic_times': [],
            'cycle_info': [],
            'rr_intervals': rr_intervals,
            'avg_rr_interval': avg_rr_interval,
            'labeled_frames': {},  # New: cycle-specific frame labels
            'frame_summary': {}    # New: organized summary
        }
        
        # Calculate phases following cardiac cycle convention: ED starts cycle, ES ends cycle
        # ES0 (before first complete cycle) + ED1-ES1, ED2-ES2, etc.
        
        # First ES0 (end-systole before first complete cycle)
        if len(r_wave_times) > 0:
            first_r_wave = r_wave_times[0]
            # ES0 occurs just before the first R-wave (estimate from previous incomplete cycle)
            if first_r_wave > 0:
                # Assume ES0 is at 35% before the first R-wave (rough estimate)
                es0_time = max(0, first_r_wave - (first_r_wave * 0.35))
                es0_frame = int(es0_time / frame_time_ms)
                es0_frame = max(0, min(es0_frame, total_frames - 1))
                
                cardiac_phases['end_systolic_frames'].append(es0_frame)
                cardiac_phases['end_systolic_times'].append(es0_time)
                cardiac_phases['labeled_frames']['ES0'] = es0_frame
        
        # Calculate complete cardiac cycles (ED1-ES1, ED2-ES2, etc.)
        for i in range(len(r_wave_times) - 1):
            r_wave_time = r_wave_times[i]
            next_r_wave_time = r_wave_times[i + 1]
            cycle_duration = next_r_wave_time - r_wave_time
            
            cycle_num = i + 1  # Start from cycle 1
            
            # Calculate end-diastolic timing (occurs at 95% of RR interval after R-wave)
            end_diastole_time = r_wave_time + (cycle_duration * self.end_diastole_percent)
            end_diastole_frame = int(end_diastole_time / frame_time_ms)
            
            # Calculate end-systolic timing (occurs at 35% of RR interval after R-wave)
            end_systole_time = r_wave_time + (cycle_duration * self.end_systole_percent)
            end_systole_frame = int(end_systole_time / frame_time_ms)
            
            # Ensure frames are within bounds
            end_systole_frame = max(0, min(end_systole_frame, total_frames - 1))
            end_diastole_frame = max(0, min(end_diastole_frame, total_frames - 1))
            
            # Only add if within valid time range
            if end_diastole_time < next_r_wave_time and end_systole_time < next_r_wave_time:
                cardiac_phases['end_systolic_frames'].append(end_systole_frame)
                cardiac_phases['end_systolic_times'].append(end_systole_time)
                cardiac_phases['end_diastolic_frames'].append(end_diastole_frame)
                cardiac_phases['end_diastolic_times'].append(end_diastole_time)
                
                # Create cycle-specific labels (conventional: cycle starts with ED)
                ed_label = f"ED{cycle_num}"
                es_label = f"ES{cycle_num}" 
                r_label = f"R{cycle_num}"
                
                cardiac_phases['labeled_frames'][ed_label] = end_diastole_frame
                cardiac_phases['labeled_frames'][es_label] = end_systole_frame
                cardiac_phases['labeled_frames'][r_label] = int(r_wave_time / frame_time_ms)
                
                cycle_info = {
                    'cycle_number': cycle_num,
                    'r_wave_time': r_wave_time,
                    'r_wave_frame': int(r_wave_time / frame_time_ms),
                    'end_diastole_time': end_diastole_time,
                    'end_diastole_frame': end_diastole_frame,
                    'end_systole_time': end_systole_time,
                    'end_systole_frame': end_systole_frame,
                    'cycle_duration_ms': cycle_duration,
                    'cycle_frames': int(cycle_duration / frame_time_ms),
                    'labels': {
                        'r_wave': r_label,
                        'end_diastole': ed_label,  # ED starts the cycle
                        'end_systole': es_label    # ES ends the cycle
                    }
                }
                cardiac_phases['cycle_info'].append(cycle_info)
        
        # Create organized frame summary
        cardiac_phases['frame_summary'] = self._create_frame_summary(cardiac_phases)
        
        return cardiac_phases
    
    def process_dicom_file(self, dicom_path: str) -> Dict:
        """
        Complete processing pipeline for a DICOM file.
        
        Args:
            dicom_path: Path to DICOM file
            
        Returns:
            Complete cardiac phase analysis results
        """
        timing_info = self.extract_dicom_timing_info(dicom_path)
        return self.calculate_cardiac_phases(timing_info)
    
    def process_dicom_dataset(self, ds) -> Dict:
        """
        Complete processing pipeline for a pydicom dataset.
        
        Args:
            ds: pydicom Dataset object
            
        Returns:
            Complete cardiac phase analysis results
        """
        timing_info = self.extract_dicom_timing_from_dataset(ds)
        return self.calculate_cardiac_phases(timing_info)
    
    def get_key_frames(self, cardiac_phases: Dict) -> Dict:
        """
        Get key cardiac phase frames in a simple format.
        
        Args:
            cardiac_phases: Results from calculate_cardiac_phases
            
        Returns:
            Dictionary with key frame information for easy access
        """
        key_frames = {
            'end_systolic_frames': cardiac_phases['end_systolic_frames'],
            'end_diastolic_frames': cardiac_phases['end_diastolic_frames'],
            'labeled_frames': cardiac_phases['labeled_frames'],
            'summary': {
                'total_cycles': len(cardiac_phases['cycle_info']),
                'frame_time_ms': cardiac_phases['timing_info']['frame_time'],
                'total_frames': cardiac_phases['timing_info']['num_frames']
            }
        }
        
        # Add first ED and ES frames for quick access
        if cardiac_phases['end_diastolic_frames']:
            key_frames['first_end_diastolic'] = cardiac_phases['end_diastolic_frames'][0]
        if cardiac_phases['end_systolic_frames']:
            key_frames['first_end_systolic'] = cardiac_phases['end_systolic_frames'][0]
            
        return key_frames
    
    def print_summary(self, cardiac_phases: Dict) -> None:
        """
        Print a concise summary of cardiac phase detection results.
        
        Args:
            cardiac_phases: Results from calculate_cardiac_phases
        """
        timing_info = cardiac_phases['timing_info']
        
        print(f"🫀 Cardiac Phase Detection Summary")
        print(f"{'='*50}")
        print(f"Total Frames: {timing_info['num_frames']}")
        print(f"Frame Time: {timing_info['frame_time']:.2f} ms")
        print(f"Cardiac Cycles: {len(cardiac_phases['cycle_info'])}")
        
        if cardiac_phases['avg_rr_interval']:
            calculated_hr = 60000 / cardiac_phases['avg_rr_interval']
            print(f"Heart Rate: {calculated_hr:.1f} BPM")
        
        print(f"\nKey Frames:")
        print(f"  End-Systolic: {cardiac_phases['end_systolic_frames']}")
        print(f"  End-Diastolic: {cardiac_phases['end_diastolic_frames']}")
        
        # Print labeled frames for easy copying
        if cardiac_phases['labeled_frames']:
            items = [f"{label}:{frame}" for label, frame in cardiac_phases['labeled_frames'].items()]
            print(f"\nLabeled Frames: {', '.join(items)}")


def detect_cardiac_phases_for_multiframe(file_path: str, verbose: bool = False) -> Optional[Dict]:
    """
    Detect cardiac phases for multi-frame DICOM files.
    
    This function integrates with the DICOM classification system to provide
    cardiac phase detection for multi-frame echocardiography images.
    
    Args:
        file_path: Path to multi-frame DICOM file
        verbose: Whether to print detailed results
        
    Returns:
        Dictionary containing cardiac phase information, or None if detection fails
    """
    try:
        detector = CardiacPhaseDetector(end_systole_percent=0.35, end_diastole_percent=0.95)
        
        # Load and process DICOM file
        ds = pydicom.dcmread(file_path)
        
        # Check if file is multi-frame
        num_frames = getattr(ds, 'NumberOfFrames', 1)
        if num_frames <= 1:
            if verbose:
                print(f"⚠️  File {os.path.basename(file_path)} is not multi-frame (frames: {num_frames})")
            return None
        
        # Check for required timing information
        required_tags = [(0x0018, 0x6060), (0x0018, 0x1063)]  # R Wave Times, Frame Time
        missing_tags = [tag for tag in required_tags if tag not in ds]
        
        if missing_tags:
            if verbose:
                print(f"⚠️  Missing required timing tags in {os.path.basename(file_path)}: {missing_tags}")
            return None
        
        # Process cardiac phases
        cardiac_phases = detector.process_dicom_dataset(ds)
        
        if verbose:
            detector.print_summary(cardiac_phases)
        else:
            print(f"✅ Detected {len(cardiac_phases['cycle_info'])} cardiac cycles in {os.path.basename(file_path)}")
            if cardiac_phases['end_systolic_frames'] and cardiac_phases['end_diastolic_frames']:
                print(f"   ES frames: {cardiac_phases['end_systolic_frames']}")
                print(f"   ED frames: {cardiac_phases['end_diastolic_frames']}")
        
        # Return key frame information
        return detector.get_key_frames(cardiac_phases)
        
    except Exception as e:
        if verbose:
            print(f"❌ Error processing {os.path.basename(file_path)}: {e}")
        return None


def batch_detect_cardiac_phases(file_paths: List[str], show_progress: bool = True) -> Dict:
    """
    Batch process multiple multi-frame DICOM files for cardiac phase detection.
    
    Args:
        file_paths: List of DICOM file paths
        show_progress: Whether to show progress bar
        
    Returns:
        Dictionary containing results for all processed files
    """
    results = {
        'successful': {},
        'failed': [],
        'summary': {
            'total_files': len(file_paths),
            'successful_count': 0,
            'failed_count': 0,
            'total_cycles_detected': 0
        }
    }
    
    # Filter for multi-frame files first
    print("🔍 Checking for multi-frame files...")
    multiframe_files = []
    
    iterator = tqdm(file_paths, desc="Checking files") if show_progress else file_paths
    
    for file_path in iterator:
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)  # Faster header-only read
            num_frames = getattr(ds, 'NumberOfFrames', 1)
            if num_frames > 1:
                multiframe_files.append(file_path)
        except:
            continue
    
    print(f"📊 Found {len(multiframe_files)} multi-frame files out of {len(file_paths)} total files")
    
    if not multiframe_files:
        print("⚠️  No multi-frame files found!")
        return results
    
    # Process multi-frame files
    print("🫀 Processing cardiac phases...")
    iterator = tqdm(multiframe_files, desc="Detecting phases") if show_progress else multiframe_files
    
    for file_path in iterator:
        cardiac_info = detect_cardiac_phases_for_multiframe(file_path, verbose=False)
        
        if cardiac_info:
            results['successful'][file_path] = cardiac_info
            results['summary']['successful_count'] += 1
            results['summary']['total_cycles_detected'] += cardiac_info['summary']['total_cycles']
        else:
            results['failed'].append(file_path)
            results['summary']['failed_count'] += 1
    
    # Print summary
    print(f"\n📈 Cardiac Phase Detection Summary:")
    print(f"  Successfully processed: {results['summary']['successful_count']}/{len(multiframe_files)} files")
    print(f"  Total cardiac cycles detected: {results['summary']['total_cycles_detected']}")
    print(f"  Failed: {results['summary']['failed_count']} files")
    
    return results


if __name__ == "__main__":
    print("Cardiac Phase Detector for DICOM Echocardiography")
    print("=" * 50)
    print("This module detects end-systolic and end-diastolic frames in multi-frame DICOM files.")
    print("\nUsage:")
    print("1. detect_cardiac_phases_for_multiframe('path/to/file.dcm')")
    print("2. batch_detect_cardiac_phases(['file1.dcm', 'file2.dcm'])")
    print("\nIntegration with DICOM Classification System v2.4")