---
name: Map Codebase
description: "Analyze the current project and generate comprehensive codebase documentation in .planning/codebase/"
---

# Map Codebase Skill

This skill provides a standardized approach to documenting any project's codebase. When invoked, you should analyze the user's project structure, code, and configurations, and then generate 7 core architectural markdown files inside the `.planning/codebase/` directory.

## Instructions

1. **Analyze the Project:** 
   Thoroughly review the application's source code, directories, package manager configurations (e.g., `package.json`, `requirements.txt`, `pyproject.toml`), and any existing documentation. Pay special attention to:
   - Layers (Frontend, Backend, Database)
   - Data flows and API usage
   - UI components and state management
   - Core business logic and external integrations

2. **Create Output Directory:** 
   Ensure the directory `.planning/codebase/` exists in the root of the project. If it doesn't, create it.

3. **Generate Documentation Files:** 
   Create the following 7 files in `.planning/codebase/`. At the top of each file, include the analysis date in this format: `**Analysis Date:** YYYY-MM-DD`. Generate these files sequentially, ensuring high-quality, project-specific details in each.

   ### 1. `ARCHITECTURE.md`
   - **Pattern Overview:** The overall architecture pattern (e.g., Layered, Microservices, MVC, Client-Server).
   - **Layers:** Breakdown and purpose of Presentation, API, Business Logic, and Data layers.
   - **Data Flow:** Step-by-step description of how data moves through the application for key user journeys.
   - **Key Abstractions:** Core models, primary controllers, and state managers.
   - **Entry Points:** The main run scripts, server entry files, or UI mount points.
   - **Error Handling & Cross-Cutting Concerns:** General strategy for exception handling, logging, validation, and authentication.

   ### 2. `STRUCTURE.md`
   - **Directory Layout:** A complete tree representation of the codebase.
   - **Directory Purposes:** A brief explanation of what goes in each top-level and important sub-level folder.
   - **Key File Locations:** Important configuration setup files and core logic singletons.
   - **Naming Conventions:** Rules for files, directories, functions, and classes (e.g., `PascalCase.tsx`, `snake_case.py`).
   - **Where to Add New Code:** Clear guidelines for where to place new features, pages, API routes, or utility functions.
   - **Special Directories:** Mention virtual environments (`venv`), build output folders (`dist`, `.next`), and node modules (`node_modules`).

   ### 3. `CONCERNS.md`
   - **Known Issues:** Existing bugs, broken features, or current limitations.
   - **Technical Debt:** Areas needing refactoring, poor test coverage, or duplicated logic.
   - **Potential Improvements:** Suggestions for future architecture enhancements or performance optimizations.
   - **Open Questions:** Ambiguities in the codebase or unclear requirements.

   ### 4. `CONVENTIONS.md`
   - **Naming Patterns:** Case styles for variables, constants, and functions across different languages in the stack.
   - **Code Style:** Formatter expectations (e.g., Prettier, Black), linting setups, and import organization rules.
   - **Error Handling Patterns:** Typical Try/Catch strategies and how exceptions are bubbled up or presented to the user.
   - **Logging & Comments:** How application logs are recorded (Console vs File) and the standard for docstrings or inline comments.
   - **State Management & Function Design:** Rules on parameter types, return values, and global state (e.g., Zustand, Redux, standard Python Threading Locks).

   ### 5. `INTEGRATIONS.md`
   - **External Interfaces:** Third-party REST/GraphQL APIs used by the application.
   - **Services:** External databases (e.g., Postgres, SQLite), message queues, or cloud platforms (AWS, GCP).
   - **Third-party Tools:** System-level executable dependencies (e.g., `ffmpeg`, `yt-dlp`, image processors).

   ### 6. `STACK.md`
   - **Languages:** Primary and secondary programming languages.
   - **Runtime & Package Managers:** Specific environmental requirements (e.g., Node.js 18+, Python 3.10+, npm, pip).
   - **Frameworks:** Core libraries (e.g., FastAPI, Next.js, React).
   - **Key Dependencies:** Critical backend and frontend packages.
   - **Platform Requirements:** Supported Operating Systems.
   - **Application Modes:** Note if the application runs as a monolith, desktop app, or divided client/server.

   ### 7. `TESTING.md`
   - **Testing Frameworks:** Tools used (e.g., pytest, Jest, Cypress).
   - **Test Coverage & Strategies:** Unit testing vs integration testing expectations.
   - **Directory Locations:** Where to place test files (e.g., co-located with components vs inside a `tests/` directory).
   - **CI/CD:** Notes on any automated testing pipelines.

4. **Iterative Refinement:** After generating the 7 files, briefly review them to ensure no overlapping conflicting information exists and that they jointly summarize the entire project accurately.
