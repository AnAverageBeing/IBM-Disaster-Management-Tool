#!/usr/bin/env bash
set -euo pipefail

IBM_DMT_VERSION="1.0.0"
REPO="AnAverageBeing/IBM-Disaster-Management-Tool"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.ibm-dmt}"
VENV_DIR="$INSTALL_DIR/venv"

GITHUB_TOKEN="${GITHUB_TOKEN:-}"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}IBM Disaster Management Tool v${IBM_DMT_VERSION}${NC}"
echo -e "${BOLD}Installer${NC}"
echo ""

detect_package_manager() {
    if command -v apt &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v zypper &>/dev/null; then
        echo "zypper"
    elif command -v brew &>/dev/null; then
        echo "brew"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    local pm
    pm=$(detect_package_manager)
    echo -e "${YELLOW}Installing system dependencies...${NC}"

    case "$pm" in
        apt)
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv git curl zstd xz-utils p7zip-full || true
            ;;
        dnf|yum)
            sudo "$pm" install -y python3 python3-pip python3-virtualenv git curl zstd xz p7zip || true
            ;;
        pacman)
            sudo pacman -Sy --noconfirm python python-pip python-virtualenv git curl zstd xz p7zip || true
            ;;
        brew)
            brew install python3 git curl zstd xz p7zip || true
            ;;
        *)
            echo -e "${YELLOW}Unsupported package manager. Install python3, pip, git, curl manually.${NC}"
            ;;
    esac
}

setup_venv() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    mkdir -p "$INSTALL_DIR"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
}

install_python_deps() {
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install pyqt6 pyzstd cryptography requests apscheduler pygithub psutil \
                pymongo redis mysql-connector-python psycopg2-binary pymssql \
                cx-oracle pydantic platformdirs
}

install_package() {
    local clone_dir="$INSTALL_DIR/repo"
    if [ -d "$clone_dir" ]; then
        source "$VENV_DIR/bin/activate"
        pip install -e "$clone_dir"
    fi
}

clone_repo() {
    local clone_dir="$INSTALL_DIR/repo"
    if [ -d "$clone_dir" ]; then
        echo -e "${YELLOW}Updating existing installation...${NC}"
        cd "$clone_dir"
        git pull
    else
        echo -e "${YELLOW}Cloning repository...${NC}"
        if [ -n "$GITHUB_TOKEN" ]; then
            git clone "https://${GITHUB_TOKEN}@github.com/${REPO}.git" "$clone_dir"
        else
            git clone "https://github.com/${REPO}.git" "$clone_dir"
        fi
    fi
}

create_symlink() {
    local launcher="$INSTALL_DIR/ibm-dmt"
    cat > "$launcher" << LAUNCHER
#!/usr/bin/env bash
export IBM_DMT_HOME="$INSTALL_DIR"
source "\$IBM_DMT_HOME/venv/bin/activate"
cd "\$IBM_DMT_HOME/repo"
python3 -m ibm_dmt.main "\$@"
LAUNCHER
    chmod +x "$launcher"

    local bin_dir="$HOME/.local/bin"
    mkdir -p "$bin_dir"
    ln -sf "$launcher" "$bin_dir/ibm-dmt"

    echo -e "${GREEN}Created launcher: $bin_dir/ibm-dmt${NC}"
    echo -e "${YELLOW}Add to PATH if needed: export PATH=\"\$PATH:$bin_dir\"${NC}"
}

create_desktop_entry() {
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir"
    cat > "$desktop_dir/ibm-dmt.desktop" << DESKTOP
[Desktop Entry]
Name=IBM Disaster Management Tool
Comment=Disaster Recovery & Business Continuity Platform
Exec=$INSTALL_DIR/ibm-dmt
Icon=$INSTALL_DIR/repo/icon.png
Terminal=false
Type=Application
Categories=Utility;System;
DESKTOP
    chmod +x "$desktop_dir/ibm-dmt.desktop"
    echo -e "${GREEN}Created desktop entry${NC}"
}

create_systemd_service() {
    local service_path="$HOME/.config/systemd/user/ibm-dmt.service"
    mkdir -p "$(dirname "$service_path")"
    cat > "$service_path" << SERVICEEOF
[Unit]
Description=IBM Disaster Management Tool Background Service
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/ibm-dmt --headless --config $INSTALL_DIR/config.json
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
SERVICEEOF

    systemctl --user daemon-reload
    echo -e "${GREEN}Created systemd user service${NC}"
}

launch_gui() {
    echo -e "${GREEN}Launching IBM-DMT GUI...${NC}"
    source "$VENV_DIR/bin/activate"
    python3 -m ibm_dmt.main &
}

run_post_install() {
    echo ""
    echo -e "${GREEN}${BOLD}Installation Complete!${NC}"
    echo ""
    echo -e "  Run:  ${BOLD}ibm-dmt${NC}"
    echo -e "  Or:   ${BOLD}ibm-dmt --headless --config config.json${NC}"
    echo ""
    echo -e "  Sessions directory: ${BOLD}$INSTALL_DIR/sessions${NC}"
    echo -e "  Config directory:   ${BOLD}$HOME/.config/ibm-dmt${NC}"
    echo -e "  Make sure $HOME/.local/bin is in your PATH."
    echo ""
}

main() {
    echo -e "${BOLD}IBM-DMT Installer${NC}"
    echo "========================"
    echo ""

    install_system_deps
    setup_venv
    install_python_deps
    clone_repo
    install_package
    create_symlink

    if [[ "$*" != *"--no-desktop"* ]]; then
        create_desktop_entry
    fi

    if [[ "$*" == *"--service"* ]]; then
        create_systemd_service
    fi

    run_post_install

    if [[ "$*" != *"--no-launch"* ]] && [[ "${IBM_DMT_NO_LAUNCH:-}" != "1" ]]; then
        launch_gui
    fi
}

main "$@"
