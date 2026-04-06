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

    # Retrieve the channel indices for each data type from the board description.
    # Use get_board_descr() dict instead of static helper methods; the helpers raise
    # UNSUPPORTED_BOARD_ERROR when a channel type is absent from the board descriptor.
    board_id = BoardIds.EMOTIBIT_BOARD
    descr = BoardShim.get_board_descr(board_id)
    ppg_channels         = descr.get("ppg_channels", []) or []          # [red, IR, green]
    eda_channels         = descr.get("eda_channels", []) or []
    temperature_channels = descr.get("temperature_channels", []) or []
    accel_channels       = descr.get("accel_channels", []) or []        # [X, Y, Z]
    gyro_channels        = descr.get("gyro_channels", []) or []         # [X, Y, Z]
    mag_channels         = descr.get("magnetometer_channels", []) or [] # [X, Y, Z]

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

                if data.shape[1] > 0:
                    # Use the timestamp of the most-recent sample for the row.
                    timestamp = time.time()

                    # Helper to safely read the latest value from a channel list.
                    def latest(channels, col=0):
                        if channels and col < len(channels):
                            col_data = data[channels[col], :]
                            return col_data[-1] if len(col_data) > 0 else ""
                        return ""

                    ppg_red   = latest(ppg_channels, 0)
                    ppg_ir    = latest(ppg_channels, 1)
                    ppg_green = latest(ppg_channels, 2)
                    eda       = latest(eda_channels, 0)
                    temp      = latest(temperature_channels, 0)
                    accel_x   = latest(accel_channels, 0)
                    accel_y   = latest(accel_channels, 1)
                    accel_z   = latest(accel_channels, 2)
                    gyro_x    = latest(gyro_channels, 0)
                    gyro_y    = latest(gyro_channels, 1)
                    gyro_z    = latest(gyro_channels, 2)
                    mag_x     = latest(mag_channels, 0)
                    mag_y     = latest(mag_channels, 1)
                    mag_z     = latest(mag_channels, 2)

                    row = (
                        f"{timestamp},"
                        f"{ppg_red},{ppg_ir},{ppg_green},"
                        f"{eda},"
                        f"{temp},"
                        f"{accel_x},{accel_y},{accel_z},"
                        f"{gyro_x},{gyro_y},{gyro_z},"
                        f"{mag_x},{mag_y},{mag_z}"
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
