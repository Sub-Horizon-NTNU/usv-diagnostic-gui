# USV Diagnostic GUI

A ROS2 GUI for monitoring the Selene USV. Shows live sensor data, camera feed, GPS map, and lets you run commands on the boat.

## Features

- **Heartbeat indicators** — shows which onboard devices are reachable on the network
- **Sensor displays** — live voltage and current for thrusters and electronics
- **Map** — GPS track with heading and camera field of view
- **Camera stream** — live video from the observation camera, with pan servo control
- **Topic echo** — inspect any ROS2 topic in real time
- **Command buttons** — run terminal commands with live output
- **GPS/RTK status** — fix type, NTRIP status, signal strength, and accuracy
- **Network stats** — MikroTik router bandwidth and signal strength

## Requirements

- Ubuntu 22.04 (native or inside a Distrobox container)
- ROS2 Humble
- Python 3.10+
- A display (X11 or Wayland)

## Installation

### Option A — Native ROS2 Humble

1. Clone the repo:
   ```bash
   git clone git@github.com:Sub-Horizon-NTNU/usv-diagnostic-gui.git
   cd usv-diagnostic-gui
   ```

2. Source ROS2 Humble if it's not already in your `.bashrc`:
   ```bash
   source /opt/ros/humble/setup.bash
   ```

3. Run the install script:
   ```bash
   ./install.sh
   ```

   This will:
   - Install required system packages
   - Install ROS2 dependencies via `rosdep`
   - Build the workspace with `colcon`
   - Add the workspace to your `.bashrc` / `.zshrc`

---

### Option B — ROS2 Humble inside Distrobox

Use this if your host OS doesn't run Ubuntu 22.04 (e.g. Fedora Silverblue, Arch, etc.). Distrobox runs an Ubuntu container with full access to your display and home folder.

#### 1. Create the container

```bash
distrobox create --name ros2-humble --image ubuntu:22.04
distrobox enter ros2-humble
```

#### 2. Install ROS2 Humble inside the container

```bash
sudo apt update && sudo apt install -y curl gnupg lsb-release

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list

sudo apt update
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions python3-rosdep
```

Add to your container's `.bashrc`:
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

#### 3. Clone and install

Clone into your home directory so it's accessible from inside the container (Distrobox mounts your home folder automatically).

```bash
# On the host
git clone git@github.com:Sub-Horizon-NTNU/usv-diagnostic-gui.git

# Inside the container
distrobox enter ros2-humble
cd ~/usv-diagnostic-gui
./install.sh
```
---

## Usage

### Build and Launch the GUI

```bash
colcon build
source install/setup.bash  # skip if already in .bashrc
ros2 launch usv_diagnostic_gui gui_launch.py
```

### Launch arguments

| Argument | Default | Description |
|---|---|---|
| `septentrio_host` | `192.168.2.6` | Septentrio GPS receiver IP |
| `septentrio_port` | `29001` | Septentrio NMEA port |
| `pi_ip` | `192.168.2.5` | Raspberry Pi IP (camera & servo) |
| `pi_udp_port` | `5600` | Video stream port |
| `pi_servo_port` | `5601` | Servo control port |
| `mikrotik_user` | `admin` | MikroTik router username |
| `mikrotik_pass` | `admin` | MikroTik router password |

Example:
```bash
ros2 launch usv_diagnostic_gui gui_launch.py \
  septentrio_host:=192.168.2.6 \
  pi_ip:=192.168.2.5 \
  mikrotik_user:=admin \
  mikrotik_pass:=yourpassword
```

---

## Network Layout

Default IPs (can be changed via launch arguments or `config/config.yaml`):

| Device | Default IP |
|---|---|
| Jetson Orin NX | 192.168.2.2 |
| Base Station | 192.168.2.3 |
| WiFi Receiver (boat) | 192.168.2.4 |
| Raspberry Pi | 192.168.2.5 |
| GPS Module (Septentrio) | 192.168.2.6 |

---

## ROS2 Nodes

### On the PC (ground station) — `usv_diagnostic_gui`

| Node | What it does |
|---|---|
| `usv_diagnostic_gui` | The main GUI window |
| `usv_external_pinger` | Pings onboard devices and publishes online/offline status |
| `usv_pi_interface` | Receives the RTP video stream from the Pi and forwards servo commands |
| `septentrio_nmea_parser` | Connects to the Septentrio GPS over TCP and publishes fix type, signal, and accuracy |
| `mikrotik_monitor` | Reads bandwidth and signal strength from the MikroTik router |

### On the Jetson (USV) — `usv_gui_interface`

| Node | What it does |
|---|---|
| `usv_arduino_interface` | Reads voltage and current from two Arduinos over serial and publishes the values |
| `usv_internal_pinger` | Pings internal network targets (e.g. checks Jetson internet access) |
| `usv_command_node` | Action server that receives commands from the GUI, runs them in a shell, and streams output back as feedback. Starts automatically on boot. |

---

## Configuration

The UI layout is controlled by [src/usv_diagnostic_gui/config/config.yaml](src/usv_diagnostic_gui/config/config.yaml). You can add or remove heartbeat indicators, sensor displays, and buttons there without touching any code.

---

## Troubleshooting

**`No module named 'PyQt5'`**
```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine
```

**`colcon: command not found`**
```bash
sudo apt install python3-colcon-common-extensions
```

**Map is blank**
The map needs an internet connection to load tiles.

**Camera shows "NO SIGNAL"**
Check that the Raspberry Pi is online and the RTP stream is running on port 5600.

**Pinger always red inside Distrobox**
Check that `distrobox-host-exec` is available:
```bash
which distrobox-host-exec
```
If it's missing, update Distrobox on the host and re-enter the container.
