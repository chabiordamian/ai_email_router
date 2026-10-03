from urllib.request import urlopen


def main() -> None:
    with urlopen("http://localhost:8000/health", timeout=5):
        pass


if __name__ == "__main__":
    main()
