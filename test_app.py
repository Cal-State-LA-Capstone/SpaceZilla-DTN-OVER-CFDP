# test_app.py
#
# This is the entry point for the test application.
# Its job is only to:
#   1. create the backend
#   2. create the UI
#   3. connect the controller
#   4. start the Tkinter event loop

from backend.backend_facade import BackendFacade
from frontend.test_controller import TestController
from frontend.test_ui import TestUI


def main():
    # Create the backend facade.
    # The facade is the single frontend-facing object that wraps the backend.
    backend = BackendFacade()
    backend.startup_check()
    # Create the UI window and widgets.
    ui = TestUI()
    # Create the controller.
    # This wires button clicks and UI events to backend actions.
    TestController(backend, ui)

    # Start the Tkinter application loop.
    ui.root.mainloop()


if __name__ == "__main__":
    main()
