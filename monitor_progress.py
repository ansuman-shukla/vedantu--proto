"""
Progress Monitor Script
This script shows how to monitor the real-time progress of PDF processing
"""

import json
import time
import os
from datetime import datetime

def monitor_progress(output_file="output.json", refresh_interval=2):
    """
    Monitor the progress of PDF processing in real-time
    
    Args:
        output_file (str): Path to the output JSON file being updated
        refresh_interval (int): Seconds between progress checks
    """
    
    print("🔍 PDF Processing Progress Monitor")
    print("="*50)
    print(f"📁 Monitoring: {output_file}")
    print(f"🔄 Refresh interval: {refresh_interval} seconds")
    print("Press Ctrl+C to stop monitoring\n")
    
    last_completed = 0
    
    try:
        while True:
            try:
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    status = data.get('processing_status', 'unknown')
                    completed = data.get('windows_completed', 0)
                    total = data.get('total_windows', 0)
                    questions_found = data.get('summary_stats', {}).get('total_questions_found', 0)
                    
                    # Clear screen for Windows/Unix
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    print("🔍 PDF Processing Progress Monitor")
                    print("="*50)
                    print(f"📄 PDF: {data.get('pdf_path', 'Unknown')}")
                    print(f"📊 Pages: {data.get('total_pages', 0)}")
                    print(f"🪟 Window Size: {data.get('window_size', 0)}")
                    print(f"🚀 Status: {status.upper()}")
                    
                    if total > 0:
                        progress_percent = (completed / total) * 100
                        progress_bar = "█" * int(progress_percent // 5) + "░" * (20 - int(progress_percent // 5))
                        print(f"📈 Progress: [{progress_bar}] {progress_percent:.1f}%")
                        print(f"✅ Windows: {completed}/{total}")
                    
                    print(f"❓ Questions Found: {questions_found}")
                    
                    if data.get('processing_started'):
                        print(f"⏰ Started: {data['processing_started']}")
                    
                    if status == 'completed':
                        if data.get('processing_completed'):
                            print(f"🏁 Completed: {data['processing_completed']}")
                        
                        # Show final statistics
                        if data.get('summary_stats', {}).get('questions_by_type'):
                            print("\n📝 Final Question Types:")
                            for q_type, count in data['summary_stats']['questions_by_type'].items():
                                print(f"   • {q_type}: {count}")
                        
                        print("\n🎉 Processing completed successfully!")
                        break
                    
                    # Show new windows completed
                    if completed > last_completed:
                        new_windows = completed - last_completed
                        print(f"\n🆕 {new_windows} new window(s) completed!")
                        
                        # Show questions from latest window
                        if data.get('windows_results') and len(data['windows_results']) > 0:
                            latest_window = data['windows_results'][-1]
                            latest_questions = latest_window.get('total_questions_found', 0)
                            print(f"   Latest window found {latest_questions} questions")
                        
                        last_completed = completed
                    
                    print(f"\n🔄 Last updated: {datetime.now().strftime('%H:%M:%S')}")
                    print("Press Ctrl+C to stop monitoring...")
                    
                else:
                    print(f"⏳ Waiting for {output_file} to be created...")
                
            except json.JSONDecodeError:
                print("⚠️  Output file is being written, retrying...")
            except Exception as e:
                print(f"❌ Error reading progress: {str(e)}")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {str(e)}")

def show_final_summary(output_file="output.json"):
    """
    Show a detailed summary of the completed processing
    
    Args:
        output_file (str): Path to the completed output JSON file
    """
    try:
        if not os.path.exists(output_file):
            print(f"❌ Output file not found: {output_file}")
            return
        
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n" + "="*60)
        print("📊 DETAILED PROCESSING SUMMARY")
        print("="*60)
        
        print(f"📄 PDF: {data.get('pdf_path', 'Unknown')}")
        print(f"📊 Total Pages: {data.get('total_pages', 0)}")
        print(f"🪟 Window Size: {data.get('window_size', 0)}")
        print(f"🔢 Total Windows: {data.get('total_windows', 0)}")
        print(f"✅ Windows Completed: {data.get('windows_completed', 0)}")
        print(f"🚀 Status: {data.get('processing_status', 'unknown').upper()}")
        
        total_questions = data.get('summary_stats', {}).get('total_questions_found', 0)
        print(f"❓ Total Questions Found: {total_questions}")
        
        # Question type breakdown
        if data.get('summary_stats', {}).get('questions_by_type'):
            print("\n📝 Questions by Type:")
            for q_type, count in data['summary_stats']['questions_by_type'].items():
                percentage = (count / total_questions * 100) if total_questions > 0 else 0
                print(f"   • {q_type}: {count} ({percentage:.1f}%)")
        
        # Difficulty breakdown
        if data.get('summary_stats', {}).get('questions_by_difficulty'):
            print("\n📈 Questions by Difficulty:")
            for difficulty, count in data['summary_stats']['questions_by_difficulty'].items():
                percentage = (count / total_questions * 100) if total_questions > 0 else 0
                print(f"   • {difficulty}: {count} ({percentage:.1f}%)")
        
        # Window-by-window breakdown
        print(f"\n🪟 Window Breakdown:")
        windows_results = data.get('windows_results', [])
        for i, window in enumerate(windows_results[:5], 1):  # Show first 5 windows
            window_questions = window.get('total_questions_found', 0)
            page_range = window.get('page_range', 'unknown')
            print(f"   Window {i} (pages {page_range}): {window_questions} questions")
        
        if len(windows_results) > 5:
            print(f"   ... and {len(windows_results) - 5} more windows")
        
        # Timing information
        if data.get('processing_started'):
            print(f"\n⏰ Started: {data['processing_started']}")
        if data.get('processing_completed'):
            print(f"🏁 Completed: {data['processing_completed']}")
        
        print(f"\n💾 Full results available in: {output_file}")
        
    except Exception as e:
        print(f"❌ Error showing summary: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "output.json"
    
    print("Choose an option:")
    print("1. Monitor progress in real-time")
    print("2. Show final summary")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        monitor_progress(output_file)
    elif choice == "2":
        show_final_summary(output_file)
    else:
        print("Invalid choice. Showing final summary...")
        show_final_summary(output_file)
