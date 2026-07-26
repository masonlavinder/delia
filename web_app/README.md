# web_app — the phone UI

Client/server split. The server is a thin, unprivileged Flask process; the
client is a React SPA it serves as static files.

```
web_app/
├── server/          Flask — the control API + static host for the built client
│   ├── server.py    routes; talks to the renderer daemon via panel.client
│   └── scenes.py    the built-in scene documents (add scenes here)
└── client/          React + TypeScript + Vite
    ├── src/
    │   ├── App.tsx          layout + status line
    │   ├── usePanel.ts      all state: polling, optimistic scene switching
    │   ├── api.ts           typed wrapper over /api/*
    │   ├── components/      SceneButton, OffButton
    │   └── styles.css
    └── dist/        build output — gitignored, rsynced to the Pi
```

**The server never derives a filesystem path from user input.** `/api/scene`
takes a *name* and looks it up in `SCENES`; the scene document sent to the
daemon is one we wrote. The daemon re-validates it regardless — that re-check is
what protects the device. See the security model in `CLAUDE.md`.

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
| `GET /api/scenes` | `{scenes: [{name, emoji}], current: string \| null}` |
| `POST /api/scene` | `{name}` → `{ok}`; `400` unknown scene, `503` daemon down |
| `POST /api/off` | `{ok}`; `503` daemon down |

Any non-`/api/` path falls back to `index.html` (SPA shell). Unknown `/api/`
paths return JSON `404`, not HTML.

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
