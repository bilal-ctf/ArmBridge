import os
import sys
import traceback
import lief
from qiling import Qiling
from qiling.const import QL_VERBOSE, QL_ARCH, QL_OS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dyld_hook import setup_dyld_hooks
from subsystems.vfs_sandbox import VFSSandbox
from subsystems.posix_syscalls import setup_posix_syscalls
from services.gcd_threadpool import setup_gcd_hooks
from services.xpc_daemon import setup_xpc_hooks
from frameworks.audio_hid import setup_audio_hid_hooks
from frameworks.cocoa_gnustep import setup_cocoa_hooks
from frameworks.metal_vulkan_bridge import setup_metal_hooks
from frameworks.swift_runtime import setup_swift_hooks


class ArmBridgeEngine:
    def __init__(self, binary_path: str):
        self.binary_path = os.path.abspath(binary_path)
        self.vfs = VFSSandbox()
        self.rootfs_path = self.vfs.get_rootfs_path()
        self.ql = None
        self.entry_point = 0

    def initialize(self):
        print(f"[*] Initializing Qiling ARM64 Engine for {os.path.basename(self.binary_path)}...")

        try:
            # 1. TRICK THE ENGINE: Boot a raw Linux ARM64 CPU environment using an empty NOP instruction.
            # This bypasses Qiling's non-existent macOS loaders entirely.
            nop_shellcode = b"\x1f\x20\x03\xd5"  # ARM64 NOP instruction
            self.ql = Qiling(
                code=nop_shellcode,
                rootfs=self.rootfs_path,
                ostype=QL_OS.LINUX,
                archtype=QL_ARCH.ARM64,
                verbose=QL_VERBOSE.DEFAULT
            )

            # 2. BUILD A CUSTOM LOADER: Use LIEF to read the Apple binary and
            # forcefully inject its memory segments straight into the virtual CPU.
            print("[*] Bypassing native loader: Manually injecting Apple Mach-O segments into memory...")
            binary = lief.parse(self.binary_path)

            for segment in binary.segments:
                # __PAGEZERO is a 4 GB empty "guard" area at address 0. Skip it.
                if segment.name == "__PAGEZERO":
                    continue

                if segment.virtual_size > 0:
                    # Align memory allocations to standard 4KB (0x1000) boundaries
                    aligned_addr = segment.virtual_address & ~0xFFF
                    aligned_size = ((segment.virtual_address + segment.virtual_size + 0xFFF) & ~0xFFF) - aligned_addr

                    try:
                        # Map the virtual memory region for the segment
                        self.ql.mem.map(aligned_addr, aligned_size, info=segment.name)
                    except Exception as map_error:
                        print(f"[!] Could not map {segment.name} (continuing): {map_error}")

                    # Write the raw hex bytes from the binary straight into the CPU RAM
                    if segment.content:
                        self.ql.mem.write(segment.virtual_address, bytes(segment.content))
                        print(f"[+] Injected {segment.name} at {hex(segment.virtual_address)} "
                              f"({len(segment.content)} bytes)")

            # Extract the real Apple C binary entry point
            self.entry_point = binary.entrypoint
            if not self.entry_point:
                print("[-] Could not find the Mach-O entry point.")
                sys.exit(1)
            self.ql.arch.regs.arch_pc = self.entry_point

            setup_dyld_hooks(self.ql)
            setup_posix_syscalls(self.ql)
            setup_gcd_hooks(self.ql)
            setup_xpc_hooks(self.ql)
            setup_audio_hid_hooks(self.ql)
            setup_cocoa_hooks(self.ql)
            setup_metal_hooks(self.ql)
            setup_swift_hooks(self.ql)

            print("[+] Qiling ARM64 CPU Engine successfully initialized with all hooks.")
            print(f"[+] Mach-O Entry Point locked at: {hex(self.entry_point)}")
        except SystemExit:
            raise
        except Exception as e:
            traceback.print_exc()
            print(f"[-] Failed to initialize Qiling Engine: {e}")
            sys.exit(1)

    def run(self):
        if not self.ql:
            print("[-] Engine not initialized!")
            return

        print("[*] Starting ARM64 CPU emulation loop...")
        try:
            # Start the CPU directly at the Mach-O entry point.
            # (ql.run() in shellcode mode ignores our start address and only runs the dummy NOP.)
            uc = getattr(self.ql, "uc", None) or self.ql.arch.uc
            uc.emu_start(self.entry_point, 0xFFFFFFFFFFFFF000)  # second value = far-away "until" address
            print("[+] Execution finished.")
            print(f"[*] CPU stopped at pc = {hex(self.ql.arch.regs.arch_pc)}")
        except Exception as e:
            traceback.print_exc()
            print(f"[!] Emulation trapped/stopped: {e}")