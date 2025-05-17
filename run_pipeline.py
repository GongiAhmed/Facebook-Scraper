import os
import subprocess
import time
import requests
import pymongo
from pymongo.errors import ConnectionFailure

def check_mongodb_connection():
    """Check if MongoDB is running and create database if needed"""
    print("Checking MongoDB connection...")
    try:
        # Try to connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        # Force a command to check the connection
        client.admin.command('ping')
        
        # Create database and collection if they don't exist
        db = client["facebook_comments"]
        collection = db["toxicity_analysis"]
        
        # Create an index on toxicity for faster queries
        collection.create_index("toxicity")
        
        print("MongoDB connection successful!")
        return True
    except ConnectionFailure:
        print("MongoDB connection failed. Make sure MongoDB is running.")
        return False
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        return False

def run_scraper():
    """Run the Facebook scraper to collect posts"""
    print("Running Facebook scraper...")
    subprocess.run(["python", "facebook_scraper.py"])
    
    # Check if the CSV file was created
    if os.path.exists("harcelement_posts.csv"):
        print("Scraper completed successfully!")
        return True
    else:
        print("Scraper failed to create CSV file.")
        return False

def upload_to_api(csv_file):
    """Upload the CSV file to the FastAPI application"""
    print(f"Uploading {csv_file} to API...")
    url = "http://localhost:8000/upload-csv/"
    
    with open(csv_file, "rb") as f:
        files = {"file": (csv_file, f, "text/csv")}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        print("Upload successful!")
        return True
    else:
        print(f"Upload failed: {response.text}")
        return False

def check_api_running():
    """Check if the FastAPI server is running"""
    print("Checking if API server is running...")
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("API server is running!")
            return True
        else:
            print(f"API server returned unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("API server is not running. Please start the server with 'python -m uvicorn app:app --reload'")
        return False
    except Exception as e:
        print(f"Error checking API server: {str(e)}")
        return False

def check_and_fix_dependencies():
    """Check and fix package compatibility issues"""
    print("Checking package dependencies...")
    try:
        # Try to import pandas to check if it works
        import pandas
        print("Pandas import successful!")
    except ValueError as e:
        if "numpy.dtype size changed" in str(e):
            print("Detected numpy compatibility issue. Attempting to fix...")
            # Reinstall numpy and pandas in the correct order
            subprocess.run(["pip", "uninstall", "-y", "numpy", "pandas"])
            subprocess.run(["pip", "install", "numpy==1.23.5"])  # Use a stable version
            subprocess.run(["pip", "install", "pandas"])
            print("Dependencies fixed. Please restart the application.")
            return False
        else:
            print(f"Unexpected error importing pandas: {str(e)}")
            return False
    except ImportError as e:
        print(f"Error importing pandas: {str(e)}")
        return False
    
    return True

def main():
    # Check dependencies first
    if not check_and_fix_dependencies():
        return
    
    # Step 0: Check MongoDB connection
    if not check_mongodb_connection():
        print("Exiting due to MongoDB connection failure.")
        return
    
    # Step 1: Run the scraper
    if not run_scraper():
        print("Exiting due to scraper failure.")
        return
    
    # Step 2: Check if API is running
    if not check_api_running():
        print("Would you like to start the API server now? (y/n)")
        choice = input().lower()
        if choice == 'y':
            print("Starting API server...")
            # Use python -m uvicorn instead of direct uvicorn command
            subprocess.Popen(["python", "-m", "uvicorn", "app:app", "--reload"], 
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("Waiting for API server to start...")
            time.sleep(10)  # Give it time to start
            if not check_api_running():
                print("Failed to start API server. Please start it manually.")
                return
        else:
            print("Exiting. Please start the API server manually.")
            return
    
    # Step 3: Upload the CSV file to the API
    if not upload_to_api("harcelement_posts.csv"):
        print("Exiting due to upload failure.")
        return
    
    print("\nPipeline completed successfully!")
    print("You can now access the API at http://localhost:8000")
    print("- View analyzed comments: http://localhost:8000/comments/")
    print("- View statistics: http://localhost:8000/stats/")

if __name__ == "__main__":
    main()