# ArmBridge

**An experiment to run macOS Apple Silicon (ARM64) programs on Windows, with no VM and no Mac.**

ArmBridge reads a macOS Mach-O program, loads it into an emulated ARM64 CPU, and catches its system calls so they can be answered by Windows instead of macOS.

The long-term idea is "Wine for macOS ARM64 on Windows". Today it runs a tiny hello world. It is an early prototype.

## Demo

```
python core/main.py hello_arm64
```

```
[+] Binary architecture verified: macOS ARM64 (Apple Silicon)
[+] Injected __TEXT at 0x100000000 (16384 bytes)
[+] Mach-O Entry Point locked at: 0x100000400
[*] Starting ARM64 CPU emulation loop...
Hello from ARM Mac!
[+] Mac program exited with code 0
```

The test program is built by hand (no Apple tools needed) with `make_hello_arm64.py`. It makes two macOS syscalls, `write` and `exit`, and nothing else.

## Status

| Part | State |
|---|---|
| Read Mach-O files (LIEF) and check they are ARM64 | Working |
| Load Mach-O segments into emulated memory | Working |
| Start the CPU at the program's entry point | Working |
| macOS syscalls: `write`, `exit` | Working |
| More syscalls (`read`, `open`, `close`, `mmap`...) | Not yet |
| dyld and Apple libraries (libSystem) | Not yet |
| Real programs (like command-line tools) | Not yet |
| GUI apps (Cocoa), Metal graphics, Swift runtime | Planned, files are empty stubs |

## How it works

1. `core/main.py` checks the file is a macOS ARM64 Mach-O.
2. `core/qiling_engine.py` starts a blank ARM64 CPU with [Qiling](https://github.com/qilingframework/qiling) (Unicorn), then copies the Mach-O segments into its memory by hand.
3. The CPU starts at the Mach-O entry point.
4. When the program runs `svc #0x80`, `subsystems/posix_syscalls.py` catches it. On ARM Macs the syscall number is in register `x16`.
5. The syscall is answered by Python on Windows (for example, `write` prints to the console).

## Limitations

- **It is emulation, not native.** ARM code runs on an Intel/AMD PC through an emulator, so it is much slower than a real Mac.
- Programs that use Apple's libraries will not work yet, because there is no dyld or libSystem replacement.
- Only two syscalls exist so far.

## Run it yourself

Requirements: Windows, Python 3.10+

```
pip install -r requirements.txt
python make_hello_arm64.py
python core/main.py hello_arm64
```

## Project structure

```
ArmBridge/
├── core/                  # entry point, Qiling engine, dyld hook (stub)
├── subsystems/            # syscalls (working), virtual filesystem
├── services/              # GCD, XPC (stubs)
├── frameworks/            # Cocoa, Metal, audio, Swift (stubs)
├── make_hello_arm64.py    # builds the hello world test program
└── requirements.txt
```

## Roadmap

1. More syscalls, one at a time, each with a tiny test program.
2. Load and run `real_macho.bin` (needs a dyld / libSystem replacement).
3. Command-line tools first, GUI apps much later.

## Credits

Built with [Qiling](https://github.com/qilingframework/qiling) and [LIEF](https://lief-project.github.io/). Inspired by [Wine](https://www.winehq.org/) and [Darling](https://www.darlinghq.org/).