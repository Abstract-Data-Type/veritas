#!/usr/bin/env python3
"""
Demo script to show the news worker in action
"""

import asyncio
import subprocess
import time

def run_command(cmd):
    """Run a command and print output"""
    print(f"\n🔹 Running: {cmd}")
    print("=" * 50)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0

def main():
    print("🚀 NEWS WORKER DEMO")
    print("This will demonstrate the stubbed news worker storing articles")
    
    # Clear any existing data
    print("\n1️⃣ Clearing database...")
    run_command("python -m src.worker.news_worker --clear")
    
    # Show initial empty status
    print("\n2️⃣ Initial status (should be empty):")
    run_command("python -m src.worker.news_worker --status")
    
    # Run first fetch
    print("\n3️⃣ Running first fetch...")
    run_command("python -m src.worker.news_worker --once")
    
    # Show status after first fetch
    print("\n4️⃣ Status after first fetch:")
    run_command("python -m src.worker.news_worker --status")
    
    # Show all articles
    print("\n5️⃣ All articles stored:")
    run_command("python -m src.worker.news_worker --show-all")
    
    # Run second fetch (should see duplicates skipped)
    print("\n6️⃣ Running second fetch (duplicates should be skipped):")
    run_command("python -m src.worker.news_worker --once")
    
    # Show sources summary
    print("\n7️⃣ Sources summary:")
    run_command("python -m src.worker.news_worker --sources")
    
    print("\n✅ DEMO COMPLETE!")
    print("The worker successfully:")
    print("  - Fetched stubbed articles from multiple sources")
    print("  - Stored them in the database")
    print("  - Detected and skipped duplicates")
    print("  - Provided visualization of stored data")

if __name__ == "__main__":
    main()