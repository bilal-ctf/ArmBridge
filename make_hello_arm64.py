"""
Builds a tiny macOS ARM64 (Apple Silicon) Mach-O program by hand.
It needs NO libraries and NO dyld. It only does 2 macOS syscalls:
  write(1, "Hello from ARM Mac!\n", 20)   -> x16 = 4
  exit(0)                                 -> x16 = 1
On ARM Macs the syscall number goes in x16 and the call is `svc #0x80`.

Run:  python make_hello_arm64.py
Output: hello_arm64
"""
import struct

BASE = 0x100000000
CODE_OFFSET = 0x400
PAGE = 0x4000                 # ARM Macs use 16 KB pages
MSG = b"Hello from ARM Mac!\n"


# ---------- tiny ARM64 assembler (only what we need) ----------
def movz(reg, imm):           # mov xREG, #imm
    return 0xD2800000 | (imm << 5) | reg

def adr(reg, offset):         # adr xREG, pc+offset
    return ((offset & 3) << 29) | 0x10000000 | (((offset >> 2) & 0x7FFFF) << 5) | reg

def svc(imm):                 # svc #imm
    return 0xD4000001 | (imm << 5)

# sanity checks against encodings I know
assert svc(0x80) == 0xD4001001
assert adr(0, 4) == 0x10000020

# ---------- the program ----------
n_instr = 8
msg_offset = n_instr * 4                     # message sits right after the code
adr_offset = msg_offset - 2 * 4              # adr is instruction #2
instrs = [
    movz(16, 4),              # x16 = 4   (write)
    movz(0, 1),               # x0  = 1   (stdout)
    adr(1, adr_offset),       # x1  = address of the text
    movz(2, len(MSG)),        # x2  = text length
    svc(0x80),                # do the syscall
    movz(16, 1),              # x16 = 1   (exit)
    movz(0, 0),               # x0  = 0   (exit code)
    svc(0x80),                # do the syscall
]
assert len(instrs) == n_instr
code = b"".join(struct.pack("<I", i) for i in instrs) + MSG


# ---------- Mach-O pieces ----------
def segment(name, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, sections=b"", nsects=0):
    return struct.pack("<II16sQQQQIIII", 0x19, 72 + len(sections), name.ljust(16, b"\0"),
                       vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, 0) + sections

pagezero = segment(b"__PAGEZERO", 0, BASE, 0, 0, 0, 0)

text_section = struct.pack("<16s16sQQIIIIIIII",
                           b"__text".ljust(16, b"\0"), b"__TEXT".ljust(16, b"\0"),
                           BASE + CODE_OFFSET, len(code), CODE_OFFSET,
                           2, 0, 0, 0x80000400, 0, 0, 0)
text = segment(b"__TEXT", BASE, PAGE, 0, PAGE, 7, 5, text_section, 1)

# LC_UNIXTHREAD for ARM64: flavor 6, 68 words of state. pc is register #32.
regs = [0] * 34
regs[32] = BASE + CODE_OFFSET
unixthread = struct.pack("<IIII", 0x5, 8 + 8 + 272, 6, 68) + struct.pack("<34Q", *regs)

cmds = pagezero + text + unixthread
header = struct.pack("<IiiIIIII", 0xfeedfacf, 0x0100000c, 0, 2, 3, len(cmds), 1, 0)

blob = header + cmds
assert len(blob) <= CODE_OFFSET
blob = blob.ljust(CODE_OFFSET, b"\0") + code
blob = blob.ljust(PAGE, b"\0")

with open("hello_arm64", "wb") as f:
    f.write(blob)

print(f"Wrote hello_arm64 ({len(blob)} bytes)")
print(f"Start address: 0x{BASE + CODE_OFFSET:x}")
print(f"Code: {len(instrs)} instructions + {len(MSG)} bytes of text")