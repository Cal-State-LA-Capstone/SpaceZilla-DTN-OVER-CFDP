from backend.test_backend import TestBackend
from frontend.test_frontend import TestUI
from runtime_logger import setup_logging


def main():
    setup_logging()
    backend = TestBackend(ipn="1.1", node="1")
    ui = TestUI(backend)
    ui.run()


if __name__ == "__main__":
    main()
