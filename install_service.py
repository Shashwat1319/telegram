import os, sys, subprocess, getpass

TASK_NAME = "BudgetDealsOrchestrator"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR = os.path.join(SCRIPT_DIR, "orchestrator.py")
LOG_FILE = os.path.join(SCRIPT_DIR, "orchestrator.log")


def find_pythonw():
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    alt = os.path.join(python_dir, "..", "pythonw.exe")
    if os.path.exists(alt):
        return os.path.abspath(alt)

    for drive in ["C:\\", "D:\\"]:
        for root, dirs, files in os.walk(drive + "Python"):
            if "pythonw.exe" in files:
                return os.path.join(root, "pythonw.exe")
            if "python3.exe" in files:
                py = os.path.join(root, "python3.exe")
                pw = os.path.join(os.path.dirname(py), "pythonw.exe")
                if os.path.exists(pw):
                    return pw

    return None


def main():
    print("=" * 55)
    print("  Budget Deals India - Auto Installer")
    print("  Will install as hidden background service")
    print("=" * 55)

    pythonw = find_pythonw()
    if not pythonw:
        print("\n[!] Could not find pythonw.exe")
        print("    Make sure Python is installed correctly.")
        input("\nPress Enter to exit...")
        return

    print(f"\n[+] PythonW found: {pythonw}")
    print(f"[+] Script: {ORCHESTRATOR}")
    print(f"[+] Logs will be at: {LOG_FILE}")

    if not os.path.exists(ORCHESTRATOR):
        print(f"\n[!] orchestrator.py not found at:")
        print(f"    {ORCHESTRATOR}")
        input("\nPress Enter to exit...")
        return

    username = getpass.getuser()

    cmd = (
        f'schtasks /CREATE /SC ONLOGON /TN "{TASK_NAME}" '
        f'/TR "\'{pythonw}\' \'{ORCHESTRATOR}\'" '
        f'/RU "{username}" /F /IT /DELAY 0001:00'
    )

    print(f"\n[+] Installing scheduled task: {TASK_NAME}")
    print(f"[+] Task will run at every logon with 1 minute delay")
    print(f"[+] No terminal window will appear")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("\n✅ INSTALLATION SUCCESSFUL!")
            print("\n   The orchestrator will start automatically:")
            print("   - When you log into Windows")
            print("   - ~1 minute after login")
            print("   - No terminal window visible")
            print("   - Runs in background using pythonw.exe")
            print(f"\n   Log file: {LOG_FILE}")
            print(f"\n   To stop:  schtasks /end /tn \"{TASK_NAME}\"")
            print(f"   To start: schtasks /run /tn \"{TASK_NAME}\"")
            print(f"   To remove: schtasks /DELETE /TN \"{TASK_NAME}\" /F")
        else:
            print(f"\n❌ FAILED!")
            print(f"   Error: {result.stderr}")

            print("\n   Trying alternative method...")
            alt_cmd = (
                f'schtasks /CREATE /SC ONLOGON /TN "{TASK_NAME}" '
                f'/TR "\'{pythonw}\' \'{ORCHESTRATOR}\'" '
                f"/F"
            )
            result2 = subprocess.run(alt_cmd, shell=True, capture_output=True, text=True)
            if result2.returncode == 0:
                print("\n✅ INSTALLATION SUCCESSFUL! (alt method)")
            else:
                print(f"\n❌ Still failed: {result2.stderr}")
                print("\nTry running this as Administrator:")
                print(f"  {alt_cmd}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
