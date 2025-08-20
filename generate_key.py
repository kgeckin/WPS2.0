"""
generate_key.py
---------------
Script to generate a Fernet key and add it to your .env file if not present.
Should only be run manually once during project setup.
"""

import os
from cryptography.fernet import Fernet

def ensure_secret_key_in_env(env_path=".env"):
    key_name = "SECRET_KEY"
    new_key = Fernet.generate_key().decode()
    # If .env doesn't exist, create it and add key
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key_name}={new_key}\n")
        print(f"Created new .env file with {key_name}.")
        return new_key

    with open(env_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.strip().startswith(f"{key_name}="):
            print(f"{key_name} already exists in .env. No changes made.")
            return line.strip().split("=",1)[1]

    with open(env_path, "a") as f:
        f.write(f"{key_name}={new_key}\n")
    print(f"Appended {key_name} to .env file.")
    return new_key

if __name__ == "__main__":
    key = ensure_secret_key_in_env()
    print("Current Fernet SECRET_KEY in .env:", key)
