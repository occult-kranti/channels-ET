# Exact-commit publication through the GitHub Git-data API

The native Git upload endpoint returned HTTP 503 after GitHub authentication had
been restored. The supported GitHub API remained reachable. This helper uploaded
immutable blobs, reconstructed the same tree and commit, checked every returned
Git object ID, then updated `main` without force. Remote commit
`0a20688c500ec6b0761f28340590c6beee58941e` exactly matches the local commit;
Pages Action `40048661028` succeeded and the actual live site passed 58 route
checks. See the dated deployment receipts in `research/youtube-access/deployment/`.

The implementation uses the official [Git database API](https://docs.github.com/en/rest/git),
the installed `gh` CLI and its existing authentication. It preserves the normal
HTTPS proxy/TLS configuration. It never reads credential values, changes local
history, rewrites origins or forces the branch. A failed blob request was resumed
serially after the other 93 returned object IDs had been verified; all 94 objects
were ultimately confirmed. Unreferenced uploaded objects do not update the branch.
`executed-0a20688.py` retains the byte-exact executed version for the dated
transport receipt. The current `publish_git_objects.py` incorporates the later
independent review's receipt-preservation fix and is the command documented below.

From this cloud checkout:

```sh
python3 research/git-api-publish/publish_git_objects.py --commit HEAD
# Explicit, already-authorized publication:
python3 research/git-api-publish/publish_git_objects.py --commit HEAD --publish
```

The default is offline inspection. The publication command supports a standard
single-parent unsigned commit with ordinary files, at most four API workers and
an 8 MiB bound per changed blob. It requires the remote branch to equal the local
parent before publication and rechecks that condition before the non-forced ref
update. A different tree or commit hash stops the update. An API failure records
whether a ref write was attempted; inspect the remote ref before retrying.
Offline inspection creates or overwrites no publication receipt. An existing
publication ledger requires `--resume`; a completed receipt is preserved even
when the remote branch already contains the exact commit.

Use `--resume --workers 1` only with the existing matching receipt under
`/workspace/setup-validation/`. It skips previously verified immutable objects;
the final tree, commit and branch checks still run. This is a fallback transport
for the explicitly authorized repository publication, separate from source-media
acquisition and scientific analysis.
