# AGENTS.md

## Project

`android-dev-flow-toolkit` is a reusable automation toolkit for Android and Gradle
development workflows.

## Current Agenda

- Build a practical interactive CLI for Android teams.
- Prioritize feature development, testing, and debugging flows.
- Support three common Android environments:
  - develop/debug
  - staging/debug
  - production/debug
- Support emulator and physical device workflows.
- Support ADB over Wi-Fi later.
- Keep the toolkit reusable outside the original RefahDpi project.
- Prepare the project to be published on GitHub.

## Known Context

- The original motivating project is `RefahDpi`.
- RefahDpi has an app module named `app`.
- RefahDpi uses Gradle variants:
  - `developDebug`
  - `stagingDebug`
  - `productionDebug`
- A broad Gradle task like `assembleDebug` builds all debug variants in that
  project, so this toolkit should prefer exact variant tasks such as
  `:app:assembleDevelopDebug`.
- Developers may use mixed operating systems, so reusable logic should be
  written in Python rather than Bash when possible.
- Some team members share generated APKs manually through company folders or
  messengers, so the toolkit should make finding and packaging APKs easy.
- The company uses a self-hosted GitLab instance; GitLab automation is planned
  but not part of the first implementation step.

## Engineering Direction

- Use Python 3.10+ and the standard library first.
- Avoid hardcoded local machine paths.
- Prefer project config files over assumptions.
- Keep commands explicit and inspectable.
- Build small, testable modules for:
  - config loading
  - Gradle wrapper execution
  - ADB/device discovery
  - emulator discovery/startup
  - APK metadata parsing
  - interactive menus
- Do not add network dependencies until packaging and GitHub distribution are
  ready.

## Safety

- Do not delete, reset, or clean user repositories automatically.
- Do not run release tasks unless explicitly requested.
- Do not use `--refresh-dependencies` by default.
- Do not guess production release behavior from debug workflows.
