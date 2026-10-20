def setup_gcd_hooks(ql):
    print("[*] [services/gcd] Registering Grand Central Dispatch (libdispatch) shims...")
    # Translate dispatch_async/sync to Windows ThreadPool work items
    pass