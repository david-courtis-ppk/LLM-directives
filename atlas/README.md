# PreciseRx Codebase Atlas

The atlas is the user-facing reference for every PrecisePK repository. It is published as a private claude.ai artifact at <https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht>, and this folder is its only source. Read this file before changing the atlas.

Agents do not read the atlas for their own work. When a user asks where something is documented, look it up in [INDEX.md](INDEX.md) and give them the deep link.

## When to update it

Keep the atlas current. Whenever a change alters something the atlas describes, such as a route, a flow, a make target, a data shape, or a known issue, update the source in the same task and rebuild. When a listed issue is fixed, remove it from the issues page. The atlas describes `main`, so republish once the change is on `main`, or when the user asks.

## Layout

| Path | What it is |
| --- | --- |
| `src/NN-name.html` | Page fragments, concatenated in filename order. `00-head.html` holds the styles, header and sidebar shell. `99-tail.html` closes the page and holds the script. |
| `data/` | Inputs the build fills in: `contract.tsv` (the frontend endpoint table), `poly.txt` and `area.txt` (the header curve, produced by `curve.py`). |
| `build.py` | Assembles the page, runs the content checks, writes `dist/preciserx-atlas.html` and regenerates `INDEX.md`. |
| `INDEX.md` | Generated section index with anchors and one-line summaries. Never edit it by hand. |
| `dist/` | Build output. Gitignored. |

## Build and publish

```sh
python3 atlas/build.py
```

The build refuses to write the page if a check fails, and prints the reason. Then publish the built file to the **same** artifact URL, so existing links keep working. Pass the URL explicitly:

- Artifact tool: `action: "publish"`, `file_path: atlas/dist/preciserx-atlas.html`, `url: https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht`.
- Omit `icon` on republish. The artifact keeps its `map` icon.

Publishing without `url` creates a second artifact. Don't do that.

## Content rules

These rules are enforced where they can be. `build.py` fails on generation notes, provenance marks, secret-shaped strings, broken anchors, duplicate ids and unbalanced tags.

1. **Pure documentation.** State how the system works. Never say how the page was produced. Don't include provenance marks such as "verified" or "reported", disclaimers about method, "last checked" notes, or sentences about the atlas itself. Uncertainty about the *system* is content: write it into the sentence ("probably", "if Main rejects it") or list it under Open questions.
2. **Trace before writing.** Read the code before describing it. Never describe a function or file from memory. Every non-trivial claim carries a `path:line` in a `<span class="path">`.
3. **Human-reader style.** Open each section with a one- or two-sentence `summary`. Gloss internal shorthand on first use. Use one idea per sentence, and write bullets as complete sentences. Use tables when comparing three or more things.
4. **Maths.** Put a "where" list (`<dl>` inside `.eq`) under every equation. Keep one meaning per letter across the whole atlas. Add every symbol to the symbol index in `90-reference.html`.
5. **No secrets or identifiers.** Never include secret values, tokens, AWS account or VPC ids, ARNs, internal hostnames, customer names, or people's names. Refer to a secret by where it is stored, and to a person by role.
6. **Diagrams earn their place.** Draw a diagram only when it shows a mechanism faster than prose. Label every arrow. Use inline SVG with the `svg-*` classes for layouts, and `<pre class="mermaid">` for sequences. Mermaid text must not contain `;`, `#`, `<` or `&`.

## Conventions

- **Section markup.** A section is `<section class="doc" id="…" data-group="…" data-title="…">` with a `<header>` holding `.eyebrow`, `h2` and `.summary`. The sidebar and `INDEX.md` are built from `data-group`, `data-title` and every `h3[id]`, so give each `h3` a unique id.
- **Id prefixes per area.** Use `fe-` (frontend), `main-`, `db-` (Database), `dbr-` (Databridge), `an-` (Analytics), `genai-`, `pk-` (PK-Library), `x-` (cross-cutting), `issues-`. Ids must be unique across the page.
- **Groups.** The sidebar groups, in page order, are: Start here, Run it, Frontend (PreciseRx-Web), Backend services, Dosing engine, Shared libraries, Across the system, Known issues, Reference. Add a new file with a number that places it in the right group.
- **Components.** Reuse the ones defined in `00-head.html`: `.facts` (key-value strip), `.tbl` (tables; add `compact` for dense ones), `.note` (`warn`, `crit`, `info`), `.steps` (numbered procedures), `.issue` with severity `.pill high|med|low`, method pills `.pill get|post|put|patch|del`, `.eq` (equations), and `figure.diagram` (diagrams).
- **Endpoint table.** Add or change frontend calls in `data/contract.tsv` (tab-separated: file, function, method, service, path, note). Don't edit the HTML table.

## Last documented state

Update this table when you re-document a repository, so the next update knows where to diff from (`git log <commit>..HEAD`).

| Repository | Branch | Commit |
| --- | --- | --- |
| PreciseRx-Web | main | `c1d47c364` (RX-3699 sections also describe uncommitted work on branch `rx-3699-model-fit-demo`) |
| PreciseRx-Web-PK | main | `dade744b` |
| PreciseRx-Main | main | `16b95c2` |
| PreciseRx-Database | main | `41050ca5` |
| PreciseRx-Analytics | main | `a3ffc2f` |
| PreciseRx-Databridge | main | `ebe6524` |
| PreciseRx-GenAI | main | `1920cb0` (`feature/rx-2901` only skimmed) |
| PK-Library | main | `d19f42f3` |
| PreciseRx-Shared-JS | main | `f2abc46` |
| PreciseRx-Shared-Python | main | `62bcb86` |
