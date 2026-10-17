# Release checklist

This package is prepared locally. Publishing remains a separate action.

- [ ] Confirm the intended GitHub owner, repository name and visibility.
- [ ] Review the proposed MIT license and author credit.
- [ ] Review the source, examples and documentation; include only synthetic/public-safe material.
- [ ] Run `python3 -m unittest discover -s tests -v` and both README demo commands.
- [ ] Confirm that timezone and input-trust limitations are acceptable.
- [ ] Create/push the remote only after explicit publication approval.
- [ ] Read the exact remote back: owner, visibility, default branch, README, license and files.
- [ ] Do not claim GitHub Actions passed unless an actual remote run was checked.

No credentials, production data or local `.git` history are needed to use the source archive.
