"""Apply reviewed process caps before invoking a configured Poppler binary."""

import os
import resource
import sys


def main() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    except (OSError, ValueError):
        sys.exit(78)
    os.execv(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
