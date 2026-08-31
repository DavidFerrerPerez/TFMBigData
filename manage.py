import subprocess
import sys


SERVICE_NAME = "app"


def build():
    subprocess.run(
        ["docker", "compose", "build"],
        check=True,
    )


def bash():
    subprocess.run(
            ["docker", "compose", "up", "-d"],
            check=True,
        )
    
    subprocess.run(
        ["docker", "compose", "exec", SERVICE_NAME, "/bin/bash"],
        check=True,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage.py build")
        print("  python manage.py bash")
        sys.exit(1)

    command = sys.argv[1]

    if command == "build":
        build()

    elif command == "bash":
        bash()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: build, bash")
        sys.exit(1)


if __name__ == "__main__":
    main()