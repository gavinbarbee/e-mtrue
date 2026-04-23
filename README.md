# E-Mtrue

**First-principles rocket physics verification.**

Live demo: **[https://e-mtrue.onrender.com](https://e-mtrue.onrender.com)**

A clean, SpaceX-inspired tool that enforces mathematical truth on rocket designs instead of blindly trusting simulator outputs.

### Why "E-Mtrue"?

The name is a direct nod to the early days of computing. In the 1940s, John Mauchly and J. Presper Eckert built ENIAC — the world’s first electronic general-purpose computer — specifically to compute ballistic firing tables using real physics instead of slow manual methods. **E-Mtrue** stands for **Electronic Mauchly-true**: a modern system built to enforce physics truth on complex engineering problems.

### My Philosophy

I strongly agree with Elon Musk’s first-principles approach — what I call his “algorithm type philosophy.” Boil every problem down to the most fundamental truths and reason up from there, rather than reasoning by analogy or following convention. This project is my practical attempt to apply that exact philosophy to rocket design verification.

### The Spark

When I saw the news that SpaceX had the rights to acquire Cursor, I decided it was the perfect moment to use the same AI-native tool they’re investing in to build something meaningful. E-Mtrue is the result — a demonstration of first-principles thinking applied to real rocket engineering.

### What It Does

You input basic rocket parameters. E-Mtrue runs independent first-principles calculations (not relying on any simulator) and clearly shows where the design aligns with physics versus where it diverges. The dashboard also features rotating authentic Elon first-principles quotes.

### Core Features (MVP)

- Minimal 6-field input form with smart defaults
- Independent calculations using SymPy + SciPy/NumPy:
  - Barrowman stability margin
  - Numerical trajectory integration (apogee & max velocity)
  - Energy balance sanity check
- Clear simulator vs. physics comparison with mismatch percentages
- Prominent E-Mtrue verdict (PASS / WARN / FAIL)
- Physics-based fix suggestions
- Sleek, dark SpaceX-style dashboard with real Elon first-principles quotes

### Tech Stack

- Flask (Python)
- SymPy + SciPy/NumPy
- Docker + Gunicorn
- Tailwind CSS

### Run Locally

```bash
docker compose build
docker compose up -d
```
Open: http://localhost:8000

### Future Iterations

- idiot Index (cost-reduction suggestions for materials and design)
- Regulatory feasibility checker
- OpenRocket .ork file import
- Charts + PDF reports

Built with unrelenting ambition and first-principles thinking.
  — Gavin Barbee
Aspiring to contribute to teams pushing the boundaries of what’s physically possible.
text
