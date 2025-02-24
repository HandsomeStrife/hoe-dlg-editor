import os
import codecs
import sys

def search_dlg_files(directory, target_text):
    # Common encodings that might be used for Russian text
    encodings = ['cp1251', 'utf-8', 'koi8-r', 'iso-8859-5']
    
    # Convert search text to bytes for different encodings
    search_bytes = []
    for encoding in encodings:
        try:
            search_bytes.append(target_text.encode(encoding))
        except UnicodeEncodeError:
            continue

    found = False
    # Walk through all directories
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dlg'):
                file_path = os.path.join(root, file)
                try:
                    # Read file in binary mode
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        
                        # Try to find text in different encodings
                        for encoded_text in search_bytes:
                            if encoded_text in content:
                                found = True
                                print(f"\nFound match in: {file_path}")
                                # Try to get some context
                                pos = content.find(encoded_text)
                                start = max(0, pos - 100)
                                end = min(len(content), pos + len(encoded_text) + 100)
                                context = content[start:end]
                                
                                # Try to decode the context in the matching encoding
                                try:
                                    decoded = context.decode(encodings[search_bytes.index(encoded_text)])
                                    print(f"Context: {decoded}\n")
                                except:
                                    print("Could not decode context\n")
                                
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
    
    if not found:
        print("\nNo matches found.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search_dlg.py <search_directory> <search_text>")
        print("Example: python search_dlg.py Data 'Сид, сынок!'")
        sys.exit(1)
        
    search_dir = sys.argv[1]
    search_text = sys.argv[2]
    
    if not os.path.exists(search_dir):
        print(f"Directory {search_dir} does not exist!")
        sys.exit(1)
    
    print(f"\nSearching for text in .dlg files under {search_dir}...")
    search_dlg_files(search_dir, search_text) 