"""
subsystems/posix_syscalls.py  (replaces your empty stub)

ARM Macs make a syscall with `svc #0x80` and put the syscall number in x16.
(Linux puts it in x8, so Qiling's own Linux handler is wrong for us.)

Supported so far: write (4), exit (1).
"""
import sys

SYS_EXIT = 1
SYS_WRITE = 4


def setup_posix_syscalls(ql):
    print("[*] [subsystems/posix] Registering BSD syscall -> Windows translators...")

    # Switch off Qiling's built-in Linux syscall handler, it reads x8 and would be confused.
    if hasattr(ql.os, "load_syscall"):
        ql.os.load_syscall = lambda *args, **kwargs: None

    def stop():
        if hasattr(ql, "emu_stop"):
            ql.emu_stop()
        else:
            ql.stop()

    def on_svc(ql, intno):
        regs = ql.arch.regs
        num = regs.read("x16")

        if num == SYS_WRITE:
            fd, buf, count = regs.read("x0"), regs.read("x1"), regs.read("x2")
            text = bytes(ql.mem.read(buf, count))
            out = {1: sys.stdout, 2: sys.stderr}.get(fd)
            if out:
                out.write(text.decode("utf-8", "replace"))
                out.flush()
                regs.write("x0", count)          # result = bytes written
            else:
                regs.write("x0", 9)              # EBADF (bad file number)

        elif num == SYS_EXIT:
            print(f"[+] Mac program exited with code {regs.read('x0')}")
            stop()

        else:
            print(f"[!] Unsupported macOS syscall number {num} (not built yet)")
            stop()

    ql.hook_intno(on_svc, 2)   # intno 2 = SVC on ARM64