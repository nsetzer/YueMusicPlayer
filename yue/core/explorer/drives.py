#! python34 $this

import sys
import string

if sys.platform == "win32":
    from ctypes import windll

    def get_drives():
        drives = []
        #value = windll.kernel32.SetErrorMode(0)
        windll.kernel32.SetErrorMode(1)
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter)
            bitmask >>= 1
        return [d + ":\\" for d in drives]

else:
    def get_drives():
        return ["/",]

if __name__ == '__main__':
    print(get_drives())     # On my PC, this prints ['A', 'C', 'D', 'F', 'H']