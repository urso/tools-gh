# github helper scripts

## Setup

All code requires python3.7. It's best to setup a virtualenv:

```bash
$ virtualenv -p python3.7 env
$ source ./env/bin/activate
$ pip install .
```

## Examples

Delete local and remote branches for merged PRs

```bash
$ gh branches prune_merged
```

Show github issue state and cross references (multiple IDS can be given):

```bash
# based on full URL
$ gh issue info <FULL URL> ...

# github owner/repo and ID
$ gh issue info <owner>/<repo>#<id> ...

# access issue in github repo matching current git repository
$ gh issue info <id> ...
```

Show a github users PRs

```bash
# all my open PRs
gh pr userlist

# all PRs of user X
gh pr userlist --states all X
```

Print PR details like state, link, message and cross references to issues and other PRs:

```bash
# Github PR for current branch
gh pr info

# PR 12345 in fork matching git remote X
gh pr info --remote X 12345
```

Find PR based on commit hash

```bash
$ gh pr of <commit hash>
```

Create PR (opens editor for writing the message):

```bash
# create PR against upstream master based on current branch
$ gh pr create

# create PR against "custom" branch
$ gh pr create --branch custom
```

Open PR for current branch in github:

```bash
$ gh pr open
```
