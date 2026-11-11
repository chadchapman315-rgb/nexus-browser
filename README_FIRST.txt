NEXUS Browser - Render Deployment Package
========================================
This package contains the backend AND the Chromebook-friendly frontend.

PART 1: UPLOAD TO GITHUB
1. Open https://github.com/new and sign in (create an account if necessary).
2. Repository name: nexus-browser
3. Choose Public (or Private if your Render plan supports it), then click Create repository.
4. On the new repository page select 'uploading an existing file', or Add file > Upload files.
5. EXTRACT THIS ZIP FIRST. Upload the FOUR individual files in this folder:
   index.html, app.py, requirements.txt, render.yaml
   They must be in the repository's TOP LEVEL, not inside a folder or ZIP.
6. Click Commit changes.

PART 2: DEPLOY ON RENDER
1. Go to https://dashboard.render.com/ and sign in.
2. Choose New > Blueprint.
3. Connect GitHub if prompted. Select your nexus-browser repository.
4. Render should detect render.yaml. Review the web service and confirm deployment.
5. After successful deployment, copy the HTTPS URL displayed for the service.
   Example only: https://nexus-browser-reader.onrender.com
6. Open the URL and check the NEXUS homepage appears.
   To check the server health, append /health. You should see JSON with ok:true.

PART 3: USE FROM YOUR CHROMEBOOK
Option A (simplest): Open the Render HTTPS URL directly.
Option B (local HTML): Extract this ZIP on your Chromebook, open index.html,
  expand 'Backend settings', paste the Render HTTPS URL, press Save,
  then try a search or read a public webpage.

LIMITATIONS
- Search currently uses Wikipedia's topic search, not the entire internet.
- Reader mode extracts content from supported public HTML pages. It is NOT
  a full Opera-style browser and cannot run Google, YouTube, games, logins,
  shopping carts, or all interactive websites inside the NEXUS window.
- Requires internet. Your Render deployment may have limits and idle delays.
- If Render changes its free plan, you may need a different host or plan.
- Never enter passwords or sensitive information into Reader mode.

TROUBLESHOOTING
- Render says it can't find render.yaml: upload the files individually to
  your GitHub repository's root, not a subfolder.
- Render service fails to build: inspect Render deploy logs; requirements.txt
  should be at the repo root alongside app.py.
- Local HTML says backend missing: enter the FULL HTTPS Render address in settings.
- Some site won't open: Reader mode supports public HTML only and can be blocked.
