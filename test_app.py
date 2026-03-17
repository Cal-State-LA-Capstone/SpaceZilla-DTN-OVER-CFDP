from backend.test_backend import TestBackend
from frontend.test_frontend import TestUI


def main():
    backend = TestBackend(ipn="1.1", node="1")
    ui = TestUI(backend)
    ui.run()


if __name__ == "__main__":
    main()
