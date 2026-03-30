# ND40 Astro Shutter

KivyMD Android app to control an ESP32 running Classic Bluetooth SPP firmware. It sends exposure sequences in the exact format the firmware expects, can abort an active run, and shows a local estimate of time remaining.

## Features
- Connects over Classic Bluetooth SPP (UUID `00001101-0000-1000-8000-00805F9B34FB`).
- Paired-device picker (no reflashing or firmware changes required).
- Start command: `shots, seconds` (sent exactly as entered, no newline).
- Abort command: `abort` (sent as-is).
- Local countdown, ETA, and per-shot progress estimate using the timing model: per-shot ≈ exposure seconds + 2.6s (0.3 start pulse + exposure + 0.3 end pulse + 2.0s pause).
- Scrollable log of connection events, commands, and any bytes received from the ESP32.
- Runs Bluetooth I/O on a background thread to keep the UI responsive.
- Graceful handling of disconnects (stops local timers, updates status, allows reconnect).

## Pairing (do this once)
1. On your Android device, open system Bluetooth settings.
2. Pair with the ESP32 device (enter PIN if needed). Ensure it shows as “Paired”.
3. Open the app; use the **Connect** button to pick the paired device.

## Permissions
- Android 12+: `BLUETOOTH_CONNECT` (and `BLUETOOTH_SCAN` for device listing). You will be prompted at runtime—approve to proceed.
- Android <12: `BLUETOOTH`, `BLUETOOTH_ADMIN` (and location if scanning is needed by the OS for Bluetooth discovery). Approve any prompts that appear.
- The app only lists already paired devices; it does not actively scan.

## Usage
1. Tap **Connect** and choose the paired ESP32 from the list.
2. Enter integers for **Shots** and **Seconds**.
3. Tap **Start** to send the command (e.g., `3, 20`). The app starts a local countdown based on the timing model.
4. The log shows `TX: 3, 20` and any incoming data (`RX: ...`).
5. To stop early, tap **Abort**. The app immediately sends `abort`, stops its countdown, and marks the state as aborted. The Bluetooth link stays up unless it fails.

### Timing model
- Per shot estimate: exposure seconds + 2.6s (0.3s start pulse + exposure + 0.3s end pulse + 2.0s pause).
- Total estimate: shots × (exposure seconds + 2.6s).
- The countdown is local; the firmware is not queried for progress.

## Build with Buildozer (Android APK)
> Building is easiest on Linux or WSL/Ubuntu. On Windows, use WSL.

### Windows one-time setup (admin)
If WSL2 fails with virtualization errors, run PowerShell **as Administrator** and execute:

```powershell
./scripts/enable-wsl-build-prereqs.ps1
```

Then reboot, install an Ubuntu distro (`wsl --install -d Ubuntu`), and continue with the Linux/WSL build steps below.

1. Install system deps (example for Ubuntu/WSL):
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv git build-essential \
       openjdk-11-jdk unzip zlib1g-dev libncurses5-dev libffi-dev libssl-dev
   pip install --user buildozer
   ```
2. In the project folder, create/activate a venv (recommended) and install Buildozer if not already installed:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install buildozer
   ```
3. Build the APK:
   ```bash
   buildozer -v android debug
   ```
   The first run downloads the Android SDK/NDK; it can take several minutes.
4. Deploy/run on a USB-connected device with developer mode enabled:
   ```bash
   buildozer android deploy run logcat
   ```

## Cloud build (no local Android toolchain)
This repo includes GitHub Actions workflow: `.github/workflows/android-apk.yml`.

1. Push this project to GitHub.
2. Open **Actions** tab → **Build Android APK**.
3. Click **Run workflow**.
4. Download artifact `nd40-astro-shutter-debug-apk` from the finished run.

This is the fastest path if local virtualization/WSL is unavailable.

## Notes and troubleshooting
- Make sure Bluetooth is turned on before connecting. If the paired list is empty, confirm the device is paired in Android settings.
- The app does not append a newline to commands. If your ESP32 requires a terminator, add it in firmware; the app keeps the raw format to match the provided protocol.
- If permissions were denied, reopen the app or enable them from system settings and retry.
- Connection drops stop the local timer and reset UI state; simply reconnect and start again.
