import time
import threading
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

# Requires BrainFlow SDK: pip install brainflow
# EmotiBit connects over WiFi.  Provide the device's IP address (or leave
# blank to use BrainFlow's multicast auto-discovery on port 9000).
# https://brainflow.org/
# https://github.com/EmotiBit/EmotiBit_Docs

# Global variable to stop the polling and output of EmotiBit data.
# Setting this to False at any time will stop output.
another = False
stop_event = threading.Event()
start_capture_event = threading.Event()


def initialise_emotibit_with_callback(hz: int, ip_address: str = "", callback_func=None):
    """
    Initialises the EmotiBit board via BrainFlow, signals the main application
    when ready, then captures data at the given polling rate until stopped.

    Parameters
    ----------
    hz : int
        Polling rate in Hz.
    ip_address : str
        IP address of the EmotiBit device on the WiFi network.  Leave empty
        to use BrainFlow's multicast auto-discovery (port 9000).
    callback_func : callable, optional
        Called once the board is streaming and ready, so that the main thread
        can start the unified timer.
    """
    global another

    another = True

    # Configure BrainFlow input parameters for EmotiBit (WiFi connection).
    params = BrainFlowInputParams()
    params.ip_address = ip_address
    params.ip_port = 9000

    board = BoardShim(BoardIds.EMOTIBIT_BOARD, params)
    try:
        board.prepare_session()
        board.start_stream()
    except Exception:
        try:
            board.release_session()
        except Exception:
            pass
        raise

    # Retrieve the channel indices for each data type from the live board description.
    # Call get_board_descr() on the board instance (not the class) after start_stream()
    # so that the descriptor is populated with the actual connected device's channels
    # (e.g. PPG, EDA, temperature channels which are absent in the static bundled JSON).
    board_id = BoardIds.EMOTIBIT_BOARD
    descr = board.get_board_descr(board_id)
    ppg_channels         = descr.get("ppg_channels", []) or []          # [red, IR, green]
    eda_channels         = descr.get("eda_channels", []) or []
    temperature_channels = descr.get("temperature_channels", []) or []
    accel_channels       = descr.get("accel_channels", []) or []        # [X, Y, Z]
    gyro_channels        = descr.get("gyro_channels", []) or []         # [X, Y, Z]
    mag_channels         = descr.get("magnetometer_channels", []) or [] # [X, Y, Z]
    timestamp_channel    = descr.get("timestamp_channel")

    try:
        with open("emotibit_output.csv", "w") as file:
            file.write(
                "Timestamp,"
                "PPG_Red,PPG_IR,PPG_Green,"
                "EDA,"
                "Temperature,"
                "AccelX,AccelY,AccelZ,"
                "GyroX,GyroY,GyroZ,"
                "MagX,MagY,MagZ\n"
            )

            # Signal the main application that the board is ready.
            if callback_func:
                callback_func()

            # Wait for the unified start signal before recording data.
            start_capture_event.wait()

            while another and not stop_event.is_set():
                loop_start = time.time()

                data = board.get_board_data()  # Returns all samples accumulated since last call

                # Helper to safely read a value from a channel list at sample index i.
                def val(channels, col, i):
                    if channels and col < len(channels):
                        return data[channels[col], i]
                    return ""

                # Write one CSV row per device sample so no data is discarded.
                # data shape: (num_channels, num_samples); each column is one sample.
                for i in range(data.shape[1]):
                    # Prefer the board's own hardware timestamp when available.
                    if timestamp_channel is not None:
                        timestamp = data[timestamp_channel, i]
                    else:
                        timestamp = time.time()

                    row = (
                        f"{timestamp},"
                        f"{val(ppg_channels, 0, i)},{val(ppg_channels, 1, i)},{val(ppg_channels, 2, i)},"
                        f"{val(eda_channels, 0, i)},"
                        f"{val(temperature_channels, 0, i)},"
                        f"{val(accel_channels, 0, i)},{val(accel_channels, 1, i)},{val(accel_channels, 2, i)},"
                        f"{val(gyro_channels, 0, i)},{val(gyro_channels, 1, i)},{val(gyro_channels, 2, i)},"
                        f"{val(mag_channels, 0, i)},{val(mag_channels, 1, i)},{val(mag_channels, 2, i)}"
                    )
                    file.write(row + "\n")

                # Sleep for the remainder of the polling interval.
                elapsed = time.time() - loop_start
                sleep_time = (1 / hz) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    finally:
        try:
            board.stop_stream()
        except Exception:
            pass
        try:
            board.release_session()
        except Exception:
            pass
