# Agent Instructions & Guidelines

## Architecture & Coding Standards
- Follow established BeamNG.Earth conventions for L-level terrain, procedural roads, vegetation, and buildings.
- Maintain high-speed streaming stability and strict frame budgets (<16ms).
- Always validate changes with the parallel test runner: `python tools/parallel_tests.py -j 12`.

## Versioning, Building, and Publishing Releases
- **Always check current named version before building and publishing**:
  - Read `VERSION` in the workspace root.
  - Run `git fetch origin --tags; git fetch upstream --tags`.
  - Check existing releases: `gh release list --repo Madderose/BeamNG.Earth`.
  - Check upstream latest commits and tags (`upstream/main`).
- **Avoid Name Mistakes & CI/CD Collisions**:
  - Never attempt to create or publish a release using an existing tag/release name.
  - Be aware that pushing to `main` triggers `.github/workflows/release.yml`. Never publish a release via CLI under the same version while pushing to `main` at the same time to avoid race condition conflicts (`a release with the same tag name already exists`).
  - Use appropriate semantic versions and prerelease markers (`preview`, `alpha`, `beta`, `rc`, `experimental`).
- **Remotes**:
  - `origin`: personal fork (`Madderose/BeamNG.Earth`).
  - `upstream`: original repository (`TecnaGamer/BeamNG.Earth`).
