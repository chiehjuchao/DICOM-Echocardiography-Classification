#!/usr/bin/env python3
"""
Test script for the DICOM Echocardiography Classifier with visualization

This script tests the classifier on a small subset of DICOM files
and provides visualization of the classified images.
"""

import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Add the current directory to path to import the classifier
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dicom_echo_classifier import EchoCardiographyClassifier

try:
    import pydicom
    from pydicom import dcmread
except ImportError:
    print("Error: pydicom library not found. Please install with: pip install pydicom")
    sys.exit(1)

def display_dicom_image(file_path, title=""):
    """
    Display a DICOM image using matplotlib
    
    Args:
        file_path: Path to DICOM file
        title: Title for the plot
    """
    try:
        ds = dcmread(file_path)
        
        # Get pixel data
        if hasattr(ds, 'pixel_array'):
            pixel_array = ds.pixel_array
            
            # Handle multi-frame images - show first frame
            if len(pixel_array.shape) > 2:
                pixel_array = pixel_array[0] if pixel_array.shape[0] > 0 else pixel_array
            
            # Handle color images
            plt.figure(figsize=(8, 6))
            if len(pixel_array.shape) == 3:  # Color image
                plt.imshow(pixel_array)
            else:  # Grayscale image
                plt.imshow(pixel_array, cmap='gray')
            
            plt.title(f"{title}\nFile: {os.path.basename(file_path)}")
            plt.axis('off')
            plt.tight_layout()
            plt.show()
            
        else:
            print(f"No pixel data found in {file_path}")
            
    except Exception as e:
        print(f"Error displaying image {file_path}: {e}")

def visualize_categories(classifier, classifications_by_category, max_per_category=2):
    """
    Visualize sample images from each category
    
    Args:
        classifier: EchoCardiographyClassifier instance
        classifications_by_category: Dict of category -> list of classifications
        max_per_category: Maximum number of images to show per category
    """
    print("\n" + "="*60)
    print("VISUALIZING SAMPLE IMAGES FROM EACH CATEGORY")
    print("="*60)
    
    for category, classifications in classifications_by_category.items():
        if not classifications:
            continue
            
        category_name = classifier.CATEGORIES[category]
        print(f"\n{category_name.upper()}")
        print("-" * len(category_name))
        
        # Show up to max_per_category images
        sample_size = min(len(classifications), max_per_category)
        samples = classifications[:sample_size]
        
        for i, classification in enumerate(samples):
            print(f"\nSample {i+1}/{sample_size}:")
            print(f"  File: {os.path.basename(classification.file_path)}")
            print(f"  Confidence: {classification.confidence:.2f}")
            print(f"  Reasoning: {classification.reasoning}")
            print(f"  Modality: {classification.metadata.get('modality', 'N/A')}")
            print(f"  Series Description: {classification.metadata.get('series_description', 'N/A')}")
            print(f"  Image Size: {classification.metadata.get('rows', 'N/A')}x{classification.metadata.get('columns', 'N/A')}")
            print(f"  Frames: {classification.metadata.get('number_of_frames', 'N/A')}")
            
            # Ask user if they want to see the image
            show_image = input(f"  Show image? (y/n/q to quit visualization): ").lower()
            if show_image == 'q':
                return
            elif show_image in ['y', 'yes']:
                display_dicom_image(classification.file_path, 
                                  f"{category_name} - Confidence: {classification.confidence:.2f}")

def test_classifier_with_visualization():
    """Test the classifier and visualize results by category"""
    
    # Set up paths
    root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    output_dir = "/research/projects/Chao/Echo-preprocessing/DICOM_classification/test_results"
    
    print("Testing DICOM Echocardiography Classifier with Visualization")
    print(f"Root directory: {root_dir}")
    print(f"Output directory: {output_dir}")
    
    # Check if root directory exists
    if not os.path.exists(root_dir):
        print(f"Error: Root directory {root_dir} does not exist")
        return False
    
    try:
        # Initialize classifier
        classifier = EchoCardiographyClassifier(root_dir, output_dir)
        
        # Find sample DICOM files for testing (more samples for better visualization)
        sample_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith('.dcm'):
                    sample_files.append(os.path.join(root, file))
                    if len(sample_files) >= 20:  # Test with more files for better category coverage
                        break
            if len(sample_files) >= 20:
                break
        
        if not sample_files:
            print("No DICOM files found for testing")
            return False
        
        print(f"Found {len(sample_files)} sample DICOM files for testing")
        
        # Classify all sample files
        classifications_by_category = {category: [] for category in classifier.CATEGORIES.keys()}
        
        print("\nClassifying sample files...")
        for i, file_path in enumerate(sample_files):
            print(f"Processing file {i+1}/{len(sample_files)}: {os.path.basename(file_path)}")
            
            classification = classifier.classify_dicom(file_path)
            if classification:
                classifications_by_category[classification.category].append(classification)
        
        # Print summary
        print("\n" + "="*60)
        print("CLASSIFICATION SUMMARY")
        print("="*60)
        total_classified = sum(len(classifications) for classifications in classifications_by_category.values())
        
        for category, classifications in classifications_by_category.items():
            count = len(classifications)
            percentage = (count / total_classified * 100) if total_classified > 0 else 0
            print(f"{classifier.CATEGORIES[category]}: {count} files ({percentage:.1f}%)")
        
        # Visualize categories
        visualize_categories(classifier, classifications_by_category)
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_full_classification_with_visualization():
    """Run the full classification and create visualization summary"""
    
    root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    output_dir = "/research/projects/Chao/Echo-preprocessing/DICOM_classification/results"
    
    print("Running full DICOM classification with visualization...")
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
        
        # Create visualization summary
        create_visualization_summary(classifier, output_dir)
        
        # Print summary
        print("\nClassification Complete!")
        print("Summary:")
        total_files = len(classifier.classifications)
        for category, count in classifier.stats.items():
            percentage = (count / total_files * 100) if total_files > 0 else 0
            print(f"  {classifier.CATEGORIES[category]}: {count} ({percentage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"Error during full classification: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_visualization_summary(classifier, output_dir):
    """Create visualization summary plots"""
    
    # Create bar chart of categories
    categories = list(classifier.CATEGORIES.values())
    counts = [classifier.stats.get(cat, 0) for cat in classifier.CATEGORIES.keys()]
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(range(len(categories)), counts)
    plt.xlabel('Category')
    plt.ylabel('Number of Files')
    plt.title('DICOM Echocardiography Classification Results')
    plt.xticks(range(len(categories)), [cat.replace(' ', '\n') for cat in categories], rotation=45, ha='right')
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                str(count), ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'classification_summary.png'), dpi=300, bbox_inches='tight')
    plt.show()
    
    # Create pie chart
    plt.figure(figsize=(10, 8))
    non_zero_categories = [(cat, count) for cat, count in zip(categories, counts) if count > 0]
    if non_zero_categories:
        labels, values = zip(*non_zero_categories)
        plt.pie(values, labels=[label.replace(' ', '\n') for label in labels], autopct='%1.1f%%', startangle=90)
        plt.title('DICOM Echocardiography Classification Distribution')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'classification_distribution.png'), dpi=300, bbox_inches='tight')
        plt.show()
    
    print(f"Visualization plots saved to {output_dir}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test or run DICOM classification with visualization')
    parser.add_argument('--full', action='store_true', 
                       help='Run full classification instead of test')
    
    args = parser.parse_args()
    
    if args.full:
        success = run_full_classification_with_visualization()
    else:
        success = test_classifier_with_visualization()
    
    sys.exit(0 if success else 1)