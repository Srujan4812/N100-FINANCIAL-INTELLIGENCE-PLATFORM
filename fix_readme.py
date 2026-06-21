import re
content = open('README.md', 'r', encoding='utf-8', errors='ignore').read()
content = re.sub(r'# #.*?D e p l o y m e n t.*|## ☁️ Deployment on Render.*', '', content, flags=re.DOTALL)
content = content.strip()

render_text = """

---

## ☁️ Deployment on Render

This project includes a `render.yaml` Blueprint to easily deploy the platform as two web services (API and Dashboard) on Render.

1. Create a [Render](https://render.com/) account and connect your GitHub repository.
2. In the Render Dashboard, click **New +** and select **Blueprint**.
3. Select this repository and click **Connect**.
4. Render will automatically detect the `render.yaml` file and provision both the **FastAPI Server** and the **Streamlit Dashboard** as separate web services.
5. The SQLite database is pre-populated and committed, so the platform will work out of the box.
"""

open('README.md', 'w', encoding='utf-8').write(content + render_text)
