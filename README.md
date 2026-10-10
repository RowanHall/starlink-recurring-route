# Starlink Performance on a Moving Vehicle

Project website for our CSC 466 research project at the University of Victoria.

**Authors:** Jasper McLennan (V01014572) · Rowan Hall (V01041357)

A static, single-page site (plain HTML/CSS, no build step) summarizing the project
proposal: studying LEO satellite (Starlink) network performance on a moving vehicle,
using a ~1.5-year measurement dataset from a school bus on a repeated daily route.

## Files

- `index.html` — the page content
- `style.css` — styles
- `.nojekyll` — tells GitHub Pages to serve files as-is (no Jekyll processing)

## Preview locally

Just open `index.html` in a browser, or serve the folder:

```sh
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Deploy to GitHub Pages

1. Create a GitHub repo and push these files to the `main` branch.
2. In the repo: **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*.
4. Choose branch `main` and folder `/ (root)`, then **Save**.
5. The site goes live at `https://<username>.github.io/<repo>/` within a minute or two.

```sh
git init
git add .
git commit -m "Add project website"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```
