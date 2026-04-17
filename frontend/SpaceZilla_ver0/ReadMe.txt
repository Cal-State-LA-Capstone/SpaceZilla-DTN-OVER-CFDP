1. Place this folder inside your PyION folder. This way, your QtWidget can access the ui file.

Inside this folder, you will find 4 things:

	1. SpaceZilla_ver0.ui: this is the ui file able to be opened and edited via QtWidget.
	
	2. spacezilla_main.py: This is the file you will be MODIFYING to add functions to buttons, change color palette, connect diff windows etc.
	
	3. ui_spacezilla.py: this is the GENERATED Python file of SpaceZilla_ver0.ui. You do not modify this file. However, you must UPDATE (re-generate) this file each time you make and save any edits in the QtWidget using the following command:
	
		pyside6-uic SpaceZilla_ver0.ui -o ui_spacezilla.py
	
	4. _pycache_: just cache. No need to touch it.
	
2. In your terminal, enter the PyION folder.

3. Open QtWidget using the following command:

	pyside6-designer

4. Within the widget, open the ui file. This will allow you to add new things to the main page. ***Remember, any changes made in this space means you must REGENERATE ui_spacezilla.py using the above given command.

5. To open the SpaceZilla window itself to test your Python modifications in spacezilla_main.py (menus, functioning buttons, etc.), open a new terminal window (make sure it's in the right file location, aka within the SpaceZilla_ver0 folder) and use:

	python3 spacezilla_main.py
	
This will either open up a window, or tell you what errors it encountered while trying to open the file in your terminal.

Note: the terminal window just. Opens. At the moment. I do not know if it connects(?), check that if you guys can.
-------------------------------------------
Optional Ubuntu launcher support

SpaceZilla can still be run normally with:
    python spacezilla_main.py

An optional Ubuntu desktop launcher is included for app search, dock icon, and Alt+Tab integration.

Launcher related files:
    icons/SpaceZillaLogo.png
    run_spacezilla.sh
    linux/spacezilla.desktop

To install the launcher locally on Ubuntu:

    mkdir -p ~/.local/share/applications
    cp ~/SpaceZilla-DTN-OVER-CFDP/frontend/SpaceZilla_ver0/linux/spacezilla.desktop ~/.local/share/applications/
    update-desktop-database ~/.local/share/applications

After that, search for "SpaceZilla" in Ubuntu and launch it from the app menu.
