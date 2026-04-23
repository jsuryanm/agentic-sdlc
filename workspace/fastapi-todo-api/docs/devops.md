# DevOps Report - fastapi-todo-api

## Purpose
This report outlines the current status and outcomes of the DevOps phase for the fastapi-todo-api project, focusing on deployment readiness and CI/CD processes.

## Inputs
- Dockerfile for containerization
- CI configuration file (ci_yaml) for continuous integration
- Project repository and codebase
- Testing results from pytest

## Outputs
- Successfully built Docker image for deployment
- CI pipeline configured to run tests and build the application
- Documentation for future contributions and understanding

## Key decisions
- Utilized FastAPI for API development due to its performance and ease of use.
- Chose Docker for containerization to ensure consistent deployment across environments.
- Implemented GitHub Actions for CI to automate testing and building processes.

## Risks and open questions
- Finalization of the database schema is pending, which may affect deployment and functionality.
- Selection of authentication methods is still under discussion, impacting security and user access.
- Potential issues with scaling and performance under load have not been fully addressed.

## Next steps
- Finalize the database schema and authentication methods to enhance security and functionality.
- Conduct further testing, especially focusing on edge cases and performance under load.
- Prepare for deployment to production and monitor for any issues post-launch.