import subprocess
import sys

MENU = """
=============================
 Cloud Waste Tracker - Main
=============================
1) Run EC2 scanner
2) Run S3 scanner
0) Exit
Choose an option: """

def run_script(script_name: str):
    # Use the same interpreter you're running now (venv-safe)
    python_exe = sys.executable
    try:
        # No extra prompts: each script runs with its defaults
        subprocess.run([python_exe, script_name], check=False)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error running {script_name}: {e}")

def main():
    while True:
        choice = input(MENU).strip()
        if choice == "1":
            run_script("ec2_scanner.py")
        elif choice == "2":
            run_script("s3_scanner.py")
        elif choice == "0":
            print("Bye.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 0.")

if __name__ == "__main__":
    main()





