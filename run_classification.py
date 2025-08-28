#!/usr/bin/env python3
"""
Non-interactive DICOM classification runner

This script runs the classification without interactive visualization
and saves all results to files.
"""

import os
import sys
from pathlib import Path

# Add the current directory to path to import the classifier
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dicom_echo_classifier import EchoCardiographyClassifier

def run_sample_classification(root_dir=None):
    """Run classification on a sample of DICOM files"""
    
    # Set up paths
    if root_dir is None:
        root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    output_dir = "/research/projects/Chao/Echo-preprocessing/DICOM_classification/sample_results"
    
    print("Running Sample DICOM Echocardiography Classification")
    print(f"Root directory: {root_dir}")
    print(f"Output directory: {output_dir}")
    
    # Check if root directory exists
    if not os.path.exists(root_dir):
        print(f"Error: Root directory {root_dir} does not exist")
        return False
    
    try:
        # Initialize classifier
        classifier = EchoCardiographyClassifier(root_dir, output_dir)
        
        # Find sample DICOM files
        sample_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith('.dcm'):
                    sample_files.append(os.path.join(root, file))
                    if len(sample_files) >= 50:  # Test with 50 sample files
                        break
            if len(sample_files) >= 50:
                break
        
        if not sample_files:
            print("No DICOM files found for testing")
            return False
        
        print(f"Found {len(sample_files)} sample DICOM files for classification")
        
        # Classify all sample files
        classifications_by_category = {category: [] for category in classifier.CATEGORIES.keys()}
        
        print("Classifying sample files...")
        successful_classifications = 0
        
        for i, file_path in enumerate(sample_files):
            print(f"Processing file {i+1}/{len(sample_files)}: {os.path.basename(file_path)}")
            
            classification = classifier.classify_dicom(file_path)
            if classification:
                classifications_by_category[classification.category].append(classification)
                classifier.classifications.append(classification)
                classifier.stats[classification.category] += 1
                successful_classifications += 1
        
        # Save results
        classifier.save_results()
        
        # Print detailed summary
        print("\n" + "="*60)
        print("DETAILED CLASSIFICATION SUMMARY")
        print("="*60)
        print(f"Total files processed: {len(sample_files)}")
        print(f"Successfully classified: {successful_classifications}")
        print(f"Failed to classify: {len(sample_files) - successful_classifications}")
        print()
        
        for category, classifications in classifications_by_category.items():
            count = len(classifications)
            percentage = (count / successful_classifications * 100) if successful_classifications > 0 else 0
            print(f"{classifier.CATEGORIES[category]}: {count} files ({percentage:.1f}%)")
            
            # Show details for each category
            if count > 0:
                print("  Sample files:")
                for j, classification in enumerate(classifications[:3]):  # Show first 3
                    print(f"    {j+1}. {os.path.basename(classification.file_path)}")
                    print(f"       Confidence: {classification.confidence:.2f}")
                    print(f"       Reasoning: {classification.reasoning}")
                    if classification.metadata.get('series_description'):
                        print(f"       Series: {classification.metadata['series_description']}")
                    print()
                if count > 3:
                    print(f"    ... and {count - 3} more files")
                print()
        
        print("Results saved to:")
        print(f"  {output_dir}/classification_results.json")
        print(f"  {output_dir}/classification_summary.csv") 
        print(f"  {output_dir}/classification_stats.json")
        
        return True
        
    except Exception as e:
        print(f"Error during classification: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_full_classification(root_dir=None):
    """Run the full classification on all DICOM files"""
    
    if root_dir is None:
        root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    output_dir = "/research/projects/Chao/Echo-preprocessing/DICOM_classification/full_results"
    
    print("Running Full DICOM Classification...")
    print(f"Root directory: {root_dir}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Initialize classifier
        classifier = EchoCardiographyClassifier(root_dir, output_dir)
        
        # Process all files
        def progress_callback(current, total):
            percent = (current / total) * 100
            print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end='', flush=True)
        
        classifier.process_directory(progress_callback)
        print()  # New line after progress
        
        # Save results
        classifier.save_results()
        
        # Print summary
        print("\nFull Classification Complete!")
        print("Summary:")
        total_files = len(classifier.classifications)
        for category, count in classifier.stats.items():
            percentage = (count / total_files * 100) if total_files > 0 else 0
            print(f"  {classifier.CATEGORIES[category]}: {count} ({percentage:.1f}%)")
        
        print(f"\nTotal files processed: {total_files}")
        print("Results saved to:")
        print(f"  {output_dir}/classification_results.json")
        print(f"  {output_dir}/classification_summary.csv")
        print(f"  {output_dir}/classification_stats.json")
        
        return True
        
    except Exception as e:
        print(f"Error during full classification: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DICOM classification')
    parser.add_argument('directory', nargs='?', 
                       default='/research/projects/Chao/Echo-preprocessing/2023Examples',
                       help='Directory containing DICOM files (default: /research/projects/Chao/Echo-preprocessing/2023Examples)')
    parser.add_argument('--full', action='store_true', 
                       help='Run full classification instead of sample')
    
    args = parser.parse_args()
    
    if args.full:
        success = run_full_classification(args.directory)
    else:
        success = run_sample_classification(args.directory)
    
    sys.exit(0 if success else 1)