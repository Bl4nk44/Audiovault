# SpotizerrNew

SpotizerrNew is a modern web application that allows you to download, manage, and play music from various sources (Spotify, YouTube).

## Key Features

*   **Music Download:** Download tracks, albums, and playlists from Spotify and YouTube.
*   **Library:** Manage downloaded tracks with search and filtering capabilities.
*   **Player:** Built-in audio player with visualization and playlist support.
*   **Watchlist:** Automatically monitor and download new releases from your favorite artists.
*   **Streaming:** Stream tracks directly before downloading.

## Technology Stack

*   **Backend:** Python, FastAPI, SQLAlchemy, yt-dlp
*   **Frontend:** React, TypeScript, TailwindCSS, Zustand
*   **Database:** SQLite (Dev) / PostgreSQL (Prod)
*   **Cache:** Redis (optional)
*   **Containerization:** Docker, Docker Compose

## Installation and Usage

The application is designed to run in Docker by default.

### Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### Running with Docker (Recommended)

1.  Clone the repository.
2.  Create a `.env` file in the root directory (or use the provided example if available).
3.  Build and start the containers:

    ```bash
    docker-compose up --build
    ```

4.  Access the application:
    *   **Frontend:** http://localhost:5173
    *   **Backend API:** http://localhost:8000/docs

### Manual Installation (Development)

If you prefer to run it locally without Docker:

#### Backend

1.  Navigate to the `backend` directory.
2.  Create a virtual environment: `python -m venv venv`.
3.  Activate the environment:
    *   Windows: `venv\Scripts\activate`
    *   Linux/Mac: `source venv/bin/activate`
4.  Install dependencies: `pip install -r requirements.txt`.
5.  Start the server: `uvicorn app.main:app --reload`.

#### Frontend

1.  Navigate to the `frontend` directory.
2.  Install dependencies: `npm install`.
3.  Start the development server: `npm run dev`.

## Author

Bl4nk44
