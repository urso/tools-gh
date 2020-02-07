from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

from . import gqlobj


def connect(token_file):
    with open(token_file) as f:
        token = f.read().strip()

    return Client(
        transport=RequestsHTTPTransport(
            url='https://api.github.com/graphql',
            use_json=True,
            headers={
                "Authorization": "bearer {}".format(token),
                "Accept": ",".join([
                    "application/vnd.github.starfire-preview+json",
                    "application/vnd.github.shadow-cat-preview+json",
                ]),
            },
        ),
        # fetch_schema_from_transport=True,
    )


def client(token_file):
    return APIClient(connect(token_file))


GHAPI = gqlobj.MakeClass('GHAPI', """
    query viewer_login { viewer { login } }

    mutation pr_create($input: CreatePullRequestInput!) {
        createPullRequest(input:$input) {
            clientMutationId
            pullRequest {
                ... prCommon
                id
                headRefName
            }
        }
    }

    mutation add_labels($input: AddLabelsToLabelableInput!) {
        addLabelsToLabelable(input:$input) {
            clientMutationId
        }
    }

    query repo_id($user: String!, $name: String!) {
        repository(owner:$user, name:$name) {
            id
        }
    }

    query repo_pr_id(
        $user: String!,
        $repo: String!,
        $number: Int!,
    ) {
        repository(owner:$user, name:$repo) {
            pullRequest(number: $number) {
                id
            }
        }
    }

    query repo_label_ids(
          $count: Int!,
          $user: String!,
          $repo: String!,
          $query: String!,
          $cursor: String
    ) {
        repository(owner:$user, name:$repo) {
            labels(first:$count, after:$cursor, query:$query) {
                edges {
                    cursor
                    node {
                        id
                        name
                    }
                }
            }
        }
    }

    query pr_info($user: String!, $name: String!, $pr: Int!) {
        repository(owner:$user, name:$name) {
            pullRequest(number:$pr) {
                ... prCommon
                ... prCrossReferences
                headRefName
                bodyText
                commits(last:1) {
                    nodes {
                        commit {
                            status {
                                state
                                contexts {
                                    context
                                    state
                                    targetUrl
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    query issue_info($user: String!, $name: String!, $num: Int!) {
        repository(owner:$user, name:$name) {
            issue(number:$num) {
                ... issueCommon
                ... issueCrossReferences
                bodyText
            }
        }
    }

    query branch_prs($user: String!, $name: String!, $ref: String!) {
        repository(owner:$user, name:$name) {
            ref(qualifiedName:$ref) {
                associatedPullRequests(last:20) {
                    nodes {
                        number
                        title
                        permalink
                    }
                }
            }
        }
    }

    query iter_list_issues(
        $count: Int!,
        $user: String!,
        $name: String!,
        $labels: [String!],
        $states: [IssueState!],
        $filter: IssueFilters,
        $cursor: String
    ) {
      repository(owner:$user, name:$name) {
        issues(first:$count, after:$cursor, labels:$labels, states:$states, filterBy: $filter) {
          edges {
            cursor
            node {
              author {
                login
              }
              createdAt
              updatedAt
              number
              state
              title

              labels(first:20) {
                nodes { name }
              }
              participants(first:20) {
                nodes { login }
              }
              projectCards(first:20) {
                nodes {
                  state
                  project {
                    name
                  }
                  column {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }

    query iter_branch_prs(
          $count: Int!,
          $user: String!,
          $repo: String!,
          $cursor: String
    ) {
        repository(owner:$user, name:$repo) {
          refs(first:$count, after:$cursor, refPrefix:"refs/heads/") {
              edges {
                cursor
                node {
                  id
                  name
                  associatedPullRequests(first:5) {
                      nodes {
                          number
                          state
                      }
                  }
                }
              }
          }
        }
    }

    query user_prs(
        $count: Int!,
        $user: String!,
        $states: [PullRequestState!],
        $labels: [String!],
        $cursor: String)
    {
        user(login:$user) {
            ...collectPRs
        }
    }

    query user_issues_search(
        $count:Int!,
        $query:String!,
        $cursor:String
    ) {
        search(first:$count, after:$cursor, query:$query, type:ISSUE) {
            edges {
                cursor
                node {
                   ... on Issue {
                      ...issueCommon
                      ...issueCrossReferences
                      createdAt
                      updatedAt
                      repository {
                        owner { login }
                        name
                      }
                      participants(first:20) {
                        nodes { login }
                      }
                      projectCards(first:20) {
                        nodes {
                          state
                          project {
                            name
                          }
                          column {
                            name
                          }
                        }
                      }
                   }
                }
            }
        }
    }

    query user_prs_search(
        $count:Int!,
        $query:String!,
        $cursor:String
    ) {
        search(first:$count, after:$cursor, query:$query, type:ISSUE) {
            edges {
                cursor
                node {
                   ... on PullRequest {
                      ...prCommon
                      ...prCrossReferences
                      createdAt
                      updatedAt
                      repository {
                        owner { login }
                        name
                      }
                      participants(first:20) {
                        nodes { login }
                      }
                      projectCards(first:20) {
                        nodes {
                          state
                          project {
                            name
                          }
                          column {
                            name
                          }
                        }
                      }
                   }
                }
            }
        }
    }

    query commit_prs($user: String!, $name: String!,$commitID: GitObjectID!) {
        repository(owner:$user, name:$name) {
            object(oid:$commitID) {
                ... on Commit {
                    associatedPullRequests(last:20) {
                        nodes {
                            number
                            title
                            permalink
                        }
                    }
                }
            }
        }
    }

    fragment collectPRs on User {
        pullRequests(first:$count,after:$cursor,labels:$labels,states:$states) {
            edges {
                cursor
                node {
                    author { login }
                    number
                    state
                    headRefName
                    title
                    repository {
                        name
                        owner { login }
                    }
                    permalink
                    lastEditedAt
                    mergeable
                    labels(first:20) {
                        nodes { name }
                    }
                }
            }
        }
    }

    fragment issueCommon on Issue {
        author { login }
        number
        title
        state
        labels(first:20) {
            nodes { name }
        }
    }

    fragment prCommon on PullRequest {
        author { login }
        number
        title
        permalink
        state
        mergeable
        headRefName
        labels(first:20) {
            nodes { name }
        }
        mergeCommit {
            committedDate
            oid
        }
        reviews(last:20,states:[APPROVED,CHANGES_REQUESTED,DISMISSED]) {
            nodes {
                author { login }
                createdAt
                state
            }
        }
    }

    fragment issueCrossReferences on Issue {
        timelineItems(itemTypes:[CROSS_REFERENCED_EVENT],first:20) {
            nodes {
                __typename
                ... on CrossReferencedEvent {
                    source {
                        __typename
                        ... on Issue {
                            ... issueCommon
                            repository {
                                owner { login }
                                name
                            }
                        }
                        ... on PullRequest {
                            ... prCommon
                        }
                    }
                }
            }
        }
    }

    fragment prCrossReferences on PullRequest {
        timelineItems(itemTypes:[CROSS_REFERENCED_EVENT],first:20) {
            nodes {
                __typename
                ... on CrossReferencedEvent {
                    source {
                        __typename
                        ... on Issue {
                            ... issueCommon
                            repository {
                                owner { login }
                                name
                            }
                        }
                        ... on PullRequest {
                            ... prCommon
                        }
                    }
                }
            }
        }
    }
""")


class APIClient(GHAPI):
    def __init__(self, *args, **kwargs):
        super(APIClient, self).__init__(*args, **kwargs)


def iter_gql(fn, key, *args, **kwargs):
    keys = key.split(".")
    while True:
        cur = fn(*args, **kwargs)
        for key in keys:
            if not key in cur:
                return
            cur = cur[key]

        if not cur:
            return

        for obj in cur:
            kwargs['cursor'] = obj['cursor']
            yield(obj['node'])
