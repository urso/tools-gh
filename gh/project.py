import git
import re


class Project:
    def __init__(self, repo, remote=None):
        remotes = ['upstream', 'origin']
        if remote:
            remotes = [remote]

        def find_remote(remotes, names):
            for name in names:
                for remote in remotes:
                    if remote.name == name:
                        return remote
            return None

        remote = find_remote(repo.remotes, remotes)
        if not remote:
            raise f"remotes do not exist: {remotes}"

        self.repo = repo
        self.remote = remote

        self.user, self.name = github_url_owner(remote.url)

    @property
    def origin(self):
        return self.repo.remotes['origin']

    @property
    def upstream(self):
        if 'upstream' in self.repo.remotes:
            return self.repo.remotes['upstream']

    @property
    def active_branch(self):
        return self.repo.head.ref

    def has_remote(self, name):
        try:
            self.repo.remote(name)
            return True
        except:
            return False

    def repo_owner(self, remote_name):
        r = self.repo.remote(remote_name)
        return github_url_owner(r.url)

    def worktrees(self):
        heads = dict((h.path, h) for h in self.repo.heads)
        output = self.repo.git.worktree("list", "--porcelain")
        lines = [l for l in output.splitlines() if len(l) > 0]
        worktrees = []
        while lines:
            [wd, _commit_id, br, *lines] = lines
            if not wd.startswith('worktree '):
                raise "expected worktree name"
            if not br.startswith('branch '):
                raise "expected branch name"
            wd = wd[len("worktree "):]
            br = br[len("branch "):]
            if br not in heads:
                continue
            br = heads[br]
            worktrees.append(Worktree(self.repo, wd, br))
        return worktrees


class Worktree:
    def __init__(self, repo, path, branch):
        self._repo = repo
        self.path = path
        self.branch = branch

    def remove(self):
        self._repo.git.worktree("remove", self.path)


class Remote:
    def __init__(self, ref):
        self._obj = ref


def open(path=None, **kwargs):
    if not path:
        path = os.path.curdir
    return Project(open_repo(path), **kwargs)


def open_repo(path):
    return git.Repo(path, search_parent_directories=True)


def github_url_owner(url):
    match = re.search('github.com[/:](?P<user>.*)/(?P<repo>[^\.]*)(.git)?$', url)
    return match.group('user'), match.group('repo')
