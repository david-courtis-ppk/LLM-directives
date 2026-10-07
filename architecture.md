# PreciseRx architecture

PrecisePK is built from the `PreciseRx-Web` frontend and the `PreciseRx-Web-PK` umbrella repo. The umbrella holds the Main, Database, Analytics, Databridge and GenAI services, the PK-Library C++ engine, and the Shared-JS and Shared-Python packages as git submodules.

- **User-facing reference.** The PreciseRx Codebase Atlas is at <https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht>, and its source is `/Users/david/git/LLM-directives/atlas/`. Do not read it to do your own work; read the code instead.
- **Pointing the user to a section.** When the user asks where something is documented, or how part of the system works at a high level, look it up in `/Users/david/git/LLM-directives/atlas/INDEX.md` and reply with the deep link.
- **Keeping it current.** When a change you make alters something the atlas documents, update the atlas source in the same task and rebuild it, following `/Users/david/git/LLM-directives/atlas/README.md`. Republish to the same URL once the change is on `main`, or when the user asks.
- **Engineering guides.** Setup, git, frontend, PK-Library and platform guides live in `/Users/david/git/LLM-directives/guides/`. `style.md` says which guide to read for which task.
