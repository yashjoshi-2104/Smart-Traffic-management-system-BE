# data_preprocessing/explore_ngsim.py
"""
Explore NGSIM dataset
Understand the data structure and characteristics
"""

import pandas as pd
import numpy as np


def load_ngsim_data(filepath="../data/raw/ngsim_us101.csv"):
    """
    Load NGSIM dataset
    
    Returns:
        DataFrame: NGSIM data
    """
    print("📥 Loading NGSIM data...")
    
    # NGSIM CSV is comma-separated
    df = pd.read_csv(filepath)
    
    print(f"✅ Loaded {len(df):,} records")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Shape: {df.shape}")
    
    return df


def explore_dataset(df):
    """Print dataset statistics"""
    
    print("\n" + "=" * 70)
    print("📊 DATASET OVERVIEW")
    print("=" * 70)
    
    # Basic info
    print(f"\n📈 Dataset Size:")
    print(f"   Total records: {len(df):,}")
    print(f"   Unique vehicles: {df['Vehicle_ID'].nunique():,}")
    print(f"   Time span: {df['Frame_ID'].min()/10:.1f}s - {df['Frame_ID'].max()/10:.1f}s")
    print(f"   Duration: {(df['Frame_ID'].max() - df['Frame_ID'].min())/10/60:.1f} minutes")
    
    # Vehicle types
    print(f"\n🚗 Vehicle Types:")
    vehicle_types = {
        1: "Motorcycle",
        2: "Car",
        3: "Truck"
    }
    for vtype, count in df['v_Class'].value_counts().items():
        type_name = vehicle_types.get(vtype, f"Unknown ({vtype})")
        print(f"   {type_name}: {count:,} records ({count/len(df)*100:.1f}%)")
    
    # Speed statistics
    print(f"\n⚡ Speed Statistics (converted to m/s):")
    speeds_ms = df['v_Vel'] * 0.3048  # Convert ft/s to m/s
    print(f"   Mean: {speeds_ms.mean():.2f} m/s ({speeds_ms.mean()*3.6:.2f} km/h)")
    print(f"   Max: {speeds_ms.max():.2f} m/s ({speeds_ms.max()*3.6:.2f} km/h)")
    print(f"   Min: {speeds_ms.min():.2f} m/s")
    print(f"   Std: {speeds_ms.std():.2f} m/s")
    
    # Lane distribution
    print(f"\n🛣️  Lane Distribution:")
    for lane, count in df['Lane_ID'].value_counts().sort_index().items():
        print(f"   Lane {lane}: {count:,} records ({count/len(df)*100:.1f}%)")
    
    # Sample vehicles
    print(f"\n🚙 Sample Vehicle Trajectories:")
    sample_vehicles = df['Vehicle_ID'].unique()[:3]
    
    for vid in sample_vehicles:
        vehicle_data = df[df['Vehicle_ID'] == vid]
        duration = len(vehicle_data) / 10  # 10 FPS
        distance = (vehicle_data['Local_Y'].max() - vehicle_data['Local_Y'].min()) * 0.3048
        
        print(f"\n   Vehicle {vid}:")
        print(f"     Duration: {duration:.1f}s")
        print(f"     Distance: {distance:.1f}m")
        print(f"     Avg Speed: {vehicle_data['v_Vel'].mean()*0.3048:.2f} m/s")
        print(f"     Vehicle Class: {vehicle_types.get(vehicle_data['v_Class'].iloc[0], 'Unknown')}")


def analyze_congestion(df):
    """Analyze traffic congestion patterns"""
    
    print("\n" + "=" * 70)
    print("🚦 CONGESTION ANALYSIS")
    print("=" * 70)
    
    # Group by time frame
    frames = df.groupby('Frame_ID').agg({
        'Vehicle_ID': 'count',
        'v_Vel': 'mean'
    }).rename(columns={
        'Vehicle_ID': 'vehicle_count',
        'v_Vel': 'avg_speed_fps'
    })
    
    frames['avg_speed_ms'] = frames['avg_speed_fps'] * 0.3048
    frames['time_seconds'] = frames.index / 10
    
    print(f"\n📊 Traffic Flow:")
    print(f"   Max vehicles at once: {frames['vehicle_count'].max()}")
    print(f"   Min vehicles at once: {frames['vehicle_count'].min()}")
    print(f"   Avg vehicles at once: {frames['vehicle_count'].mean():.1f}")
    
    # Find congestion periods (low speed, high density)
    congested = frames[
        (frames['avg_speed_ms'] < 5.0) &  # < 18 km/h
        (frames['vehicle_count'] > frames['vehicle_count'].median())
    ]
    
    print(f"\n🔴 Congestion Periods:")
    print(f"   Frames with congestion: {len(congested)}")
    print(f"   Percentage of time: {len(congested)/len(frames)*100:.1f}%")
    
    if len(congested) > 0:
        print(f"   Avg speed during congestion: {congested['avg_speed_ms'].mean():.2f} m/s")
        print(f"   Avg vehicles during congestion: {congested['vehicle_count'].mean():.1f}")


def extract_sample_period(df, start_frame=1000, duration_seconds=60):
    """
    Extract a sample period for SUMO conversion
    
    Args:
        df: Full dataset
        start_frame: Starting frame
        duration_seconds: Duration to extract
        
    Returns:
        DataFrame: Filtered data
    """
    end_frame = start_frame + (duration_seconds * 10)
    
    sample = df[
        (df['Frame_ID'] >= start_frame) &
        (df['Frame_ID'] < end_frame)
    ].copy()
    
    print(f"\n" + "=" * 70)
    print(f"✂️  SAMPLE EXTRACTION")
    print("=" * 70)
    print(f"\n📌 Extracted period:")
    print(f"   Start frame: {start_frame} ({start_frame/10:.1f}s)")
    print(f"   End frame: {end_frame} ({end_frame/10:.1f}s)")
    print(f"   Duration: {duration_seconds}s")
    print(f"   Records: {len(sample):,}")
    print(f"   Unique vehicles: {sample['Vehicle_ID'].nunique()}")
    
    # Save sample
    output_path = "../data/processed/ngsim_sample_60s.csv"
    sample.to_csv(output_path, index=False)
    print(f"\n💾 Saved to: {output_path}")
    
    return sample


if __name__ == "__main__":
    # Load data
    df = load_ngsim_data()
    
    # Explore
    explore_dataset(df)
    
    # Analyze congestion
    analyze_congestion(df)
    
    # Extract sample for SUMO conversion
    sample = extract_sample_period(df, start_frame=1000, duration_seconds=60)
    
    print("\n" + "=" * 70)
    print("✅ EXPLORATION COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Review the statistics above")
    print("  2. Run map_to_sumo.py to convert to SUMO format")
    print("  3. Generate route files for simulation")