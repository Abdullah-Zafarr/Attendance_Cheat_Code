"""
main.py — Entry point for the Attendance Alarm application.

Usage:
    python main.py
"""

import tkinter as tk
from gui import AttendanceAlarmApp


def main():
    root = tk.Tk()
    app = AttendanceAlarmApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
