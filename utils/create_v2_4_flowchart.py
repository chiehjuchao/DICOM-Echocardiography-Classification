#!/usr/bin/env python3
"""
Create v2.4 flowchart with side-by-side detection and tissue doppler classification
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Use non-GUI backend for headless systems
import matplotlib
matplotlib.use('Agg')

def create_v2_4_classification_flowchart():
    """Create v2.4 flowchart showing the DICOM classification decision process"""
    
    fig, ax = plt.subplots(1, 1, figsize=(18, 24))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 24)
    ax.axis('off')
    
    # Define colors for different types of nodes
    colors = {
        'start': '#4CAF50',      # Green
        'decision': '#2196F3',   # Blue
        'process': '#FF9800',    # Orange
        'category': '#9C27B0',   # Purple
        'priority': '#E91E63',   # Pink
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
    ax.text(6, 23, 'DICOM Echocardiography Classification v2.4 Flowchart', 
            ha='center', va='center', fontsize=16, weight='bold')
    ax.text(6, 22.3, 'Side-by-side Detection & Tissue Doppler Classification', 
            ha='center', va='center', fontsize=12, style='italic')
    
    # Start
    create_box(6, 21.5, 2.5, 0.8, 'Start: Load DICOM File', colors['start'])
    create_arrow(6, 21.1, 6, 20.4)
    
    # Extract headers
    create_box(6, 20, 3.5, 0.8, 'Extract DICOM Headers:\n• ImageType[10], ImageType[2]\n• ImageType[3] vendor code\n• SequenceOfUltrasoundRegions\n• NumberOfFrames', colors['process'], 9)
    create_arrow(6, 19.6, 6, 18.9)
    
    # Step 1: Exclusion Check
    create_box(6, 18.5, 4, 0.8, 'STEP 1: Exclusion Check (HIGHEST PRIORITY)\nImageType[10] == "I1" OR ImageType[2] == "INVALID"?', colors['priority'])
    create_arrow(8, 18.5, 10, 18.5, 'YES')
    create_box(10.5, 18.5, 1.8, 0.6, 'EXCLUDED\n(Category 1)', colors['category'], 8)
    
    create_arrow(6, 18.1, 6, 17.4, 'NO')
    
    # Step 2: Tissue Doppler Detection
    create_box(6, 17, 4, 0.8, 'STEP 2: Tissue Doppler Detection (2ND PRIORITY)\nImageType[3] == "0019" OR "0003"?', colors['priority'])
    create_arrow(8, 17, 10, 17, 'YES')
    create_box(10.5, 17, 1.8, 0.6, 'TISSUE DOPPLER\n(Category 2)', colors['category'], 8)
    
    create_arrow(6, 16.6, 6, 15.9, 'NO')
    
    # Step 3: Side-by-side Detection
    create_box(6, 15.5, 4.5, 1.2, 'STEP 3: Side-by-side Detection (3RD PRIORITY)\n• Exactly 2 ultrasound regions?\n• 1 B-mode (RegionDataType=1) + 1 Color Doppler (RegionDataType=2)?\n• Adjacent layout (gap < 100px + overlap)?', colors['priority'], 9)
    create_arrow(8.25, 15.5, 10, 15.5, 'YES')
    create_box(10.5, 15.5, 1.8, 0.6, 'SIDE-BY-SIDE\nB-mode + Doppler\n(Category 3)', colors['category'], 8)
    
    create_arrow(6, 14.9, 6, 14.2, 'NO')
    
    # Step 4: Frame Count Detection
    create_box(6, 13.8, 3.5, 0.8, 'STEP 4: Frame Count Detection\nNumberOfFrames > 1?', colors['decision'])
    
    # Multi-frame branch
    create_arrow(4.25, 13.8, 2.5, 13.8, 'YES')
    create_box(1.5, 13.8, 2, 0.6, 'Multi-frame\n(Cine loop)', colors['process'], 9)
    create_arrow(1.5, 13.5, 1.5, 12.8)
    
    # Multi-frame color doppler check
    create_box(1.5, 12.4, 2.5, 0.8, 'ImageType[3] == "0011"?\n(UltrasoundColorDataPresent=1)', colors['decision'], 8)
    create_arrow(0.25, 12.4, 0.25, 11.7, 'YES')
    create_box(0.5, 11.3, 1.5, 0.6, 'MULTI-FRAME\nwith Color Doppler\n(Category 4)', colors['category'], 7)
    
    create_arrow(2.75, 12.4, 2.75, 11.7, 'NO')
    create_box(2.5, 11.3, 1.5, 0.6, 'MULTI-FRAME\nwithout Color Doppler\n(Category 5)', colors['category'], 7)
    
    # Single-frame branch
    create_arrow(7.75, 13.8, 9.5, 13.8, 'NO')
    create_box(10.5, 13.8, 2, 0.6, 'Single-frame\n(Static image)', colors['process'], 9)
    create_arrow(10.5, 13.5, 10.5, 12.8)
    
    # Step 5: ImageType[3] Classification
    create_box(10.5, 12.4, 2.8, 1.0, 'STEP 5: ImageType[3] Classification\nClassify by vendor code', colors['decision'], 9)
    create_arrow(10.5, 11.9, 10.5, 11.2)
    
    # ImageType[3] decision tree
    create_box(10.5, 10.8, 3.5, 1.4, 'ImageType[3] Code:\n• "0001": 2D no Doppler\n• "0011": 2D with Doppler\n• "0002","0004","0005","0015": CW Doppler\n• "0008","0009": PW Doppler\n• "0020": Color M-Mode', colors['process'], 8)
    
    # Single-frame categories
    create_arrow(8.5, 10.8, 7, 10.2)
    create_box(6, 10.2, 1.8, 0.5, '2D SINGLE\nno Doppler\n(Category 6)', colors['category'], 7)
    
    create_arrow(8.5, 10.2, 7, 9.5)
    create_box(6, 9.5, 1.8, 0.5, '2D SINGLE\nwith Doppler\n(Category 7)', colors['category'], 7)
    
    create_arrow(10.5, 10.1, 10.5, 9.5)
    create_box(10.5, 9.2, 1.5, 0.5, 'CW DOPPLER\n(Category 8)', colors['category'], 7)
    
    create_arrow(12.5, 10.2, 12.5, 9.5)
    create_box(12.5, 9.2, 1.5, 0.5, 'PW DOPPLER\n(Category 9)', colors['category'], 7)
    
    create_arrow(12.5, 10.8, 12.5, 8.5)
    create_box(12.5, 8.2, 1.5, 0.5, 'COLOR M-MODE\n(Category 10)', colors['category'], 7)
    
    # Categories summary
    categories_text = '''
CLASSIFICATION CATEGORIES (v2.4 - 10 total):
1. Excluded Images - Invalid (ImageType[10]=="I1" or [2]=="INVALID")
2. Tissue Doppler (0019,0003) - HIGH PRIORITY
3. Side-by-side B-mode + Color Doppler - HIGH PRIORITY  
4. Multi-frame with Color Doppler (0011) - excluding side-by-side
5. Multi-frame without Color Doppler (0001) - grayscale cine loops
6. 2D Single-frame without Color Doppler (0001) - standard 2D images
7. 2D Single-frame with Color Doppler (0011) - static color flow
8. CW Doppler (0002,0004,0005,0015) - continuous wave spectrograms
9. PW Doppler (0008,0009) - pulsed wave spectrograms  
10. Color M-Mode (0020) - M-mode with color overlay
'''
    ax.text(2, 6.5, categories_text, fontsize=9, weight='bold', 
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue'))
    
    # Key features box
    features_text = '''
NEW FEATURES IN v2.4:
• Side-by-side layout detection using SequenceOfUltrasoundRegions
• Tissue Doppler classification (renamed from annotations)
• Enhanced spatial analysis for clinical accuracy
• Separates comparative displays from cine loops
• 10-category system (expanded from 9)

ALGORITHM HIGHLIGHTS:
• RegionDataType=1 (B-mode) + RegionDataType=2 (Color Doppler)
• Horizontal/vertical adjacency detection (gap < 100px)
• ImageType[3] code 0003 moved to tissue doppler
• Priority order: Exclusion → Tissue Doppler → Side-by-side → Frame → Code
'''
    ax.text(8, 6.5, features_text, fontsize=9, weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen'))
    
    # Example detection box
    example_text = '''
EXAMPLE SIDE-BY-SIDE DETECTION:
File: 1.2.840.113619.2.391.3279.1672658559.79.1.512.dcm
• 73 frames (cine loop)
• Region 1: B-mode (0,50) to (456,686) - 456x636px
• Region 2: Color Doppler (497,50) to (954,686) - 457x636px  
• Layout: Side-by-side with 41px gap
• Result: side_by_side_doppler (not multi_frame_with_doppler)
• Clinical use: Combined anatomical and hemodynamic assessment
'''
    ax.text(2, 3, example_text, fontsize=8, weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow'))
    
    plt.tight_layout()
    
    # Save the flowchart
    output_path = '/research/projects/Chao/Echo-preprocessing/DICOM_classification/analysis/v2_4_classification_flowchart.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ v2.4 flowchart saved to: {output_path}")
    
    return output_path

if __name__ == '__main__':
    print("Creating v2.4 DICOM classification flowchart...")
    create_v2_4_classification_flowchart()
    print("🎉 v2.4 flowchart complete!")