from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError
import time
import threading

# EmotiBit connects over WiFi using the BrainFlow SDK.
# Ensure the EmotiBit device is powered on and connected to the same WiFi network.
# The IP address of the EmotiBit device is required to connect.
#
# Install BrainFlow: pip install brainflow
#
# BrainFlow docs: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html

EMOTIBIT_BOARD_ID = BoardIds.EMOTIBIT_BOARD.value

# Global variable to stop the polling and output of EmotiBit data.
# Setting this to False at any time will stop output.
another = False
stop_event = threading.Event()
start_capture_event = threading.Event()

# Board instance used to communicate with the EmotiBit device.
board = None


def initialise_emotibit(ip_address: str) -> BoardShim:
    """
    Initialises the EmotiBit board via BrainFlow over WiFi.

    :param ip_address: The IP address of the EmotiBit device on the local network.
    :return: A prepared and streaming BoardShim instance.
    """
    params = BrainFlowInputParams()
    params.ip_address = ip_address

    new_board = BoardShim(EMOTIBIT_BOARD_ID, params)
    new_board.prepare_session()
    new_board.start_stream()
    return new_board


def close_emotibit(board_instance: BoardShim):
    """
    Stops the data stream and releases the EmotiBit board session.

    :param board_instance: The BoardShim instance to close.
    """
    try:
        board_instance.stop_stream()
        board_instance.release_session()
    except Exception as e:
        print(f"EmotiBit: Error during close: {e}")


def output_data_with_callback(hz: int, ip_address: str, callback_func=None):
    """
    Initialises the EmotiBit, signals the callback when ready, then records sensor
    data to 'emotibit_output.csv' until stopped.

    The EmotiBit streams at its native rate (25 Hz as reported by BrainFlow's board
    descriptor for BoardIds.EMOTIBIT_BOARD). Each call to the polling loop drains the
    internal BrainFlow buffer, so all hardware samples are written even when the
    user-specified polling rate differs from the native sampling rate.

    :param hz: The rate (in Hz) at which the buffer is drained and written.
    :param ip_address: The IP address of the EmotiBit device.
    :param callback_func: Optional function called when the device is ready.
    """
    global another, board

    another = True

    # Retrieve channel indices once for this board type.
    timestamp_ch = BoardShim.get_timestamp_channel(EMOTIBIT_BOARD_ID)
    accel_channels = BoardShim.get_accel_channels(EMOTIBIT_BOARD_ID)   # X, Y, Z
    gyro_channels = BoardShim.get_gyro_channels(EMOTIBIT_BOARD_ID)     # X, Y, Z
    mag_channels = BoardShim.get_magnetometer_channels(EMOTIBIT_BOARD_ID)  # X, Y, Z

    # All data channels in the order they will appear as CSV columns.
    all_channels = [timestamp_ch] + accel_channels + gyro_channels + mag_channels
    headers = (
        "Timestamp,"
        "AccelX,AccelY,AccelZ,"
        "GyroX,GyroY,GyroZ,"
        "MagX,MagY,MagZ"
    )

    try:
        board = initialise_emotibit(ip_address)
    except BrainFlowError as e:
        print(f"EmotiBit: Could not connect to device at {ip_address}: {e}")
        if callback_func:
            callback_func()
        return
    except Exception as e:
        print(f"EmotiBit: Unexpected error during initialisation: {e}")
        if callback_func:
            callback_func()
        return

    with open("emotibit_output.csv", "w") as file:
        file.write(headers + "\n")

        # Signal main thread that this tracker is initialised and ready.
        if callback_func:
            callback_func()

        # Wait for the synchronised start signal before recording data.
        start_capture_event.wait()

        while another and not stop_event.is_set():
            # Drain all samples accumulated in the BrainFlow buffer.
            data = board.get_board_data()
            if data.shape[1] > 0:
                for sample_idx in range(data.shape[1]):
                    row = ",".join(str(data[ch][sample_idx]) for ch in all_channels)
                    file.write(row + "\n")
            time.sleep(1 / hz)

    close_emotibit(board)
