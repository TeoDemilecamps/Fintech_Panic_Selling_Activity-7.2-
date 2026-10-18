# Deploying on PythonAnywhere

These steps put the app on a public URL of the form `https://teodemilecamps.pythonanywhere.com`. They follow PythonAnywhere's own [Flask guide](https://help.pythonanywhere.com/pages/Flask) (manual configuration).

Replace `teodemilecamps` with your PythonAnywhere username and `Fintech_Panic_Selling_Activity-7.2-` with the repository name.

## 0. Before you start

- The dependencies need **Python 3.12 or newer** (numpy 2.5 and scikit-learn 1.9 require it). On PythonAnywhere, open **Account → System Image** and check that your account offers Python 3.12 or 3.13. PythonAnywhere's [supported versions page](https://help.pythonanywhere.com/pages/PythonVersions) lists these on the `innit` image; the older `haggis` image stops at 3.10. If you are on `haggis`, follow PythonAnywhere's [changing your system image](https://help.pythonanywhere.com/pages/ChangingSystemImage) guide first.
- The repository must be on GitHub (section 1).

## 1. Put the project on GitHub

On github.com create a **new repository** (public is simplest, so the professor can open the link). Then either:

**Option A: command line** (from the project folder)

```bash
git init
git add .
git commit -m "Panic sale risk predictor: model, Flask app and API"
git branch -M main
git remote add origin https://github.com/YOURGITHUBUSER/YOURREPO.git
git push -u origin main
```

**Option B: web upload**: on the new repository page choose **Add file → Upload files**, drag in *everything* from the project folder (including the `templates`, `static`, `tests` and `docs` folders), and commit.

Check that the repository shows these files: `flask_app.py`, `fintech.py`, `fintech.xlsx`, `fintech.joblib`, `requirements.txt`, `README.md`, `templates/index.html`, `static/style.css`, `static/app.js`. Check nothing contains passwords or tokens (there are none in this project).

## 2. Get the code onto PythonAnywhere

Log in, open **Consoles → Bash**, and run:

```bash
git clone https://github.com/YOURGITHUBUSER/YOURREPO.git
ls YOURREPO
```

The project is now at `/home/TeoDemilecamps/Fintech_Panic_Selling_Activity-7.2-`.

## 3. Create the virtualenv and install dependencies

Still in the Bash console (use 3.13 or 3.12, whichever your account offers):

```bash
mkvirtualenv --python=/usr/bin/python3.13 fintech-env
cd ~/YOURREPO
pip install -r requirements.txt
```

If the install fails with a **disk quota** error, or the pinned versions are not available for your Python version:

- Delete the environment (`rmvirtualenv fintech-env`) and skip the virtualenv. PythonAnywhere images come with Flask, scikit-learn, pandas, numpy, joblib and openpyxl pre-installed for most Python versions, and you can leave the Virtualenv box on the Web tab empty.
- The app handles a version difference by itself: if `fintech.joblib` cannot be loaded, `flask_app.py` retrains the model with `fintech.py` using the installed versions (same seed, same result).

You can also create the model files on the server yourself, which guarantees they match the installed libraries:

```bash
cd ~/YOURREPO
python fintech.py
```

## 4. Create the web app

1. Open the **Web** tab and click **Add a new web app**.
2. Choose **Manual configuration** (not the Flask quickstart) and select the **same Python version** you used for the virtualenv.
3. In the **Virtualenv** section enter `fintech-env` (it expands to `/home/YOURUSERNAME/.virtualenvs/fintech-env`).
4. Optional but recommended: in **Static files** add URL `/static/` with directory `/home/YOURUSERNAME/YOURREPO/static`.

## 5. Edit the WSGI file

On the Web tab click the link to the **WSGI configuration file**. Remove or comment out everything that is active and put in:

```python
import sys

path = '/home/YOURUSERNAME/YOURREPO'
if path not in sys.path:
    sys.path.insert(0, path)

from flask_app import app as application
```

Save the file.

## 6. Reload and test

Click the green **Reload** button on the Web tab, then open `https://YOURUSERNAME.pythonanywhere.com`.

If you see an error page, open the **Error log** link on the Web tab. The usual causes are a wrong path in the WSGI file, a virtualenv name that does not match, or a missing package.

### Final test checklist

- [ ] The home page loads and explains what is being predicted.
- [ ] Form: try the **Calm**, **Average** and **Stressed** examples and a few values of your own. The probability and risk level should move sensibly (more app checks, a bigger drawdown and more single stocks or crypto mean a higher panic-sale probability).
- [ ] Form: enter an invalid value (for example a drawdown of 99) and confirm a clear error appears.
- [ ] API: run this from your own computer's terminal and confirm you get JSON back:

  ```bash
  curl -X POST https://YOURUSERNAME.pythonanywhere.com/api/predict \
    -H "Content-Type: application/json" \
    -d '{"app_checks_per_day": 18, "portfolio_drawdown_pct": 30, "single_stock_crypto_share_pct": 70}'
  ```

  Expected: `"prediction": "panic_sale"` with a `probability_panic_sale` around 0.83.
- [ ] Health check: `https://YOURUSERNAME.pythonanywhere.com/api/health` returns `"status": "ok"`.
- [ ] Open the public URL from **another browser or device** (for example your phone on mobile data, or a private window).
- [ ] The README's example URL uses your real username.

## 7. Submission steps

1. **Invite the professor:** on PythonAnywhere open **Account** (top-right menu), find the **Teacher** field, enter `mfalonso` and save. Do not share your password or API token.
2. **GitHub link:** submit the repository URL.
3. **PythonAnywhere URL:** submit `https://YOURUSERNAME.pythonanywhere.com`.

## 8. Keeping the app online

Check the **Web** tab on PythonAnywhere. Free accounts may need the web app to be periodically extended, and the button for this appears there. Confirm the app is still running just before the deadline and on the days the work is marked.

## Updating the app later

```bash
cd ~/YOURREPO
git pull
```

Then click **Reload** on the Web tab.
