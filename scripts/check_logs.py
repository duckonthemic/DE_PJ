import os
import glob
from datetime import datetime

def check_logs():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        print(f"Log directory '{log_dir}' not found.")
        return

    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    if not log_files:
        print("No log files found.")
        return

    print(f"=== Log Summary ({datetime.now()}) ===")
    
    for log_file in log_files:
        filename = os.path.basename(log_file)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        error_count = sum(1 for line in lines if "ERROR" in line)
        warning_count = sum(1 for line in lines if "WARNING" in line)
        
        status = "✅ OK"
        if error_count > 0:
            status = "❌ ERROR"
        elif warning_count > 0:
            status = "⚠️ WARNING"
            
        print(f"{status} | {filename:<30} | Errors: {error_count} | Warnings: {warning_count}")

if __name__ == "__main__":
    check_logs()
