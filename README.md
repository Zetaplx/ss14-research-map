# SS14 Research Map

An interactive GitHub Pages view of research technologies, direct prerequisites, costs, and recipe unlocks.

## Update model

The `source/` submodule tracks `Zetaplx/SS14-Persistence` on its `master` branch. GitHub Actions refreshes it every six hours, rebuilds the page from the three research prototype folders, and deploys the result. Pushes to this project and manual workflow runs also rebuild the site.

The workflow commits a changed submodule pointer back to `main`, so the repository records the source revision used for the published map. The source checkout is sparse and shallow; only research prototypes and their English localization files are included in the Actions workspace.

## Local build

```powershell
python -m pip install -r requirements.txt
git submodule update --init --remote
python build.py source/Resources
```

The generated page is `dist/index.html`.
