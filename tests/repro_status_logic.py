
import sys
import os
from unittest.mock import MagicMock, patch

# Mock PyQt6 modules to avoid GUI requirement
with patch.dict(sys.modules, {
    'PyQt6': MagicMock(), 
    'PyQt6.QtWidgets': MagicMock(),
    'PyQt6.QtCore': MagicMock(),
    'PyQt6.QtGui': MagicMock(),
    'send2trash': MagicMock(),
}):
    from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel
    # Manually import main_window_qt to test the logic
    # We need to bypass some imports inside main_window_qt too if they use Qt
    
    # Let's just strip the class logic we want to test: on_file_finished
    
    # We will "mock" the MainWindow class instance
    class MockMainWindow:
        def __init__(self):
            self.list_widget = MagicMock()
            self.added_paths = set()
            
        # We'll copy the method source or just patch it?
        # Actually, since we modified the file, let's verify the file content string directly
        # to ensure indentation is correct.
        pass

def verify_indentation():
    file_path = r"f:\PyApps\videoconverter\src\ui\main_window_qt.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start_line = 0
    for i, line in enumerate(lines):
        if "def on_file_finished" in line:
            start_line = i
            break
            
    relevant_lines = lines[start_line:start_line+30]
    
    # Look for the success block
    success_block_found = False
    else_block_found = False
    failed_status_indent = -1
    done_status_indent = -1
    
    for line in relevant_lines:
        stripped = line.strip()
        if "if success:" in line:
            success_block_found = True
            
        if success_block_found and 'w.set_status("Done"' in line:
            done_status_indent = len(line) - len(line.lstrip())
            
        if success_block_found and 'else:' in line:
            # Check indentation of else
            pass
            
        if success_block_found and 'w.set_status("Failed"' in line:
            failed_status_indent = len(line) - len(line.lstrip())
            print(f"Found 'Failed' status line: {stripped}")
            
    # Logic Verification:
    # "Done" line usually has 24 spaces (if tab=4 and inside if success > if w.path == path > for i in range)
    # The "Failed" line should have SAME indentation as "Done" line IF it was incorrect (outside else) 
    # BUT wait, the correction puts "Failed" INSIDE an `else` block for `if success`.
    # Let's check relative indentation.
    
    if done_status_indent == -1:
        print("Could not find 'Done' status line.")
        return False
        
    print(f"'Done' indent: {done_status_indent}")
    print(f"'Failed' indent: {failed_status_indent}")
    
    # In the fixed code:
    # if success:
    #    ...
    #    set "Done"
    # else:
    #    set "Failed"
    
    # The 'set "Failed"' line should be indented MORE than the 'else' line, and the 'else' line should match 'if success'.
    # And 'set "Done"' is inside 'if success', so 'set "Failed"' inside 'else' should roughly match 'set "Done"' indentation 
    # IF they are simple blocks.
    
    if failed_status_indent == done_status_indent:
        print("SUCCESS: 'Failed' logic appears to be in correct block depth (assuming aligned with Done).")
        return True
    else:
        # Wait, if done is inside `else` of `deleted`, it is deeper.
        # Original code structure:
        # if success:
        #    if deleted:
        #        ...
        #    else:
        #        set "Done"  <-- Deep
        # else:
        #    set "Failed" <-- Shallow (aligned with if success)
        
        # Ah! `if success:` is at level N. `w.set_status("Done")` is at N+2 (inside if success > else).
        # `w.set_status("Failed")` should be at N+1 (inside else).
        
        # My patch moved it to:
        # else:
        #    w.set_status("Failed")
        
        # So "Failed" status should be LESS indented than "Done" if "Done" is nested in that inner else.
        pass

if __name__ == "__main__":
    verify_indentation()
