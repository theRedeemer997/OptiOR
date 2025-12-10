import subprocess
import time
import os
import sys
import platform

def kill_process_tree(pid):
    """Kills a process tree (including children) robustly on Windows/Unix."""
    if platform.system() == "Windows":
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
    else:
        os.killpg(os.getpgid(pid), signal.SIGTERM)

def run_app():
    root_dir = os.getcwd()
    frontend_dir = os.path.join(root_dir, "web-app")
    
    # 1. Start Backend
    print("🚀 Starting OptiOR Backend...")
    # Using python directly
    backend = subprocess.Popen(
        [sys.executable, "server_new.py"], 
        cwd=root_dir,
        shell=False
    )
    
    # Wait a moment for backend to initialize
    time.sleep(2)
    
    # 2. Start Frontend
    print("🚀 Starting OptiOR Frontend...")
    # On Windows, npm is a batch file, so shell=True is often required or finding npm.cmd
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"], 
        cwd=frontend_dir,
        shell=False # Better process control if we call npm.cmd directly
    )

    print("\n✅ OptiOR is active!")
    print("   Backend: http://127.0.0.1:5000")
    print("   Frontend: http://localhost:3000")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print("❌ Backend stopped unexpectedly.")
                break
            if frontend.poll() is not None:
                print("❌ Frontend stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
    finally:
        # Cleanup
        if backend.poll() is None:
            kill_process_tree(backend.pid)
        if frontend.poll() is None:
            kill_process_tree(frontend.pid)
        print("Goodbye!")

if __name__ == "__main__":
    run_app()
