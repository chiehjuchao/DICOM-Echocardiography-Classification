#!/usr/bin/env python3
"""
Test Cardiac Phase Extraction

Quick test script to extract cardiac phases from a specific multi-frame DICOM file.
"""

import os
import sys
from extract_cardiac_phases import CardiacPhaseExtractor
from cardiac_phase_detector import detect_cardiac_phases_for_multiframe

def test_single_file(file_path: str):
    """
    Test cardiac phase extraction on a single file.
    
    Args:
        file_path: Path to DICOM file
    """
    print(f"🫀 Testing cardiac phase extraction on:")
    print(f"   {os.path.basename(file_path)}")
    print("=" * 60)
    
    # Use CardiacPhaseDetector directly to get full results
    from cardiac_phase_detector import CardiacPhaseDetector
    import pydicom
    
    try:
        detector = CardiacPhaseDetector(end_systole_percent=0.35, end_diastole_percent=0.95)
        ds = pydicom.dcmread(file_path)
        
        # Check if multi-frame
        num_frames = getattr(ds, 'NumberOfFrames', 1)
        if num_frames <= 1:
            print(f"❌ File is not multi-frame (frames: {num_frames})")
            return None
        
        # Get full cardiac phase analysis
        cardiac_phases = detector.process_dicom_dataset(ds)
        
        if cardiac_phases and cardiac_phases.get('labeled_frames'):
            print(f"\n✅ Cardiac phases detected successfully!")
            print(f"Total frames: {cardiac_phases['timing_info']['num_frames']}")
            print(f"Cardiac cycles: {len(cardiac_phases['cycle_info'])}")
            
            # Show multiple access formats (as requested)
            print(f"\n🔄 Multiple Access Formats:")
            print("=" * 50)
            
            # Simple Dictionary
            simple_dict = cardiac_phases['labeled_frames']
            print(f"Simple Dictionary: {simple_dict}")
            
            # By Cycle
            by_cycle = cardiac_phases['frame_summary']['by_cycle']
            print(f"By Cycle: {by_cycle}")
            
            # By Phase
            by_phase = cardiac_phases['frame_summary']['by_phase']
            print(f"By Phase: {by_phase}")
            
            # Sequential Order
            sequential = cardiac_phases['frame_summary']['sequential_order']
            sequential_str = ", ".join([f"{label}:{frame}" for frame, label in sequential])
            print(f"Sequential Order: {sequential_str}")
            
            # Formatted string for easy copying (following cardiac cycle convention)
            formatted_pairs = []
            
            # First add ES0 if it exists (pre-cycle end-systole)
            if 'ES0' in simple_dict:
                formatted_pairs.append(f"ES0: {simple_dict['ES0']}")
            
            # Sort cycles by number and add in conventional order: EDn, ESn
            ed_frames = []
            es_frames = []
            
            for label, frame in simple_dict.items():
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
            
            formatted_string = ", ".join(formatted_pairs)
            print(f"\n📋 Formatted output (copy-paste ready):")
            print(f"   {formatted_string}")
            
            return {
                'simple_dictionary': simple_dict,
                'by_cycle': by_cycle,
                'by_phase': by_phase,
                'formatted_string': formatted_string
            }
        else:
            print(f"❌ No cardiac phases detected")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_directory_sample(directory: str, max_files: int = 3):
    """
    Test cardiac phase extraction on a sample of files from a directory.
    
    Args:
        directory: Directory containing DICOM files
        max_files: Maximum number of files to test
    """
    print(f"🔍 Testing cardiac phase extraction on sample files from:")
    print(f"   {directory}")
    print("=" * 60)
    
    extractor = CardiacPhaseExtractor(directory)
    multiframe_files = extractor.find_multiframe_dicoms()
    
    if not multiframe_files:
        print("❌ No multi-frame files found!")
        return
    
    # Test first few files
    test_files = multiframe_files[:max_files]
    print(f"\n🧪 Testing {len(test_files)} files:")
    
    results = []
    for i, file_path in enumerate(test_files, 1):
        print(f"\n--- File {i}: {os.path.basename(file_path)} ---")
        result = test_single_file(file_path)
        if result:
            results.append((os.path.basename(file_path), result))
    
    print(f"\n📈 Summary of {len(results)} successful extractions:")
    print("=" * 60)
    for filename, result in results:
        print(f"{filename}: {result['formatted_string']}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        
        if os.path.isfile(input_path):
            # Test single file
            test_single_file(input_path)
        elif os.path.isdir(input_path):
            # Test directory sample
            test_directory_sample(input_path)
        else:
            print(f"❌ Path not found: {input_path}")
    else:
        print("Usage:")
        print("  python test_cardiac_extraction.py <file_or_directory>")
        print("\nExamples:")
        print("  python test_cardiac_extraction.py /path/to/multiframe.dcm")
        print("  python test_cardiac_extraction.py /path/to/dicom/directory/")