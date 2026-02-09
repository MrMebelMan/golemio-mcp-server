Analyze changes since the last git tag and recommend a version bump.

1. Find the latest git tag
2. Show the diff/commits since that tag
3. Analyze the changes and recommend a semver bump:
   - PATCH (0.0.x): bug fixes, CI/chore changes, documentation
   - MINOR (0.x.0): new features, backward-compatible changes
   - MAJOR (x.0.0): breaking changes
4. Update the version in pyproject.toml
5. Provide instructions to publish:
   - Commit the version bump
   - Push to origin
   - Create a GitHub release with `gh release create`

Do not push or create releases automatically - just give me the commands to run.
