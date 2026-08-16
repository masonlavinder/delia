# web_app — the phone UI

Client/server split. The server is a thin, unprivileged Flask process; the
client is a React SPA it serves as static files.

```
web_app/
├── server/          Flask — the control API + static host for the built client
│   ├── server.py    routes; talks to the renderer daemon via panel.client
│   ├── scenes.py    the BACKGROUNDS + OVERLAYS registry (add scenes here)
│   └── ai.py        optional: a typed sentence -> a pick from that registry
└── client/          React + TypeScript + Vite
    ├── src/
    │   ├── App.tsx          layout + status readout
    │   ├── usePanel.ts      all state: polling, optimistic scene switching
    │   ├── api.ts           typed wrapper over /api/*
    │   ├── components/      SceneButton, OverlayChip, AskBox, …
    │   ├── styles/          the design layer, ported from @knurled/kit
    │   │   ├── global.css   layer order + reset + base — import FIRST
    │   │   ├── tokens.css   custom properties only
    │   │   ├── fonts.css    self-hosted Geist, latin subset
    │   │   └── patterns.css chamfer, knurl, mono treatments
    │   └── styles.css       delia's own components layer
    └── dist/        build output — gitignored, rsynced to the Pi
```

**The server never derives a filesystem path from user input.** `/api/scene`
takes *names* and looks them up in `BACKGROUNDS` / `OVERLAYS`; the scene
document sent to the daemon is composed from layers we wrote. The daemon
re-validates it regardless — that re-check is what protects the device. See the
security model in `CLAUDE.md`.

## Responsibilities

| | server | client |
|---|---|---|
| Scene definitions (layer documents) | ✅ `scenes.py` | never sees them |
| Talking to the renderer daemon | ✅ Unix socket | ✅ via `/api/*` only |
| Which scenes exist | ✅ source of truth | renders whatever `/api/scenes` returns |
| Emoji / labels / layout | hint only (`SCENE_EMOJI`) | ✅ |
| Optimistic UI, polling, errors | — | ✅ `usePanel.ts` |

The client hardcodes no scene list. Adding a scene is a one-file change in
`server/scenes.py`; no rebuild of the client is needed.

## API

| | |
|---|---|
| `GET /api/backgrounds` | `{backgrounds: [{name, emoji}], current: string \| null}` |
| `GET /api/overlays` | `{overlays: [{name, emoji, params}]}` — `params` is the editable spec |
| `POST /api/scene` | `{background, overlays[], brightness?, color?}` → `{ok}`; `400` unknown name, `503` daemon down |
| `POST /api/brightness` | `{value}` (1–100) → `{ok}` |
| `POST /api/off` | `{ok}`; `503` daemon down |
| `GET /api/ai` | `{enabled, model}` — whether the ask box should exist |
| `POST /api/ai/scene` | `{prompt}` → the applied selection + `note`; `503` when disabled |

Any non-`/api/` path falls back to `index.html` (SPA shell). Unknown `/api/`
paths return JSON `404`, not HTML.

## Ask (optional)

`ai.py` turns "make it look like a thunderstorm" into a scene. It is a second
*front-end* to `compose()`, not a second way in:

- Claude only ever **picks from the registry**. The JSON Schema it must answer
  in is derived from `list_backgrounds()` / `list_overlays()` at call time, so
  its vocabulary tracks `scenes.py` automatically — add a background there and
  it can use it, no rebuild, same as the client.
- Each overlay gets its own param shape from `_params_for`, so the model can't
  set `x` on `label` (a scroll layer has no `x`, and the daemon would reject
  the whole scene for it).
- Numbers are clamped and hex is parsed in `_to_request` before anything is
  composed — JSON Schema can't express `minimum`, so one silly coordinate
  can't sink a scene.
- The result goes through the same `_apply()` as a button tap, and the daemon
  re-validates it like anything else. The model is just another untrusted
  client of the socket.

Off by default. Give the server a key and restart:

```bash
# on the Pi
printf 'ANTHROPIC_API_KEY=sk-ant-...\n' > ~/delia/.env && chmod 600 ~/delia/.env
sudo pip3 install --break-system-packages anthropic
sudo systemctl restart panel-api
```

`.env` is gitignored *and* rsync-excluded — the Pi owns its own copy. With no
key, `/api/ai` reports `enabled: false`; the box is still rendered but disabled,
saying so in its placeholder — a control that explains why it's dead beats one
that silently isn't there.

Tunables (same `.env`): `PANEL_AI_MODEL` (default `claude-opus-5`;
`claude-haiku-4-5` is faster and cheaper), `PANEL_AI_EFFORT` (default `low`),
`PANEL_AI_TIMEOUT`.

## Styling

delia follows the Knurled Studio design system. The rules are in `KNURLED.md`
in that repo; the short version is chamfers instead of rounded corners, no
faked light (no gradients, shadows or glows — depth is hairline borders and
flat surface steps), colour only from a custom property, durations from
`--dur-*`, one grain direction at 45°, dark only.

The token layer is **vendored, not depended on** — delia is a separate repo
that deploys by rsync to a Pi, so a `@knurled/kit` workspace dependency has
nowhere to resolve from. `src/styles/` is a copy; keep it in step with
`packages/kit/src/` by hand, the same trade the studio already makes for
`favicon.svg` and `og.png`.

Import order in `main.tsx` is load-bearing: **`global.css` first.** A layer
takes its position from wherever its name first appears, so any `@layer` block
emitted ahead of the declaration is pinned where it lands and the declared
order silently stops applying.

Two deliberate deviations from the studio, both because delia's client is
plain CSS rather than CSS Modules:

- **Patterns are class names in JSX.** The studio reaches them only through
  `composes:` and never writes them into markup. Honouring that here means
  converting every component to CSS Modules — an architecture change, not a
  restyle. Worth doing if delia's UI grows.
- **The chamfer is one element, not two.** The studio pairs a shell that paints
  the edge with a face inset 1px that paints the surface, because `clip-path`
  clips a border. Here the element's own background is the shell and a
  `::before` is the face, so a `<button>` needs no wrapper. Same polygon, same
  1px inset. An `<input>` can't carry a `::before`, so the ask box keeps the
  wrapper.

Plus three delia-local tokens, flagged as such at the bottom of `tokens.css`:
`--panel-max` (a grid of scene tiles is not a page of prose), `--hit` (44px —
a thumb in a dark room), and `--text-field` (16px, or iOS zooms the page on
focus; the studio's `--text-base` is 15px).

**The second hue is data-driven.** Verdigris means "leaves the studio", so in
delia it marks exactly one thing: an overlay that fetches over the network.
`/api/overlays` reports `dynamic` per overlay, so which ones those are stays
declared beside the overlay in `scenes.py` rather than as a hardcoded
`name === 'weather'` in the client.

The studio's stylelint config is the enforcement, and it runs against delia
with no dependency here:

```bash
cd ../knurled-studio    # wherever it lives
npx stylelint --config packages/stylelint-config/index.js \
  "$OLDPWD/web_app/client/src/**/*.css"
```

Adding stylelint to delia proper would make that a build failure rather than a
thing to remember. Not done — it is a dependency, and KNURLED.md says ask.

## Develop

Two terminals. Vite serves the client with HMR and proxies `/api` to a real
Flask instance, so you develop against the actual daemon:

```bash
# 1. the API (on the Pi, or locally against a running daemon)
python3 web_app/server/server.py

# 2. the client — opens on :5173, reachable from your phone (host: true)
cd web_app/client && npm install && npm run dev
```

The proxy target defaults to `http://delia-pi.local:8080`. Override it:

```bash
PANEL_API=http://localhost:8080 npm run dev
```

`npm run build` runs `tsc -b` first, so type errors fail the build.

## Deploy

Use `./deploy.sh` at the repo root:

```bash
./deploy.sh            # build client, push everything, restart both services
./deploy.sh client     # build + push dist/ only — no restart needed
./deploy.sh api        # push server/ + restart panel-api
./deploy.sh -n         # dry run: show what would change, touch nothing
```

**Client-only changes need no service restart** — Flask reads `dist/` off disk
per request, so `./deploy.sh client` is the fast loop.

**Build on your laptop, not the Pi** — the Pi 3 A+ has 512 MB, the same reason
the matrix library is built with `LTO_FLAGS=`. `dist/` is gitignored but *is*
rsynced; the Pi needs no Node.js. If you forget to build, the server returns a
plain-text `503` saying so rather than a blank page.

The client push uses `rsync --delete` on purpose: asset filenames are
content-hashed, so without it every build leaves its predecessors behind.
