Order Pipeline Lab
A small ASP.NET Core 10 project for learning Git Flow, GitHub Actions, semantic versioning, Git tags, and Docker images in GHCR. No Jenkins, GitLab, or local .NET SDK is required to run CI.
Project structure
- src/OrderPipeline.Api: API (POST /orders/calculate, GET /health, GET /version)
- tests/OrderPipeline.UnitTests: xUnit tests
- .github/workflows/unit-tests.yml: validates PR policy, builds and runs tests
- .github/workflows/build-release.yml: calculates a version, builds and publishes an image, then creates a Git tag
- build/versioning.py: version calculator
- build/validate_pr.py: Git Flow PR policy
- deploy/compose.yaml: optional manual Docker deployment profiles (dev, staging, prod)
- docs/FLOW.md: detailed walkthrough of Git Flow
Branches and versions
Branch / action	Version example	Git tag
feature/* PR to develop	no release yet	none
push after merge to develop	0.1.0-dev.1	v0.1.0-dev.1
push to release/0.1.0	0.1.0-rc.1	v0.1.0-rc.1
merged release/0.1.0 PR into main	0.1.0	v0.1.0
merged hotfix/0.1.1 PR into main	0.1.1	v0.1.1


Use Conventional Commit PR titles such as feat: add discount, fix: correct rounding, or feat!: breaking change. Squash merge regular feature PRs into develop; use Create a merge commit for release PRs into main.

There is no automatic remote deployment in this lab. GitHub Actions publishes versioned Docker images to GHCR. The Compose file is for manual deployment. The stable image is rebuilt with its final version, not simply promoted from an RC image.
Run tests locally (if .NET 10 is installed)
dotnet restore OrderPipelineLab.sln
dotnet test OrderPipelineLab.sln -c Release
python3 -m unittest discover -s build/tests -p 'test_*.py' -v
Test the API
curl http://localhost:8080/health
curl http://localhost:8080/version
curl -X POST http://localhost:8080/orders/calculate \
  -H 'Content-Type: application/json' \
  -d '{"unitPrice":100,"quantity":2,"discountPercent":10}'
Build Docker locally (optional)
docker build -t order-pipeline-lab:local .
docker run --rm -p 8080:8080 order-pipeline-lab:local
Documentation
Read [`docs/FLOW.md`](docs/FLOW.md) for the PR → test → version → tag → GHCR process.