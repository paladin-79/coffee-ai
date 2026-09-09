# Frontend — Next.js + TypeScript + Tailwind

A thin client. It renders the chat, counts what the backend tells it to count,
and holds no authority over game state.

## Structure

| Path | Contents |
|---|---|
| `app/page.tsx` | Landing page — the ten-second pitch and a START button |
| `app/play/page.tsx` | Chat interface |
| `components/` | `ChatWindow`, `MessageBubble`, `AttemptCounter`, `Timer`, `SuccessModal`, `Leaderboard` |
| `lib/api.ts` | Typed client for the backend |

## Rules that hold across sprints

**The bundle must not contain challenge answers.** No target string, no
forbidden list, no solution paths. Everything comes from `GET /api/challenge`,
which returns only the `public` block. Anyone can read a JS bundle.

**The displayed timer is cosmetic.** It exists so the player feels the clock.
The score uses the backend's elapsed time, always.

**Design for a phone on event wifi.** Players arrive by QR code on mobile, on a
network under load. Optimistic UI, visible retry, honest timeouts.

## Local development

```bash
npm install
npm run dev
```
