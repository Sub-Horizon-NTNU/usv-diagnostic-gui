#!/usr/bin/env bash
# install.sh — USV Diagnostic GUI install script
# Supports: native ROS2 Humble, or ROS2 Humble inside a Distrobox container
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
info()    { echo -e "\e[1;34m[INFO]\e[0m  $*"; }
success() { echo -e "\e[1;32m[OK]\e[0m    $*"; }
warn()    { echo -e "\e[1;33m[WARN]\e[0m  $*"; }
die()     { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }

# ─────────────────────────────────────────────
# Detect environment: native or distrobox
# ─────────────────────────────────────────────
IN_DISTROBOX=false
if [ -f /run/.containerenv ] || [ -n "$CONTAINER_ID" ]; then
    IN_DISTROBOX=true
fi

if $IN_DISTROBOX; then
    info "Detected Distrobox container environment."
else
    info "Detected native (host) environment."
fi

# ─────────────────────────────────────────────
# Check ROS2 Humble is sourced / available
# ─────────────────────────────────────────────
if [ -z "$ROS_DISTRO" ]; then
    # Try sourcing the default install location
    if [ -f /opt/ros/humble/setup.bash ]; then
        # shellcheck source=/dev/null
        source /opt/ros/humble/setup.bash
        info "Sourced /opt/ros/humble/setup.bash"
    else
        die "ROS2 Humble not found. Please install ROS2 Humble and make sure /opt/ros/humble/setup.bash exists, then re-run this script."
    fi
fi

if [ "$ROS_DISTRO" != "humble" ]; then
    die "This package requires ROS2 Humble, but \$ROS_DISTRO='$ROS_DISTRO' is sourced. Please source ROS2 Humble instead."
fi

success "ROS2 Humble is available (\$ROS_DISTRO=$ROS_DISTRO)."

# ─────────────────────────────────────────────
# System dependencies
# ─────────────────────────────────────────────
info "Installing system dependencies..."

SYSTEM_PACKAGES=(
    python3-pip
    python3-colcon-common-extensions
    python3-rosdep
    python3-pyqt5
    python3-pyqt5.qtwebengine
    python3-yaml
    python3-opencv
)

if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y "${SYSTEM_PACKAGES[@]}"
    success "System packages installed."
else
    warn "apt-get not found — skipping system package install. Make sure the following are installed manually:"
    for pkg in "${SYSTEM_PACKAGES[@]}"; do
        echo "  - $pkg"
    done
fi

# ─────────────────────────────────────────────
# rosdep init / update (skip if already done)
# ─────────────────────────────────────────────
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    info "Initializing rosdep..."
    sudo rosdep init
fi
info "Updating rosdep..."
rosdep update

# ─────────────────────────────────────────────
# Install rosdep dependencies for the workspace
# ─────────────────────────────────────────────
info "Installing ROS2 package dependencies via rosdep..."
cd "$SCRIPT_DIR"
rosdep install --from-paths src --ignore-src -r -y
success "ROS2 dependencies installed."

# ─────────────────────────────────────────────
# Build the workspace
# ─────────────────────────────────────────────
info "Building workspace with colcon..."
cd "$SCRIPT_DIR"
colcon build --symlink-install
success "Build complete."

# ─────────────────────────────────────────────
# Add workspace source to shell rc (optional)
# ─────────────────────────────────────────────
SETUP_LINE="source \"$SCRIPT_DIR/install/setup.bash\""

add_to_rc() {
    local RC_FILE="$1"
    if [ -f "$RC_FILE" ]; then
        if ! grep -qF "$SCRIPT_DIR/install/setup.bash" "$RC_FILE"; then
            echo "" >> "$RC_FILE"
            echo "# USV Diagnostic GUI workspace" >> "$RC_FILE"
            echo "$SETUP_LINE" >> "$RC_FILE"
            success "Added workspace source to $RC_FILE"
        else
            info "Workspace already sourced in $RC_FILE — skipping."
        fi
    fi
}

if [ -f "$HOME/.bashrc" ]; then
    add_to_rc "$HOME/.bashrc"
fi
if [ -f "$HOME/.zshrc" ]; then
    add_to_rc "$HOME/.zshrc"
fi

# ─────────────────────────────────────────────
# Distrobox-specific instructions
# ─────────────────────────────────────────────
if $IN_DISTROBOX; then
    echo ""
    warn "You are inside a Distrobox container."
    warn "To launch the GUI from the host (with display access), run:"
    echo ""
    echo "    distrobox enter <your-container-name> -- bash -c \\"
    echo "      'source /opt/ros/humble/setup.bash && \\"
    echo "       source $SCRIPT_DIR/install/setup.bash && \\"
    echo "       ros2 launch usv_diagnostic_gui gui_launch.py'"
    echo ""
    warn "Make sure DISPLAY or WAYLAND_DISPLAY is set correctly inside the container."
    warn "Distrobox usually handles this automatically."
fi

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo ""
success "Installation complete!"
echo ""
echo "To launch the GUI:"
echo ""
echo "  1. Source the workspace (if you haven't already):"
echo "       source $SCRIPT_DIR/install/setup.bash"
echo ""
echo "  2. Launch:"
echo "       ros2 launch usv_diagnostic_gui gui_launch.py"
echo ""
echo "Optional launch arguments:"
echo "  septentrio_host:=<IP>   (default: 192.168.2.6)"
echo "  pi_ip:=<IP>             (default: 192.168.2.5)"
echo "  mikrotik_user:=<user>   (default: admin)"
echo "  mikrotik_pass:=<pass>   (default: admin)"
