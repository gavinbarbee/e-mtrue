# E-Mtrue

**First-principles rocket physics verification.**

A clean, SpaceX-inspired tool that enforces mathematical truth on rocket designs instead of blindly trusting simulator outputs.

### Why "E-Mtrue"?

The name is a nod to the early days of computing. In the 1940s, John Mauchly and J. Presper Eckert built ENIAC — the world’s first electronic general-purpose computer — specifically to compute ballistic firing tables using real physics instead of slow manual methods. E-Mtrue continues that spirit: **Electronic Mauchly-true** — a modern system that enforces physics truth on complex engineering problems.

### My Philosophy

I deeply agree with Elon Musk’s first-principles approach: boil problems down to the most fundamental truths and reason up from there, rather than reasoning by analogy or tradition. This project is my attempt to apply that exact mindset to rocket design verification.

### The Spark

When I saw the news that SpaceX had obtained the rights to aquire Cursor, I decided it was the perfect moment to use the same AI-native tool they’re investing in to build something meaningful. E-Mtrue is the result: a practical demonstration of first-principles thinking applied to real rocket engineering.

### What It Does

You input basic rocket parameters. E-Mtrue runs independent first-principles calculations (not relying on any simulator) and clearly shows where the design aligns with physics versus where it diverges.

### Core Features (MVP)

- Minimal 6-field input form with smart defaults
- Independent calculations using SymPy + SciPy/NumPy:
  - Barrowman stability margin
  - Numerical trajectory integration (apogee & max velocity)
  - Energy balance sanity check
- Clear simulator vs. physics comparison with mismatch percentages
- Prominent E-Mtrue verdict (PASS / WARN / FAIL) with explanation
- Physics-based fix suggestions
- Sleek, dark SpaceX-style dashboard with authentic Elon first-principles quotes

### Tech Stack

- Flask (Python)
- SymPy + SciPy/NumPy
- Docker + Gunicorn
- Tailwind CSS

### Run Locally

```bash
docker compose build
docker compose up -d
