#!/usr/bin/env python3
"""
Create a corrected flowchart based on actual DICOM header analysis
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Use non-GUI backend for headless systems
import matplotlib
matplotlib.use('Agg')

def create_corrected_classification_flowchart():
    """Create a corrected flowchart showing the DICOM classification decision process"""
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 22))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 22)
    ax.axis('off')
    
    # Define colors for different types of nodes
    colors = {
        'start': '#4CAF50',      # Green
        'decision': '#2196F3',   # Blue
        'process': '#FF9800',    # Orange
        'category': '#9C27B0',   # Purple
        'problem': '#F44336',    # Red
        'solution': '#8BC34A'    # Light Green
    }
    
    # Helper function to create boxes
    def create_box(x, y, width, height, text, color, fontsize=10):
        box = FancyBboxPatch((x-width/2, y-height/2), width, height,
                            boxstyle="round,pad=0.1", 
                            facecolor=color, 
                            edgecolor='black',
                            linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, 
                weight='bold', wrap=True)
    
    # Helper function to create arrows
    def create_arrow(x1, y1, x2, y2, text=''):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'))
        if text:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x + 0.2, mid_y, text, fontsize=8, weight='bold')
    
    # Title
    ax.text(5, 21, 'CORRECTED DICOM Echocardiography Classification Flowchart', 
            ha='center', va='center', fontsize=16, weight='bold')
    
    # Problem identification
    create_box(5, 20, 4.5, 0.8, 'PROBLEMS IDENTIFIED:\n• All files have SamplesPerPixel=3 (RGB)\n• SeriesDescription is empty\n• Multi-frame = cine loops, not side-by-side', colors['problem'], 9)
    create_arrow(5, 19.6, 5, 18.9)
    
    # Start
    create_box(5, 18.5, 2.5, 0.8, 'Start: Load DICOM File', colors['start'])
    create_arrow(5, 18.1, 5, 17.4)
    
    # Read headers
    create_box(5, 17, 3, 0.8, 'Extract DICOM Headers:\n• ImageType (0008,0008)\n• UltrasoundColorDataPresent\n• NumberOfFrames\n• Dimensions', colors['process'], 9)
    create_arrow(5, 16.6, 5, 15.9)
    
    # New approach using ImageType vendor codes
    create_box(5, 15.5, 4.5, 1.2, 'NEW APPROACH: Use ImageType[3] Code\n\nImageType format: [DERIVED, PRIMARY, \'\', CODE]\nWhere CODE appears to be:\n• 0001, 0011: Multi-frame cine\n• 0005, 0009, 0015, 0019: Single frame', colors['solution'], 9)
    create_arrow(5, 14.9, 5, 14.2)
    
    # Check for annotations first
    create_box(5, 13.8, 4, 0.8, 'Priority 1: Check for Annotations\n• GraphicAnnotationSequence?\n• TextObjectSequence?\n• Pixel analysis for burned-in text?', colors['decision'], 9)
    create_arrow(6.5, 13.8, 8, 13.8)
    create_box(8.5, 13.8, 1.8, 0.6, 'Annotations\n(Category 6)\nConfidence: 0.9', colors['category'], 8)
    
    create_arrow(5, 13.4, 5, 12.7, 'No')
    
    # Check ImageType code for cine vs static
    create_box(5, 12.3, 4, 1, 'Priority 2: Analyze ImageType[3] Code\n• Code = 0001 or 0011: Cine loop\n• Code = 0005, 0009, 0015, 0019: Static\n• Use UltrasoundColorDataPresent for Doppler', colors['decision'], 9)
    
    # Cine branch
    create_arrow(3.5, 12.3, 2, 11.5)
    create_box(1.5, 11, 2.5, 0.8, 'Cine Loop Detected\n(Multi-frame)', colors['process'], 9)
    create_arrow(1.5, 10.6, 1.5, 10)
    create_box(1.5, 9.6, 2.2, 0.8, 'Check Color Doppler:\nUltrasoundColorDataPresent=1?', colors['decision'], 8)
    
    create_arrow(0.4, 9.6, 0.2, 8.8)
    create_box(0.5, 8.4, 1.5, 0.6, 'Multi-frame\nColor Doppler\n(Category 2b)', colors['category'], 7)
    
    create_arrow(2.6, 9.6, 2.8, 8.8, 'No')
    create_box(2.5, 8.4, 1.5, 0.6, 'Multi-frame\n2D Gray\n(Category 1b)', colors['category'], 7)
    
    # Static branch  
    create_arrow(6.5, 12.3, 8, 11.5, 'Static')
    create_box(8, 11, 2.5, 0.8, 'Static Image Detected\n(Single frame)', colors['process'], 9)
    create_arrow(8, 10.6, 8, 10)
    create_box(8, 9.6, 2.2, 0.8, 'Check Color Doppler:\nUltrasoundColorDataPresent=1?', colors['decision'], 8)
    
    create_arrow(7, 9.6, 6.8, 8.8)
    create_box(6.5, 8.4, 1.5, 0.6, 'Static\nColor Doppler\n(Category 2a)', colors['category'], 7)
    
    create_arrow(9, 9.6, 9.2, 8.8, 'No')
    create_box(9.5, 8.4, 1.5, 0.6, 'Static\n2D Gray\n(Category 1a)', colors['category'], 7)
    
    # Continue with other checks
    create_arrow(5, 11.8, 5, 7.5)
    
    # M-mode detection (lower priority since not seen in sample)
    create_box(5, 7, 4, 0.8, 'Priority 3: M-mode Detection\n• Look for M-mode specific codes\n• Analyze image aspect ratio\n• Check for time-motion patterns', colors['decision'], 9)
    create_arrow(6.5, 7, 8, 7)
    create_box(8.5, 7, 1.8, 0.6, 'M-mode\n(Categories 3,4)\nNot found in sample', colors['category'], 8)
    
    create_arrow(5, 6.6, 5, 5.9, 'No')
    
    # True side-by-side detection
    create_box(5, 5.5, 4, 0.8, 'Priority 4: True Side-by-side\n• Aspect ratio > 2.0?\n• Visual analysis for split screen\n• Different from cine loops', colors['decision'], 9)
    create_arrow(6.5, 5.5, 8, 5.5)
    create_box(8.5, 5.5, 1.8, 0.6, 'Side-by-side\n(Category 5)\nRare in sample', colors['category'], 8)
    
    # Updated categories box
    categories_text = '''
UPDATED CATEGORIES:
1a. Static 2D without Color Doppler  
1b. Multi-frame 2D without Color Doppler
2a. Static 2D with Color Doppler
2b. Multi-frame 2D with Color Doppler  
3. M-mode Doppler signals
4. M-mode 2D images
5. True side-by-side comparison
6. Images with annotations
'''
    ax.text(2, 3.5, categories_text, fontsize=9, weight='bold', 
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue'))
    
    # Key insights box
    insights_text = '''
KEY INSIGHTS FROM DATA:
• ImageType[3] codes: 
  - 0001, 0011: Cine loops (60% of files)
  - 0005, 0009, 0015, 0019: Static images
• UltrasoundColorDataPresent: 0 or 1
• All files are 758x1016 pixels
• SamplesPerPixel=3 for ALL (misleading!)
• SeriesDescription empty (no text clues)
'''
    ax.text(7, 3.5, insights_text, fontsize=9, weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow'))
    
    plt.tight_layout()
    
    # Save the flowchart
    output_path = '/research/projects/Chao/Echo-preprocessing/DICOM_classification/corrected_classification_flowchart.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Corrected flowchart saved to: {output_path}")
    
    return output_path

if __name__ == '__main__':
    print("Creating corrected DICOM classification flowchart...")
    create_corrected_classification_flowchart()
    print("🎉 Corrected flowchart complete!")