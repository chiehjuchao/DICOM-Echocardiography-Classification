#!/usr/bin/env python3
"""
Test the side-by-side detection on specific DICOM file
"""
import pydicom
from dicom_echo_classifier import EchoCardiographyClassifier

def test_side_by_side_detection():
    """Test side-by-side detection on the specific file"""
    
    # The file you mentioned
    test_file = "/mnt/research/research/projects/Chao/Echo-preprocessing/2023Examples/2023-01-02_r/5162101/34772301/1.2.840.114350.2.451.2.798268.2.2223131894690.1/1.2.840.113619.2.391.3279.1672657186.1.1/1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm"
    
    print(f"Testing file: {test_file.split('/')[-1]}")
    print("=" * 80)
    
    # Initialize classifier
    classifier = EchoCardiographyClassifier("/tmp", "/tmp")
    
    # Load and analyze the file
    try:
        ds = pydicom.dcmread(test_file)
        metadata = classifier.extract_metadata(ds)
        
        print(f"Modality: {ds.get('Modality', 'Unknown')}")
        print(f"ImageType: {metadata.get('image_type', [])}")
        print(f"Number of Frames: {metadata.get('number_of_frames', 1)}")
        print(f"UltrasoundColorDataPresent: {metadata.get('ultrasound_color_data_present', 0)}")
        
        # Check if ultrasound regions exist
        if hasattr(ds, 'SequenceOfUltrasoundRegions'):
            regions = ds.SequenceOfUltrasoundRegions
            print(f"\nFound {len(regions)} ultrasound regions:")
            
            for i, region in enumerate(regions):
                data_type = getattr(region, 'RegionDataType', 0)
                min_x = getattr(region, 'RegionLocationMinX0', 0)
                max_x = getattr(region, 'RegionLocationMaxX1', 0)
                min_y = getattr(region, 'RegionLocationMinY0', 0)
                max_y = getattr(region, 'RegionLocationMaxY1', 0)
                
                if data_type == 1:
                    region_type = "B-mode (grayscale)"
                elif data_type == 2:
                    region_type = "Color Doppler"
                else:
                    region_type = f"Unknown type ({data_type})"
                
                print(f"  Region {i+1}: {region_type}")
                print(f"    Position: ({min_x},{min_y}) to ({max_x},{max_y})")
                print(f"    Size: {max_x-min_x} x {max_y-min_y} pixels")
        else:
            print("\nNo ultrasound regions found")
        
        # Test side-by-side detection
        print(f"\nSide-by-side detection: {classifier.is_side_by_side_doppler(ds, metadata)}")
        
        # Run full classification
        classification = classifier.classify_dicom(test_file)
        if classification:
            print(f"\nClassification result:")
            print(f"  Category: {classification.category}")
            print(f"  Description: {classifier.CATEGORIES[classification.category]}")
            print(f"  Confidence: {classification.confidence:.2f}")
            print(f"  Reasoning: {classification.reasoning}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_side_by_side_detection()