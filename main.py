import threading
import time
from typing import Callable, List, Optional

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.menu import MDDropdownMenu

# Standard SPP UUID for RFCOMM
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

KV = """
#:import dp kivy.metrics.dp

<RootScreen@MDScreen>:
    md_bg_color: 0, 0, 0, 1
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(12)

        MDCard:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(8)
            size_hint_y: None
            height: self.minimum_height
            md_bg_color: 0.08, 0.08, 0.08, 1
            MDBoxLayout:
                spacing: dp(8)
                size_hint_y: None
                height: dp(48)
                MDDropDownItem:
                    id: device_dropdown
                    text: app.device_dropdown_text
                    on_release: app.open_device_menu()
                    text_color: 1,1,1,1
                    size_hint_x: 1
            MDBoxLayout:
                spacing: dp(8)
                size_hint_y: None
                height: dp(48)
                MDRaisedButton:
                    text: "Connect"
                    disabled: not app.can_connect
                    md_bg_color: (1, 0.76, 0, 1) if not self.disabled else (.35, .35, .35, 1)
                    text_color: 1,1,1,1
                    size_hint_x: 0.5
                    on_release: app.connect_selected()
                MDRaisedButton:
                    text: "Disconnect"
                    disabled: not app.can_disconnect
                    md_bg_color: (1, 0.76, 0, 1) if not self.disabled else (.35, .35, .35, 1)
                    text_color: 1,1,1,1
                    size_hint_x: 0.5
                    on_release: app.disconnect()
            MDLabel:
                id: device_label
                text: app.device_text
                theme_text_color: "Custom"
                text_color: 1,1,1,1
                font_style: "Body2"
                size_hint_y: None
                height: self.texture_size[1]
            MDLabel:
                id: status_label
                text: app.status_text
                theme_text_color: "Custom"
                text_color: .8,.8,.8,1
                font_style: "Caption"
                size_hint_y: None
                height: self.texture_size[1]

        MDCard:
            orientation: "vertical"
            padding: dp(12)
            md_bg_color: 0.08, 0.08, 0.08, 1
            MDLabel:
                text: "Exposure Control"
                font_style: "H6"
                theme_text_color: "Custom"
                text_color: 1,1,1,1
                size_hint_y: None
                height: self.texture_size[1]
            MDBoxLayout:
                spacing: dp(12)
                size_hint_y: None
                height: dp(60)
                MDTextField:
                    id: shots_input
                    hint_text: "Shots"
                    text: "3"
                    mode: "rectangle"
                    input_filter: "int"
                    helper_text: "Number of exposures"
                    helper_text_mode: "on_focus"
                    text_color: 1,1,1,1
                    line_color_focus: 1,0.76,0,1
                MDTextField:
                    id: seconds_input
                    hint_text: "Seconds"
                    text: "20"
                    mode: "rectangle"
                    input_filter: "int"
                    helper_text: "Exposure length"
                    helper_text_mode: "on_focus"
                    text_color: 1,1,1,1
                    line_color_focus: 1,0.76,0,1
            MDBoxLayout:
                spacing: dp(12)
                size_hint_y: None
                height: dp(52)
                MDRaisedButton:
                    text: "Start"
                    disabled: not app.can_start
                    md_bg_color: (1, 0.76, 0, 1) if not self.disabled else (.35, .35, .35, 1)
                    text_color: 1,1,1,1
                    on_release: app.start_sequence()
                MDRaisedButton:
                    text: "Abort"
                    disabled: not app.can_abort
                    md_bg_color: (1, 0.76, 0, 1) if not self.disabled else (.35, .35, .35, 1)
                    text_color: 1,1,1,1
                    on_release: app.abort_sequence()
            MDLabel:
                id: total_label
                text: app.total_text
                theme_text_color: "Custom"
                text_color: 1,1,1,1
            MDLabel:
                id: remaining_label
                text: app.remaining_text
                theme_text_color: "Custom"
                text_color: 1,1,1,1
            MDLabel:
                id: progress_label
                text: app.progress_label
                theme_text_color: "Custom"
                text_color: 1,1,1,1
            MDProgressBar:
                id: progress_bar
                value: app.progress_value
                max: 100
            MDLabel:
                id: eta_label
                text: app.eta_text
                theme_text_color: "Custom"
                text_color: 1,1,1,1

        MDCard:
            orientation: "vertical"
            padding: dp(12)
            md_bg_color: 0.08, 0.08, 0.08, 1
            MDLabel:
                text: "Log"
                font_style: "H6"
                theme_text_color: "Custom"
                text_color: 1,1,1,1
                size_hint_y: None
                height: self.texture_size[1]
            ScrollView:
                size_hint: 1, None
                height: dp(200)
                MDLabel:
                    id: log_label
                    text: app.log_text
                    markup: True
                    size_hint_y: None
                    height: self.texture_size[1]
                    font_style: "Body2"
                    theme_text_color: "Custom"
                    text_color: 1,1,1,1
RootScreen:
"""


def format_seconds(total_seconds: float) -> str:
    total_seconds = max(0, total_seconds)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class LoggerBuffer:
    """Keeps a bounded scrollback log for the UI."""

    def __init__(self, limit: int = 200):
        self.limit = limit
        self.lines: List[str] = []

    def add(self, message: str) -> str:
        timestamp = time.strftime("%H:%M:%S")
        self.lines.append(f"[color=#888888]{timestamp}[/color] {message}")
        if len(self.lines) > self.limit:
            self.lines = self.lines[-self.limit :]
        return "\n".join(self.lines)


class BluetoothClient:
    """RFCOMM SPP helper using PyJNIus on Android; desktop stub for testing."""

    def __init__(
        self,
        on_connected: Callable[[str], None],
        on_disconnected: Callable[[str], None],
        on_message: Callable[[str], None],
        on_log: Callable[[str], None],
    ):
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.on_message = on_message
        self.on_log = on_log
        self._socket = None
        self._input_stream = None
        self._output_stream = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._platform_is_android = platform == "android"
        if self._platform_is_android:
            # Import jnius classes lazily to keep desktop testing working.
            from jnius import autoclass, cast  # type: ignore

            self.autoclass = autoclass
            self.cast = cast

    # Android permission handling
    def ensure_permissions(self):
        if not self._platform_is_android:
            return True
        try:
            autoclass = self.autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ActivityCompat = autoclass("androidx.core.app.ActivityCompat")
            ContextCompat = autoclass("androidx.core.content.ContextCompat")
            Manifest = autoclass("android.Manifest")
            Build = autoclass("android.os.Build")
            activity = PythonActivity.mActivity

            sdk = Build.VERSION.SDK_INT
            needed = []
            if sdk >= 31:
                needed.extend([Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN])
            else:
                needed.extend([Manifest.permission.BLUETOOTH, Manifest.permission.BLUETOOTH_ADMIN])
                needed.append(Manifest.permission.ACCESS_FINE_LOCATION)

            missing = []
            for perm in needed:
                granted = ContextCompat.checkSelfPermission(activity, perm)
                if granted != 0:
                    missing.append(perm)
            if missing:
                ActivityCompat.requestPermissions(activity, missing, 1)
                self.on_log("Requested Bluetooth permissions; please approve on device.")
            return True
        except Exception as exc:  # pragma: no cover - Android only
            self.on_log(f"[color=#ff3333]Permission check failed: {exc}[/color]")
            return False

    def get_paired_devices(self):
        if not self._platform_is_android:
            # Desktop stub to let the UI work.
            return [
                {"name": "Mock ESP32", "address": "00:00:00:00:00:00"},
            ]
        try:
            self.ensure_permissions()
            autoclass = self.autoclass
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None or not adapter.isEnabled():
                self.on_log("[color=#ff3333]Bluetooth adapter unavailable or disabled.[/color]")
                return []
            devices = adapter.getBondedDevices()
            result = []
            if devices:
                for dev in devices.toArray():
                    result.append({"name": dev.getName(), "address": dev.getAddress()})
            return result
        except Exception as exc:  # pragma: no cover - Android only
            self.on_log(f"[color=#ff3333]Failed to list paired devices: {exc}[/color]")
            return []

    def connect(self, address: str, name: str = ""):
        thread = threading.Thread(target=self._connect_thread, args=(address, name), daemon=True)
        thread.start()

    def _connect_thread(self, address: str, name: str):
        try:
            if not self._platform_is_android:
                time.sleep(0.5)
                self._running = True
                self.on_connected(name or address)
                return

            self.ensure_permissions()
            autoclass = self.autoclass
            cast = self.cast
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            UUID = autoclass("java.util.UUID")

            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None or not adapter.isEnabled():
                self.on_disconnected("Bluetooth adapter unavailable or disabled.")
                return

            device = adapter.getRemoteDevice(address)
            uuid = UUID.fromString(SPP_UUID)
            socket = device.createRfcommSocketToServiceRecord(uuid)
            adapter.cancelDiscovery()
            socket.connect()
            self._socket = socket
            self._input_stream = socket.getInputStream()
            self._output_stream = socket.getOutputStream()
            self._running = True
            self.on_connected(device.getName())
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
        except Exception as exc:
            self.on_disconnected(f"Connection failed: {exc}")

    def _reader_loop(self):
        try:
            buffer = bytearray(256)
            while self._running and self._input_stream is not None:
                count = self._input_stream.read(buffer)
                if count == -1:
                    break
                if count:
                    msg = bytes(buffer[:count]).decode(errors="replace")
                    self.on_message(msg)
        except Exception as exc:
            self.on_log(f"[color=#ff3333]Read error: {exc}[/color]")
        finally:
            self.close()
            self.on_disconnected("Disconnected")

    def send(self, data: str):
        if not self._running:
            raise RuntimeError("Not connected")
        if not self._platform_is_android:
            self.on_log(f"TX (stub): {data}")
            return
        try:
            payload = data.encode("utf-8")
            self._output_stream.write(payload)
            self._output_stream.flush()
            self.on_log(f"TX: {data}")
        except Exception as exc:  # pragma: no cover - Android only
            self.on_disconnected(f"Send failed: {exc}")

    def close(self):
        self._running = False
        try:
            if self._input_stream:
                self._input_stream.close()
            if self._output_stream:
                self._output_stream.close()
            if self._socket:
                self._socket.close()
        except Exception:
            pass
        self._socket = None
        self._input_stream = None
        self._output_stream = None

    @property
    def connected(self) -> bool:
        return self._running


class ShutterApp(MDApp):
    status_text = StringProperty("Status: Disconnected")
    device_text = StringProperty("Device: None")
    total_text = StringProperty("Estimated total: --")
    remaining_text = StringProperty("Time remaining: --")
    progress_label = StringProperty("Idle")
    eta_text = StringProperty("ETA: --")
    log_text = StringProperty("")
    progress_value = NumericProperty(0)
    can_start = BooleanProperty(False)
    can_abort = BooleanProperty(False)
    can_connect = BooleanProperty(False)
    can_disconnect = BooleanProperty(False)
    device_dropdown_text = StringProperty("Select device")
    selected_device_name = StringProperty("")
    selected_device_address = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = LoggerBuffer()
        self.bt_client = BluetoothClient(
            on_connected=self._on_bt_connected,
            on_disconnected=self._on_bt_disconnected,
            on_message=self._on_bt_message,
            on_log=self._append_log,
        )
        Window.clearcolor = (0, 0, 0, 1)
        if platform != "android":
            # Approximate Galaxy A54 aspect (20:9) for desktop preview.
            Window.size = (360, 780)
        self._countdown_event = None
        self._sequence_active = False
        self._sequence_aborted = False
        self._sequence_started_at = 0.0
        self._per_shot_duration = 0.0
        self._total_duration = 0.0
        self._shots = 0
        self._seconds = 0
        self.device_menu: Optional[MDDropdownMenu] = None

    def build(self):
        self.title = "ND40 Astro Shutter"
        self.theme_cls.primary_palette = "Amber"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    # Logging helpers
    def _append_log(self, message: str):
        self.log_text = self.logger.add(message)

    # Bluetooth callbacks
    def _on_bt_connected(self, name: str):
        def _update(dt):
            self.status_text = "Status: Connected"
            self.device_text = f"Device: {name}"
            self.can_start = True
            self.can_disconnect = True
            self.can_connect = False
            self._append_log(f"[color=#33aa33]Connected to {name}[/color]")

        Clock.schedule_once(_update)

    def _on_bt_disconnected(self, reason: str):
        def _update(dt):
            self.status_text = "Status: Disconnected"
            self.device_text = "Device: None"
            self.can_start = False
            self.can_abort = False
            self.can_disconnect = False
            if self._sequence_active:
                self._stop_countdown(reason="Disconnected")
            self._append_log(f"[color=#ff3333]{reason}[/color]")

        Clock.schedule_once(_update)

    def _on_bt_message(self, data: str):
        Clock.schedule_once(lambda dt: self._append_log(f"RX: {data.strip()}"))

    # UI actions
    def open_device_menu(self):
        devices = self.bt_client.get_paired_devices()
        if not devices:
            self._append_log("[color=#ff3333]No paired devices found.[/color]")
            return

        menu_items = []
        for dev in devices:
            name = dev.get("name", "Unknown")
            addr = dev.get("address", "")
            menu_items.append(
                {
                    "text": f"{name} ({addr})",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x=name, y=addr: self._select_device(x, y),
                    "height": dp(48),
                    "text_color": (1, 1, 1, 1),
                }
            )

        if self.device_menu:
            self.device_menu.dismiss()

        self.device_menu = MDDropdownMenu(
            caller=self.root.ids.device_dropdown,
            items=menu_items,
            width_mult=4,
            background_color=(0.12, 0.12, 0.12, 1),
        )
        self.device_menu.open()

    def _select_device(self, name: str, addr: str):
        self.selected_device_name = name
        self.selected_device_address = addr
        self.device_dropdown_text = name
        self.device_text = f"Device: {name}"
        self.can_connect = True
        if self.device_menu:
            self.device_menu.dismiss()

    def connect_selected(self):
        if not self.selected_device_address:
            self._append_log("[color=#ff3333]Select a device first.[/color]")
            return
        self.status_text = "Status: Connecting..."
        self.device_text = f"Device: {self.selected_device_name}"
        self.bt_client.connect(self.selected_device_address, self.selected_device_name)
        self._append_log(f"Connecting to {self.selected_device_name} ({self.selected_device_address})")
        self.can_connect = False

    def disconnect(self):
        if self.bt_client.connected:
            self.bt_client.close()
        self._stop_countdown(reason="Disconnected")
        self.status_text = "Status: Disconnected"
        self.device_text = "Device: None"
        self.can_start = False
        self.can_abort = False
        self.can_disconnect = False

    def start_sequence(self):
        try:
            shots = int(self.root.ids.shots_input.text.strip())
            seconds = int(self.root.ids.seconds_input.text.strip())
        except ValueError:
            self._append_log("[color=#ff3333]Enter valid integers for shots and seconds.[/color]")
            return

        if shots <= 0 or seconds <= 0:
            self._append_log("[color=#ff3333]Shots and seconds must be > 0.[/color]")
            return
        if not self.bt_client.connected:
            self._append_log("[color=#ff3333]Connect to a device first.[/color]")
            return
        if self._sequence_active:
            self._append_log("[color=#ff3333]Sequence already running.[/color]")
            return

        command = f"{shots}, {seconds}"
        try:
            self.bt_client.send(command)
        except Exception as exc:
            self._append_log(f"[color=#ff3333]Send failed: {exc}[/color]")
            return

        # Timing model: per-shot ~= seconds + 2.6 (0.3 + exposure + 0.3 + 2.0 pause)
        per_shot = seconds + 2.6
        total = shots * per_shot
        self._shots = shots
        self._seconds = seconds
        self._per_shot_duration = per_shot
        self._total_duration = total
        self._sequence_started_at = time.time()
        self._sequence_active = True
        self._sequence_aborted = False
        self.can_abort = True
        self.can_start = False

        self.total_text = f"Estimated total: {format_seconds(total)}"
        self._append_log(f"Started sequence '{command}' (est. {format_seconds(total)})")

        self._countdown_event = Clock.schedule_interval(self._update_countdown, 0.5)

    def _update_countdown(self, dt):
        elapsed = time.time() - self._sequence_started_at
        remaining = max(0.0, self._total_duration - elapsed)
        progress = 1.0 - (remaining / self._total_duration) if self._total_duration else 0.0
        current_shot = min(self._shots, int(elapsed // self._per_shot_duration) + 1)
        self.remaining_text = f"Time remaining: {format_seconds(remaining)}"
        self.progress_label = f"Shot {current_shot} of {self._shots}"
        self.progress_value = int(progress * 100)
        finish_eta = time.strftime("%H:%M:%S", time.localtime(time.time() + remaining))
        self.eta_text = f"ETA: {finish_eta}"
        if remaining <= 0.0:
            self._stop_countdown(reason="Sequence complete")
            self._append_log("[color=#33aa33]Sequence finished (local estimate).[/color]")

    def abort_sequence(self):
        if not self.bt_client.connected:
            self._append_log("[color=#ff3333]Not connected.[/color]")
            return
        try:
            self.bt_client.send("abort")
        except Exception as exc:
            self._append_log(f"[color=#ff3333]Abort send failed: {exc}[/color]")
        self._append_log("[color=#cc5500]Abort sent; stopping local countdown.[/color]")
        self._stop_countdown(reason="Aborted")

    def _stop_countdown(self, reason: str):
        if self._countdown_event:
            self._countdown_event.cancel()
            self._countdown_event = None
        self._sequence_active = False
        self._sequence_aborted = reason.lower().startswith("abort")
        self.progress_label = reason
        self.remaining_text = "Time remaining: --"
        self.eta_text = "ETA: --"
        self.progress_value = 0
        self.can_abort = False
        self.can_start = self.bt_client.connected
        self.can_connect = bool(self.selected_device_address) and not self.bt_client.connected
        self.can_disconnect = self.bt_client.connected

    def on_stop(self):
        self.bt_client.close()


if __name__ == "__main__":
    ShutterApp().run()
