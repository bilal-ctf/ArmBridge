import os

class VFSSandbox:
    def __init__(self, base_dir: str = None):
        # Anchor the rootfs inside the ArmBridge base directory
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rootfs = os.path.join(self.base_dir, "rootfs")
        self._setup_sandbox_dirs()

    def _setup_sandbox_dirs(self):
        """Builds standard macOS virtual directory structure on the Windows host."""
        standard_dirs = [
            "System/Library/Frameworks",
            "usr/lib",
            "usr/bin",
            "var/tmp",
            "private/etc",
            "tmp"
        ]
        for path in standard_dirs:
            os.makedirs(os.path.join(self.rootfs, path), exist_ok=True)

    def get_rootfs_path(self) -> str:
        return self.rootfs