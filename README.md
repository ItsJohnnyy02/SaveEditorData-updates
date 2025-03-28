# Schedule I Save Editor - Source Code

**Version**: 1.0.0  
**Last Updated**: March 27, 2025  

Welcome to the source code repository for *Schedule I Save Editor*, a Python-based tool designed to unlock in-game content for personal use. This project powers the standalone Windows app distributed via the [ScheduleIEditor-Installer](https://github.com/ItsJohnnyy02/ScheduleIEditor-Installer) public repo. Here, you’ll find the raw code, including the GUI, updater, and RAR extraction logic.

**Note**: This repository is private. The compiled installer is the only public release. See the [license](#license) below for usage terms.

---

## 🎯 Purpose
This editor simplifies modifying game save files by:
- Unlocking all properties via automated downloads and extraction.
- Providing a tabbed Tkinter GUI for easy cheat access.
- Supporting self-updates (currently in progress).

---

## 🛠️ Setup for Development
To run or modify the source code locally:

### Prerequisites
- **Python**: 3.8+ (tested on 3.11).
- **Dependencies**: Install via pip:
  ```bash
  pip install requests pyinstaller
