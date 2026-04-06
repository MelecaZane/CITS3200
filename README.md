https://github.com/MelecaZane/CITS3200
# Installation
## Prerequisites
- [*Python 3*](https://python.org/) (tested working with Python 3.11.8)
- [*Ultraleap Gemini* hand tracking software](https://developer.leapmotion.com/tracking-software-download) (installed to it's default location)
    - *Ultraleap Tracking* service must be running
- [*Polhemus Liberty* USB driver](https://ftp.polhemus1.com/pub/Trackers/Liberty/)
    - *Note:* This driver is **old** and not compatible with the *Core Isolation* feature of Windows 11. Please disable this feature to use *Polhemus* tracking.
- [*SteamVR*](https://store.steampowered.com/app/250820/SteamVR/)
- [*EmotiBit Software and Drivers*](https://github.com/EmotiBit/EmotiBit_Docs/blob/master/Getting_Started.md)
    - Follow the *Getting Started* steps in the link to install both the *EmotiBit* software and drivers.

## Compatibility
- Tested and working Windows 10 and Windows 11*
    - Due to its age, the *Polhemus Liberty USB driver* is **not compatible** with the *Microsoft Vulnerable Driver Blocklist* feature of *Core Isolation* in Windows 11. If run while enabled, only zeroes will be captured by *Polhemus* tracking.
- Tested and working with Python 3.11.8

## Install Instructions
> *Ensure the above [prerequisites](#prerequisites) are installed **before** proceeding.*
1. Download this repository as a *zip* file.
    - Hit the green 'Code' button at the top of the page, then 'Download ZIP'.
2. Extract the *zip* file to the desired directory.
3. Double-click `initialise.py` (run with *Python*) and wait while the environment is setup.
    - This process requires an internet connection.
    - This process should only be completed **once** and can take quite a while, but no user interaction is required, so feel free to walk away from the computer.
    - A message saying, `Initialisation complete. Run 'start.py' to start the application` should be shown once the process is complete.
5. Double-click `start.py` to start the program.
    - This should be used each time you wish to start the program.

### *"`start.py` isn't working!"*
> *If `start.py` isn't working, please check the following.*
- Ensure the listed [*prerequisites*](#prerequisites) are met.
- Ensure no errors occurred during the running of `initialise.py`.
- Ensure you are running it using Python.

# Usage
## User Guide
1. Run `start.py` with Python to launch the program.
2. Select the tracker checkboxes you intend to use.
3. Enter the polling rate (in Hz) that data should be tracked at.
4. Press `Start` to begin tracking (this may take a moment to begin on slower systems).
5. When ready, press `Stop` to halt tracking.
6. Press `Save zip to...` to select a location for the zip file containing all the tracked data to be saved.
   - Ensure you do this before doing another tracking run, files may be overwritten otherwise!
  
*Note:* When using *EmotiBit* tracking, ensure the system is connected to the same network as the *EmotiBit* device itself and ensure you know the device's **IP address**.

## Data Interpretation
For all tracker types, each row of output is a single "poll", each poll is labeled with its Unix timestamp (seconds since *00:00:00 UTC on 1 January 1970*).
### Polhemus
- Output file contains tracking information for **two** tracking nodes.
    - `x`, `y`, and `z` for each node
    - Pitch, roll, and yaw for each node
- Output also contains tracking data for stylus accessory (`0` if not present).

### Ultraleap Leapmotion 2
> **WARNING**: *These files contain a **lot** of data!*
- Output file contains tracking information for **two** hands (left + right).
    - *Each hand* has a palm, arm, and *five digits* (thumb, index, middle, ring, and pinky)
    - *Each digit* has *four bones* (metacarpal, proximal, intermediate, distal)
    - *Each bone* has a width, x-position, y-position, z-position, and rotation (w)
- Thus each "poll" has ***217 columns*** of output (including the timestamp).

### Virtual Reality
- Each output file corresponds to a single tracker picked up by *OpenVR*/*SteamVR*.
- Each poll for each tracker contains the information from a 3x4 transformation matrix used to represent the pose of the corresponding device (see matrix below).
    - `M00`, `M01`, `M02`: Rotation component for the x-axis,
    - `M10`, `M11`, `M12`: Rotation component for the y-axis,
    - `M20`, `M21`, `M22`: Rotation component for the z-axis,
    - `M03`, `M13`, `M23`: Translation (position) component for the x, y, and z directions
- The output essentially contains a "flattened" matrix for each poll.
```
| M00 M01 M02 M03 |
| M10 M11 M12 M13 |
| M20 M21 M22 M23 |
```

### EmotiBit
- This tracker outputs three files, one for each of the following data sets:
    - Accel/Gyro/Mag: Sampled at 25Hz
    - PPG Red/IR/Green: Sampled at 25Hz (used to calculate heart-rate)
    - EDA + Temperature: Sampled at 15Hz
- The sampling rates listed above are set by the *EmotiBit* tracker itself. They will track at this rate regardless of the rate set in the program (other simultaneous trackers will still respect the set rate).
- Setting a static IP address on your router for the *EmotiBit* may make life easier as it will prevent having to find out the dynamically-assigned IP address each use.
