#!/usr/bin/env bash
set -euo pipefail

# Defaults
PROJECT_ROOT="$HOME/Projects/openbmc-11.03"
MACHINE="nvidia-vru"
QEMU_MACHINE="ast2700-evb"
FMC_MODEL="w25q512jv"

BUILD_DIR=""
NATIVE_ROOT=""
QEMU=""
BIOS_DIR=""
IMAGE=""

usage() {
    cat <<'EOF'
Usage: start_qemu.sh [options]

Options:
  --project-root PATH   Project directory
                        Default: $HOME/Projects/openbmc-11.03
  --machine NAME        Yocto machine (default: nvidia-vru)
  --build-dir PATH      Build directory (default: PROJECT_ROOT/build/MACHINE)
  --native-root PATH    Native sysroot for QEMU and its shared libraries
  --qemu PATH           QEMU executable
  --bios-dir PATH       Directory containing ast27x0_bootrom.bin
  --image PATH          Flash image (.static.mtd)
  --qemu-machine NAME   QEMU board (default: ast2700-evb)
  --fmc-model NAME      Flash model (default: w25q512jv)
  -h, --help            Show help

Examples:
  bash start_qemu.sh
  bash start_qemu.sh --image /path/to/test.static.mtd
  bash start_qemu.sh --project-root /path/to/openbmc
  bash start_qemu.sh --build-dir /path/to/build/nvidia-vru

Network forwarding:
  SSH:   127.0.0.1:2222 -> guest:22
  HTTPS: 127.0.0.1:8443 -> guest:443
  HTTP:  127.0.0.1:8080 -> guest:80
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --project-root|--machine|--build-dir|--native-root|\
        --qemu|--bios-dir|--image|--qemu-machine|--fmc-model)
            if (($# < 2)); then
                die "Missing value for $1"
            fi
            if [[ -z "$2" || "$2" == --* ]]; then
                die "Missing value for $1"
            fi

            case "$1" in
                --project-root) PROJECT_ROOT="$2" ;;
                --machine) MACHINE="$2" ;;
                --build-dir) BUILD_DIR="$2" ;;
                --native-root) NATIVE_ROOT="$2" ;;
                --qemu) QEMU="$2" ;;
                --bios-dir) BIOS_DIR="$2" ;;
                --image) IMAGE="$2" ;;
                --qemu-machine) QEMU_MACHINE="$2" ;;
                --fmc-model) FMC_MODEL="$2" ;;
            esac
            shift 2
            ;;
        *)
            die "Unknown option: $1 (use --help)"
            ;;
    esac
done

# Derive paths after parsing options.
BUILD_DIR="${BUILD_DIR:-$PROJECT_ROOT/build/$MACHINE}"
SDK_TMP="$BUILD_DIR/tmp"

# Default work-directory naming for this SDK.
MACHINE_WORK="${MACHINE//-/_}"
NATIVE_ROOT="${NATIVE_ROOT:-$SDK_TMP/work/${MACHINE_WORK}-openbmc-linux/obmc-phosphor-image/1.0/recipe-sysroot-native}"

QEMU="${QEMU:-$NATIVE_ROOT/usr/bin/qemu-system-aarch64}"
BIOS_DIR="${BIOS_DIR:-$SDK_TMP/sysroots-components/x86_64/qemu-system-native/usr/share/qemu}"
IMAGE="${IMAGE:-$SDK_TMP/deploy/images/$MACHINE/obmc-phosphor-image-$MACHINE.static.mtd}"
BOOTROM="$BIOS_DIR/ast27x0_bootrom.bin"

# Shared libraries required by the SDK-built native QEMU.
export LD_LIBRARY_PATH="$NATIVE_ROOT/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "Checking environment..."

[[ -x "$QEMU" ]] ||
    die "QEMU not found or not executable: $QEMU"

[[ -f "$IMAGE" && -r "$IMAGE" && -s "$IMAGE" ]] ||
    die "Image missing, unreadable or empty: $IMAGE"

[[ -f "$BOOTROM" && -r "$BOOTROM" && -s "$BOOTROM" ]] ||
    die "Bootrom missing, unreadable or empty: $BOOTROM"

echo
echo "[OK] QEMU:"
ls -lh "$QEMU"

echo
echo "[OK] Image:"
ls -lh "$IMAGE"
echo "Resolved image: $(readlink -f -- "$IMAGE")"

echo
echo "[OK] Bootrom:"
ls -lh "$BOOTROM"

echo
"$QEMU" --version ||
    die "QEMU cannot run; check --native-root and shared libraries"

echo
echo "Checking QEMU machine support: $QEMU_MACHINE"
if ! "$QEMU" -machine help |
    awk -v wanted="$QEMU_MACHINE" '
        $1 == wanted { found = 1 }
        END { exit !found }
    '; then
    die "QEMU machine unavailable: $QEMU_MACHINE"
fi

echo
echo "Starting OpenBMC QEMU..."
echo "Yocto machine: $MACHINE"
echo "QEMU machine:  $QEMU_MACHINE"
echo "Flash model:   $FMC_MODEL"
echo
echo "NVIDIA eth0 uses MAC3; port forwarding is attached to MAC3."
echo "SSH:   ssh -p 2222 root@127.0.0.1"
echo "HTTPS: https://127.0.0.1:8443"
echo "HTTP:  http://127.0.0.1:8080"
echo "Exit:  Ctrl+A, then X"
echo

exec "$QEMU" \
    -L "$BIOS_DIR" \
    -bios "$BOOTROM" \
    -machine "$QEMU_MACHINE,fmc-model=$FMC_MODEL" \
    -m 2G \
    -nographic \
    -drive "file=$IMAGE,if=mtd,format=raw" \
    -serial mon:stdio \
    -serial null \
    -netdev user,id=net0 \
    -netdev user,id=net1 \
    -netdev user,id=net2,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:8443-:443,hostfwd=tcp:127.0.0.1:8080-:80 \
    -net nic,netdev=net0 \
    -net nic,netdev=net1 \
    -net nic,netdev=net2
