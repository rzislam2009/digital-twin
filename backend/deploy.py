import os
import shutil
import zipfile
import subprocess

def main():
    print("🚀 Starting Lambda deployment packaging...")

    # 1. Clean up previous builds
    paths_to_clean = ["lambda-package", "lambda-deployment.zip"]
    for path in paths_to_clean:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    # 2. Create package directory
    os.makedirs("lambda-package")

    # 3. Install dependencies using Docker
    # We use the SAM build image because it has better compatibility for native C-extensions
    print("📦 Installing dependencies inside Docker (Linux x86_64)...")
    
    docker_command = [
        "docker", "run", "--rm",
        "-v", f"{os.getcwd()}:/var/task",
        "--platform", "linux/amd64",
        "public.ecr.aws/sam/build-python3.12:latest", # Use the Build image specifically
        "/bin/sh", "-c",
        "pip install -r requirements.txt -t /var/task/lambda-package --upgrade --only-binary=:all:"
    ]

    try:
        subprocess.run(docker_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker pip install failed: {e}")
        return

    # 4. Copy application files
    print("📄 Copying application files...")
    app_files = ["server.py", "lambda_handler.py", "context.py", "resources.py"]
    for file in app_files:
        if os.path.exists(file):
            shutil.copy2(file, "lambda-package/")
        else:
            print(f"⚠️ Warning: {file} not found, skipping.")
    
    # 5. Copy data directory
    if os.path.exists("data"):
        shutil.copytree("data", "lambda-package/data", dirs_exist_ok=True)

    # 6. Create zip (Ensure the root of the zip contains lambda_handler.py)
    print("🤐 Creating zip file...")
    with zipfile.ZipFile("lambda-deployment.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda-package"):
            for file in files:
                file_path = os.path.join(root, file)
                # arcname makes sure the file isn't nested inside a 'lambda-package' folder inside the zip
                arcname = os.path.relpath(file_path, "lambda-package")
                zipf.write(file_path, arcname)

    # 7. Final Report
    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"✅ Success! Created lambda-deployment.zip ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()