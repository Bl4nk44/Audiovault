```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend (`/frontend`)

```bash
npm install
npm run dev
```

## Credits

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - The backbone of media extraction.
- **[FastAPI](https://fastapi.tiangolo.com/)** - High-performance web framework.
- **[React](https://react.dev/)** - UI library.

## Author

Bl4nk44
