import os
import sys
import lief

# Ensure the root ArmBridge directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.qiling_engine import ArmBridgeEngine

def main():
    if len(sys.argv) < 2:
        print("Usage: python core/main.py <path_to_macho_binary>")
        sys.exit(1)

    target_binary = sys.argv[1]

    if not os.path.exists(target_binary):
        print(f"[-] Error: Cannot find file {target_binary}")
        sys.exit(1)

    print(f"[*] Analyzing header for {target_binary}...")
    binary = lief.parse(target_binary)

    if not binary or not isinstance(binary, lief.MachO.Binary):
        print("[-] Error: Target is not a valid macOS Mach-O binary.")
        sys.exit(1)

    # Bulletproof check: Compare the raw integer value instead of volatile LIEF enums
    # 0x0100000c is the official Apple Silicon (ARM64) magic value
    if int(binary.header.cpu_type) != 0x0100000c:
        print(f"[-] Error: Target is not ARM64. Detected CPU Type: {binary.header.cpu_type}")
        sys.exit(1)

    print("[+] Binary architecture verified: macOS ARM64 (Apple Silicon)")

    # Instantiate and start the execution engine
    engine = ArmBridgeEngine(binary_path=target_binary)
    engine.initialize()
    engine.run()

if __name__ == "__main__":
    main()