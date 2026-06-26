#!/usr/bin/env bash
set -uo pipefail

IBM_DMT_VERSION="1.0.0"
REPO="AnAverageBeing/IBM-Disaster-Management-Tool"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.ibm-dmt}"
VENV_DIR="$INSTALL_DIR/venv"
CLONE_DIR="$INSTALL_DIR/repo"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()  { echo -e "${GREEN}${BOLD}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC}  $1"; }
step()  { echo; echo -e "${BOLD}── $1 ──${NC}"; }

detect_package_manager() {
    for pm in apt dnf yum pacman zypper brew; do
        command -v "$pm" &>/dev/null && echo "$pm" && return
    done
    echo "unknown"
}

install_system_deps() {
    step "System dependencies"
    local pm
    pm=$(detect_package_manager)
    case "$pm" in
        apt)
            sudo apt update -qq 2>/dev/null
            for pkg in python3 python3-pip python3-venv git curl zstd xz-utils \
                       p7zip-full p7zip libxcb-cursor0; do
                dpkg -s "$pkg" >/dev/null 2>&1 && continue
                sudo apt install -y -qq "$pkg" 2>/dev/null && info "  $pkg installed" || warn "  $pkg failed"
            done
            ;;
        dnf|yum)
            sudo "$pm" install -y \
                python3 python3-pip python3-virtualenv git curl zstd xz \
                p7zip p7zip-plugins xcb-util-cursor >/dev/null 2>&1 || true
            ;;
        pacman)
            sudo pacman -Sy --noconfirm \
                python python-pip python-virtualenv git curl zstd xz \
                p7zip xcb-util-cursor >/dev/null 2>&1 || true
            ;;
        brew)
            brew install python3 git curl zstd xz p7zip >/dev/null 2>&1 || true
            ;;
        *)
            warn "Unknown package manager. Ensure python3, pip, git, curl are installed."
            ;;
    esac
    info "System dependencies OK"
}

setup_venv() {
    step "Python virtual environment"
    mkdir -p "$INSTALL_DIR"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --quiet --upgrade pip setuptools wheel >/dev/null 2>&1
    info "Virtual environment ready at $VENV_DIR"
}

install_python_deps() {
    step "Python packages (core)"
    source "$VENV_DIR/bin/activate"

    CORE_PKGS=(
        pyqt6 pyzstd cryptography requests apscheduler pygithub psutil
        pydantic platformdirs
    )
    pip install --quiet "${CORE_PKGS[@]}" 2>&1 | tail -1
    info "Core packages installed"

    step "Python packages (database drivers)"
    DB_PKGS=(
        pymongo redis mysql-connector-python psycopg2-binary pymssql
    )
    for pkg in "${DB_PKGS[@]}"; do
        pip install --quiet "$pkg" 2>/dev/null && info "  $pkg OK" || warn "  $pkg skipped (not available on this system)"
    done

    step "Python packages (optional)"
    if python3 -c "import ctypes; ctypes.CDLL('libclntsh.so')" 2>/dev/null ||
       python3 -c "import ctypes; ctypes.CDLL('libclntsh.dylib')" 2>/dev/null ||
       [ -n "${ORACLE_HOME:-}" ]; then
        pip install --quiet cx-oracle 2>/dev/null && info "  cx-oracle OK" || warn "  cx-oracle skipped"
    else
        warn "  cx-oracle skipped (Oracle Instant Client not detected)"
    fi
}

clone_repo() {
    step "Cloning repository"
    if [ -d "$CLONE_DIR" ]; then
        info "Updating existing installation..."
        git -C "$CLONE_DIR" pull --ff-only >/dev/null 2>&1 && info "Updated" || warn "Update failed, using existing"
    else
        local url="https://github.com/${REPO}.git"
        [ -n "$GITHUB_TOKEN" ] && url="https://${GITHUB_TOKEN}@github.com/${REPO}.git"
        git clone --depth 1 "$url" "$CLONE_DIR" >/dev/null 2>&1 && info "Cloned" || {
            err "Clone failed"; exit 1
        }
    fi
    source "$VENV_DIR/bin/activate"
    pip install --quiet -e "$CLONE_DIR" >/dev/null 2>&1 || warn "Editable install skipped"
}

create_launcher() {
    step "Launcher"
    local launcher="$INSTALL_DIR/ibm-dmt"
    cat > "$launcher" << LAUNCHER
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
cd "$CLONE_DIR" 2>/dev/null || true

# Use xcb if a display is available, offscreen otherwise
if [ -z "\${DISPLAY:-}" ] && [ -z "\${WAYLAND_DISPLAY:-}" ]; then
    export QT_QPA_PLATFORM=offscreen
fi

python3 -m ibm_dmt.main "\$@"
LAUNCHER
    chmod +x "$launcher"

    # Install to PATH — use /usr/local/bin for root, ~/.local/bin otherwise
    if [ "$(id -u)" -eq 0 ]; then
        local bin_dir="/usr/local/bin"
    else
        local bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
    fi
    mkdir -p "$bin_dir"
    ln -sf "$launcher" "$bin_dir/ibm-dmt"
    info "Launcher: $bin_dir/ibm-dmt"
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "$bin_dir"; then
        warn "$bin_dir is not in PATH. Add it: export PATH=\"\$PATH:$bin_dir\""
    fi
}

create_desktop_entry() {
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir"
    cat > "$desktop_dir/ibm-dmt.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=IBM Disaster Management Tool
Comment=Disaster Recovery & Business Continuity
Exec=$INSTALL_DIR/ibm-dmt
Terminal=false
Categories=Utility;System;
DESKTOP
    chmod +x "$desktop_dir/ibm-dmt.desktop"
    info "Desktop entry created"
}

create_systemd_service() {
    local service_path="$HOME/.config/systemd/user/ibm-dmt.service"
    mkdir -p "$(dirname "$service_path")"
    cat > "$service_path" << SERVICE
[Unit]
Description=IBM Disaster Management Tool
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/ibm-dmt --headless
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
SERVICE
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    info "Systemd service created"
}

launch_gui() {
    echo
    info "Launching IBM-DMT GUI..."

    source "$VENV_DIR/bin/activate"
    cd "$CLONE_DIR" 2>/dev/null || true

    # Use xcb if a display is available, offscreen otherwise
    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        warn "No display detected — using offscreen mode (run with --headless for CLI)"
        export QT_QPA_PLATFORM=offscreen
    fi

    python3 -m ibm_dmt.main &
    sleep 2
}

main() {
    echo -e "${BOLD}IBM Disaster Management Tool v${IBM_DMT_VERSION}${NC}"
    echo -e "${BOLD}Installer${NC}"

    install_system_deps
    setup_venv
    install_python_deps
    clone_repo
    create_launcher

    if [[ "$*" != *"--no-desktop"* ]]; then
        create_desktop_entry
    fi
    if [[ "$*" == *"--service"* ]]; then
        create_systemd_service
    fi

    echo
    echo -e "${GREEN}${BOLD}Installation complete${NC}"
    echo -e "  Run:  ${BOLD}ibm-dmt${NC}"
    echo -e "  Config: ${BOLD}\$HOME/.config/ibm-dmt${NC}"

    if [[ "$*" != *"--no-launch"* ]]; then
        launch_gui
    fi
}

main "$@"
