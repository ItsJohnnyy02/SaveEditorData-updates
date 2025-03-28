# Schedule I Save Editor - Source Code & License  
*Version 1.0.0*  
*Last Updated: March 27, 2025*

Hey there! Welcome to the heart of **Schedule I Save Editor**, where the magic happens. This private repo holds the Python source code that powers the slick Windows app you can grab from the [ScheduleIEditor-Installer](https://github.com/ItsJohnnyy02/ScheduleIEditor-Installer) public repo. Below, you’ll find the dev details and the *all-important* license that keeps this locked down.

---

### ✨ What’s This About?
This tool’s built to tweak game saves with style:  
- **Unlocks Properties**: Grabs and applies in-game goodies effortlessly.  
- **Sleek GUI**: A Tkinter tabbed interface for cheat mastery.  
- **Auto-Update**: Pulls updates from the public repo (*work in progress*).  
- **Custom Vibes**: Rocks a unique icon for that personal touch.

---

### 📦 Setup for Devs
Wanna dive in and tinker? Here’s how to get rolling:

#### Requirements
- **Python**: 3.8+ (I’m using 3.11).  
- **Tools**:  
  - [7-Zip](https://www.7-zip.org/) or [WinRAR](https://www.win-rar.com/) for extraction.  
- **Dependencies**:  
  ```bash
  pip install requests pyinstaller

  🗂️ What’s Inside
editor.py: The core—GUI, updater, and save magic.
editor.ico: That sweet custom icon.
editor_installer.iss: Inno Setup script for the installer.
data/: Where RARs unpack at runtime.

⚙️ How It Works
GUI: Tkinter Notebook tabs for cheats.
Updater: Dual-mode for .py and .exe updates.
RAR Magic: Pulls and extracts Properties.rar with 7-Zip or WinRAR.

🚧 Heads Up
Auto-Update: Not quite there yet—planning a fix in a few days!
Permissions: Might need admin vibes or an AppData tweak for data.

📝 Dev Notes
Updater Fix: Next up—swapping hardcoded versions for a GitHub API check.

Got questions? Ping me directly!

