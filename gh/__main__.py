import argparse
import os

from clidec import root, argument, with_commands

from . import branches
from . import issues
from . import pr
from . import user


default_token_file = os.path.expanduser("~/.elastic/github.token")


main = root(
        argument("--token", default=default_token_file, help='token file'),
        with_commands(
            branches.ns,
            issues.ns,
            pr.ns,
            user.ns,
        ),
)


if __name__ == '__main__':
    main()
