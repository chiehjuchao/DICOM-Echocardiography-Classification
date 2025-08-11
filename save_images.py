#!/usr/bin/env python3
"""
DICOM Image Saver

Saves classified DICOM images as PNG files for viewing.
Works on headless servers without GUI display.
"""

import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
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

def save_dicom_image(file_path, output_path, title=""):
    """
    Save a DICOM image as PNG file
    
    Args:
        file_path: Path to DICOM file
        output_path: Path where to save PNG image
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
            
            # Create figure
            plt.figure(figsize=(12, 10))
            
            # Handle color images
            if len(pixel_array.shape) == 3:  # Color image
                plt.imshow(pixel_array)
            else:  # Grayscale image
                plt.imshow(pixel_array, cmap='gray')
            
            plt.title(f"{title}\nFile: {os.path.basename(file_path)}", fontsize=14, pad=20)
            plt.axis('off')
            plt.tight_layout()
            
            # Save the image
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()  # Close to free memory
            
            return True
            
        else:
            print(f"No pixel data found in {file_path}")
            return False
            
    except Exception as e:
        print(f"Error saving image {file_path}: {e}")
        return False

def save_sample_images(max_per_category=3):
    """
    Save sample images from each classification category as PNG files
    """
    
    # Set up paths
    root_dir = "/research/projects/Chao/Echo-preprocessing/2023Examples"
    output_dir = "/research/projects/Chao/Echo-preprocessing/DICOM_classification/saved_images"
    
    print("DICOM Echocardiography Image Saver")
    print(f"Root directory: {root_dir}")
    print(f"Output directory: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if root directory exists
    if not os.path.exists(root_dir):
        print(f"Error: Root directory {root_dir} does not exist")
        return False
    
    try:
        # Initialize classifier
        classifier = EchoCardiographyClassifier(root_dir)
        
        # Find sample DICOM files
        sample_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith('.dcm'):
                    sample_files.append(os.path.join(root, file))
                    if len(sample_files) >= 30:  # Get enough samples for good coverage
                        break
            if len(sample_files) >= 30:
                break
        
        if not sample_files:
            print("No DICOM files found")
            return False
        
        print(f"Found {len(sample_files)} sample DICOM files")
        
        # Classify all sample files
        classifications_by_category = {category: [] for category in classifier.CATEGORIES.keys()}
        
        print("Classifying sample files...")
        for i, file_path in enumerate(sample_files):
            print(f"  Processing {i+1}/{len(sample_files)}: {os.path.basename(file_path)}")
            
            classification = classifier.classify_dicom(file_path)
            if classification:
                classifications_by_category[classification.category].append(classification)
        
        # Save images from each category
        print("\n" + "="*60)
        print("SAVING SAMPLE IMAGES FROM EACH CATEGORY")
        print("="*60)
        
        total_saved = 0
        summary_info = []
        
        for category, classifications in classifications_by_category.items():
            if not classifications:
                continue
                
            category_name = classifier.CATEGORIES[category]
            print(f"\n{category_name.upper()} ({len(classifications)} files found)")
            print("-" * len(category_name))
            
            # Create category subdirectory
            category_dir = os.path.join(output_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Save up to max_per_category images
            sample_size = min(len(classifications), max_per_category)
            samples = classifications[:sample_size]
            
            for i, classification in enumerate(samples):
                print(f"  Saving image {i+1}/{sample_size}...")
                print(f"    File: {os.path.basename(classification.file_path)}")
                print(f"    Confidence: {classification.confidence:.2f}")
                print(f"    Reasoning: {classification.reasoning}")
                
                # Create output filename
                base_name = os.path.basename(classification.file_path)
                output_filename = f"{category}_{i+1:02d}_{base_name}.png"
                output_path = os.path.join(category_dir, output_filename)
                
                # Create title with classification info
                title = f"{category_name}\nConfidence: {classification.confidence:.2f}\nReasoning: {classification.reasoning}"
                
                # Save the image
                if save_dicom_image(classification.file_path, output_path, title):
                    print(f"    ✅ Saved: {output_path}")
                    total_saved += 1
                    
                    # Add to summary
                    summary_info.append({
                        'category': category_name,
                        'file': base_name,
                        'confidence': classification.confidence,
                        'saved_as': output_filename
                    })
                else:
                    print(f"    ❌ Failed to save")
        
        # Create summary file
        summary_path = os.path.join(output_dir, "image_summary.txt")
        with open(summary_path, 'w') as f:
            f.write("DICOM Echocardiography Images Summary\n")
            f.write("="*50 + "\n\n")
            
            current_category = ""
            for info in summary_info:
                if info['category'] != current_category:
                    current_category = info['category']
                    f.write(f"\n{current_category}:\n")
                    f.write("-" * len(current_category) + "\n")
                
                f.write(f"  {info['saved_as']}\n")
                f.write(f"    Original: {info['file']}\n")
                f.write(f"    Confidence: {info['confidence']:.2f}\n\n")
        
        print(f"\n✅ Successfully saved {total_saved} DICOM images as PNG files")
        print(f"✅ Images saved to: {output_dir}")
        print(f"✅ Summary saved to: {summary_path}")
        
        # List the saved files
        print(f"\nSaved image files:")
        for category in os.listdir(output_dir):
            category_path = os.path.join(output_dir, category)
            if os.path.isdir(category_path):
                print(f"\n  {category}/")
                for filename in sorted(os.listdir(category_path)):
                    if filename.endswith('.png'):
                        print(f"    {filename}")
        
        return True
        
    except Exception as e:
        print(f"Error during image saving: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Save DICOM echocardiography images as PNG files')
    parser.add_argument('--max-per-category', type=int, default=3,
                       help='Maximum images to save per category (default: 3)')
    
    args = parser.parse_args()
    
    success = save_sample_images(args.max_per_category)
    
    if success:
        print("\n🎉 All images saved successfully!")
        print("You can now view the PNG files in the saved_images directory")
    else:
        print("\n❌ Failed to save images")
        sys.exit(1)