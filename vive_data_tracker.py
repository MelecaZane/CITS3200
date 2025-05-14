import openvr  # Library to interact with HTC Vive devices (VR system)
import time  # Library for time management (e.g., time tracking, sleep)
import csv  # For reading/writing CSV files
import os  # OS-level operations (e.g., checking file size)
import pandas as pd  # For working with data in DataFrames (used for xlsx output)
import scipy.io as sio  # For saving data in MATLAB's .mat format

# Boolean variable to control indefinite recording loop
another = True

# Set to keep track of created files
files = set()

def get_device_name_type_and_serial(device_index):
    """
    Retrieve the device's name, type (e.g., Headset, Controller, Tracker), and serial number.
    
    :param device_index: The index of the device in the VR system.
    :return: A tuple containing (device_name, device_type, device_serial).
    """
    # Get the device's class/type (e.g., headset, controller)
    device_class = openvr.VRSystem().getTrackedDeviceClass(device_index)

    # Get the device's model number/name
    device_name = openvr.VRSystem().getStringTrackedDeviceProperty(device_index, openvr.Prop_ModelNumber_String)
    
    # Get the device's serial number (unique identifier for the device)
    device_serial = openvr.VRSystem().getStringTrackedDeviceProperty(device_index, openvr.Prop_SerialNumber_String)

    # Determine the type of device based on the class
    if device_class == openvr.TrackedDeviceClass_HMD:
        device_type = "Headset"
    elif device_class == openvr.TrackedDeviceClass_Controller:
        device_type = "Controller"
    elif device_class == openvr.TrackedDeviceClass_TrackingReference:
        device_type = "Tracker"
    else:
        device_type = "Unknown"  # If not identified, it falls under "Unknown"

    return device_name, device_type, device_serial

def get_tracker_data():
    """
    Retrieves tracking data (pose) for all connected devices and categorizes them by type.
    """
    poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
    openvr.VRSystem().getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)

    device_data = {"Headset": [], "Controller": [], "Tracker": [], "Unknown": []}
    for i, pose in enumerate(poses):
        if pose.bPoseIsValid:
            timestamp = time.time()  # Capture timestamp at the time of recording
            device_name, device_type, device_serial = get_device_name_type_and_serial(i)
            tracker_pose = pose.mDeviceToAbsoluteTracking
            flat_pose = [item for row in tracker_pose for item in row]
            device_data[device_type].append([timestamp, i, device_name, device_serial] + flat_pose)

    return device_data

def write_data_to_files(data_buffer, export_format="csv"):
    """
    Writes the tracking data from the buffer to files in batches (default: CSV format).
    """
    if export_format != "csv":
        raise ValueError("Only CSV format is supported in this optimized version.")

    for device_type, devices in data_buffer.items():
        for device in devices:
            timestamp, device_id, device_name, device_serial, *pose_data = device
            file_name = f"{device_type.lower()}_{device_serial}_data.csv"

            with open(file_name, mode="a", newline="") as csv_file:
                csv_writer = csv.writer(csv_file)
                if csv_file.tell() == 0:  # If file is empty, write the header
                    header = ["Timestamp", "Device ID", "Device Name", "Device Serial", "M00", "M01", "M02", "M03",
                              "M10", "M11", "M12", "M13", "M20", "M21", "M22", "M23"]
                    csv_writer.writerow(header)

                # Write the data along with the pre-captured timestamp
                csv_writer.writerow([timestamp] + [device_id, device_name, device_serial] + pose_data)

def record_for_preset_time(duration_seconds, hz, export_format="csv"):
    """
    Records device tracking data for a preset time duration at a given frequency.
    
    :param duration_seconds: The total duration (in seconds) to record.
    :param hz: The frequency of data collection (in Hz, i.e., number of recordings per second).
    :param export_format: The format in which to save the data (default is "csv").
    """
    start_time = time.time()  # Start timer
    while time.time() - start_time < duration_seconds:  # Loop until the preset duration is reached
        device_data, completion_rate = get_tracker_data()  # Get tracking data
        write_data_to_files(device_data, export_format)  # Save the data
        time.sleep(1/hz)  # Wait for the next data collection (based on the frequency)
    print("Recording completed.")

def record_indefinitely(hz, export_format="csv"):
    """
    Optimized recording function with dynamic batch size based on polling frequency.
    
    :param hz: Polling frequency in Hz (samples per second).
    :param export_format: Format to export the data (default: "csv").
    """
    batch_size = max(1, hz)  # Set dynamic batch size to match the polling frequency
    data_buffer = {"Headset": [], "Controller": [], "Tracker": [], "Unknown": []}
    
    print(f"Starting recording with polling frequency: {hz} Hz and batch size: {batch_size}")
    
    while another:  # Continue recording until 'another' is set to False
        start_time = time.time()
        device_data = get_tracker_data()  # Get tracking data

        # Add data to buffer
        for key, value in device_data.items():
            data_buffer[key].extend(value)

        # Write to file if buffer size is reached
        if sum(len(v) for v in data_buffer.values()) >= batch_size:
            write_data_to_files(data_buffer, export_format)
            data_buffer = {"Headset": [], "Controller": [], "Tracker": [], "Unknown": []}  # Clear buffer

        # Ensure loop adheres to specified frequency
        elapsed = time.time() - start_time
        time.sleep(max(0, 1/hz - elapsed))
        
def map_device_id_to_physical_tracker():
    """
    Maps each device ID to a physical tracker (Headset, Controller, Tracker) and prints the mapping.
    
    :return: A dictionary mapping device IDs to their type, name, and serial number.
    """
    device_mapping = {}
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if openvr.VRSystem().isTrackedDeviceConnected(i):  # Check if the device is connected
            device_name, device_type, device_serial = get_device_name_type_and_serial(i)
            device_mapping[i] = (device_type, device_name, device_serial)
    
    # Print the device mapping (ID -> Type, Name, Serial Number)
    print("Device Mapping:")
    for device_id, (device_type, device_name, device_serial) in device_mapping.items():
        print(f"ID {device_id}: {device_type}, Name: {device_name}, Serial: {device_serial}")
    
    return
