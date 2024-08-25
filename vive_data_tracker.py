import openvr
import time

openvr.init(openvr.VRApplication_Scene)

def get_tracker_data():
    poses = openvr.TrackedDevicePose_t()
    openvr.VRSystem().getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)

    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if poses[i].bPoseIsValid:
            device_class = openvr.VRSystem().getTrackedDeviceClass(i)
            if device_class == openvr.TrackedDeviceClass_TrackingReference:
                print(f"Tracker {i} data:")
                print(f"Position: {poses[i].mDeviceToAbsoluteTracking[:3]}")
                print(f"Rotation: {poses[i].mDeviceToAbsoluteTracking[3:7]}")
                print()

try:
    while True:
        get_tracker_data()
        time.sleep(0.1)  # Polling interval
except KeyboardInterrupt:
    print("Exiting...")
finally:
    openvr.shutdown()
