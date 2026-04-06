import time
import threading
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets

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

    # BrainFlow exposes EmotiBit data across three presets, each with its own
    # ring buffer and sampling rate:
    #   DEFAULT_PRESET   – IMU (accel/gyro/mag) at 25 Hz
    #   AUXILIARY_PRESET – PPG (red/IR/green)    at 25 Hz
    #   ANCILLARY_PRESET – EDA + temperature     at 15 Hz
    # Channel indices come from the static descriptor for each preset.

    def _descr(preset):
        return BoardShim.get_board_descr(BoardIds.EMOTIBIT_BOARD, preset)

    imu_descr = _descr(BrainFlowPresets.DEFAULT_PRESET)
    accel_channels = imu_descr.get("accel_channels", []) or []
    gyro_channels  = imu_descr.get("gyro_channels", []) or []
    mag_channels   = imu_descr.get("magnetometer_channels", []) or []
    imu_ts_channel = imu_descr.get("timestamp_channel")

    ppg_descr    = _descr(BrainFlowPresets.AUXILIARY_PRESET)
    ppg_channels = ppg_descr.get("ppg_channels", []) or []  # [red, IR, green]
    ppg_ts_channel = ppg_descr.get("timestamp_channel")

    bio_descr            = _descr(BrainFlowPresets.ANCILLARY_PRESET)
    eda_channels         = bio_descr.get("eda_channels", []) or []
    temperature_channels = bio_descr.get("temperature_channels", []) or []
    bio_ts_channel       = bio_descr.get("timestamp_channel")

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

            def _ts(matrix, ts_col, col_idx):
                """Return the hardware timestamp for sample col_idx, or wall time."""
                if ts_col is not None:
                    return matrix[ts_col, col_idx]
                return time.time()

            def _v(matrix, channels, ch_idx, col_idx):
                """Safely read one value from a channel list; return empty string if absent."""
                if channels and ch_idx < len(channels):
                    return matrix[channels[ch_idx], col_idx]
                return ""

            # CSV column layout (indices 0-14):
            #  0:Timestamp  1:PPG_Red  2:PPG_IR  3:PPG_Green  4:EDA  5:Temperature
            #  6:AccelX  7:AccelY  8:AccelZ  9:GyroX  10:GyroY  11:GyroZ
            #  12:MagX  13:MagY  14:MagZ

            while another and not stop_event.is_set():
                loop_start = time.time()

                # Flush each preset's ring buffer independently.
                imu_data = board.get_board_data(preset=BrainFlowPresets.DEFAULT_PRESET)
                ppg_data = board.get_board_data(preset=BrainFlowPresets.AUXILIARY_PRESET)
                bio_data = board.get_board_data(preset=BrainFlowPresets.ANCILLARY_PRESET)

                # --- IMU rows (accel / gyro / mag) ---
                for i in range(imu_data.shape[1]):
                    v = [""] * 15
                    v[0]  = _ts(imu_data, imu_ts_channel, i)
                    v[6]  = _v(imu_data, accel_channels, 0, i)
                    v[7]  = _v(imu_data, accel_channels, 1, i)
                    v[8]  = _v(imu_data, accel_channels, 2, i)
                    v[9]  = _v(imu_data, gyro_channels, 0, i)
                    v[10] = _v(imu_data, gyro_channels, 1, i)
                    v[11] = _v(imu_data, gyro_channels, 2, i)
                    v[12] = _v(imu_data, mag_channels, 0, i)
                    v[13] = _v(imu_data, mag_channels, 1, i)
                    v[14] = _v(imu_data, mag_channels, 2, i)
                    file.write(",".join(str(x) for x in v) + "\n")

                # --- PPG rows (red / IR / green) ---
                for i in range(ppg_data.shape[1]):
                    v = [""] * 15
                    v[0] = _ts(ppg_data, ppg_ts_channel, i)
                    v[1] = _v(ppg_data, ppg_channels, 0, i)
                    v[2] = _v(ppg_data, ppg_channels, 1, i)
                    v[3] = _v(ppg_data, ppg_channels, 2, i)
                    file.write(",".join(str(x) for x in v) + "\n")

                # --- Biometric rows (EDA / temperature) ---
                for i in range(bio_data.shape[1]):
                    v = [""] * 15
                    v[0] = _ts(bio_data, bio_ts_channel, i)
                    v[4] = _v(bio_data, eda_channels, 0, i)
                    v[5] = _v(bio_data, temperature_channels, 0, i)
                    file.write(",".join(str(x) for x in v) + "\n")

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
