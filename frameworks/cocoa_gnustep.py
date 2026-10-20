def setup_cocoa_hooks(ql):
    print("[*] [frameworks/cocoa] Registering AppKit UI shims...")
    # Intercept objc_msgSend for window creation and map to Windows HWNDs
    pass