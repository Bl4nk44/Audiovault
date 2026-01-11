# Getting Help with Audiovault

We're here to help! If you need support with Audiovault, there are several ways to get assistance.

## 🤝 Community Support

### GitHub Discussions

The best place to ask questions and get help from the community:

- **[Q&A Section](https://github.com/Bl4nk44/Audiovault/discussions/categories/q-a)** - Ask questions and get answers
- **[Ideas & Suggestions](https://github.com/Bl4nk44/Audiovault/discussions/categories/ideas)** - Share your ideas for new features
- **[General Chat](https://github.com/Bl4nk44/Audiovault/discussions/categories/general)** - General discussions about Audiovault

### Wiki & Documentation

- **[Project Wiki](https://github.com/Bl4nk44/Audiovault/wiki)** - Comprehensive guides and documentation
- **[README](README.md)** - Quick start guide
- **[CHANGELOG](CHANGELOG.md)** - Release notes and changes

## 🐛 Found a Bug?

If you've found a bug, please report it using the [Bug Report Template](https://github.com/Bl4nk44/Audiovault/issues/new?template=bug_report.md).

**Include:**
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, version, Docker/bare metal)
- Error logs from `docker compose logs backend`
- Screenshots if applicable

## ✨ Have a Feature Request?

We'd love to hear your ideas! Use the [Feature Request Template](https://github.com/Bl4nk44/Audiovault/issues/new?template=feature_request.md).

**Include:**
- Description of the feature
- Why you need it
- Possible implementation ideas (optional)
- Screenshots or mockups (optional)

## 📚 Common Issues & Troubleshooting

### Installation Issues

#### Docker compose fails to start

```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Restart containers
docker compose down
docker compose up -d --build

# Check if ports are already in use
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
```

#### Unable to connect to backend from frontend

**Solution**: Make sure `BACKEND_URL` environment variable is set correctly in the frontend container:

```bash
# In docker-compose.yml
frontend:
  environment:
    - BACKEND_URL=http://audiovault-backend:8000
```

#### Admin password not working

```bash
# Check the generated password in logs
docker compose logs backend | grep "Initial superuser"

# Or set a custom password before first start
echo "FIRST_SUPERUSER_PASSWORD=your_password" >> .env
docker compose up -d
```

### Download Issues

#### Tracks not downloading

1. Check the download logs in the UI
2. Verify that `yt-dlp` is working: `docker compose exec backend yt-dlp --version`
3. Check storage permissions: `ls -la` in the music library folder
4. Ensure adequate disk space: `df -h`

#### "Geo-blocked" errors

Audiovault automatically tries fallback sources. If you still get blocked:

- Try enabling a proxy (if configured)
- Check if the track is available in other services
- Report the issue with specific track information

#### "Connection timeout" errors

1. Check your internet connection
2. Verify firewall isn't blocking external connections
3. Check if the service (Spotify, YouTube, etc.) is up
4. Restart the backend: `docker compose restart backend`

### Performance Issues

#### Slow UI/Responsiveness

```bash
# Check container resources
docker stats

# Increase memory limit in docker-compose.yml
services:
  backend:
    mem_limit: 4g  # Increase from 2g if needed
```

#### High CPU usage during downloads

This is normal - `yt-dlp` uses CPU for encoding. To reduce:

- Set `CONCURRENT_DOWNLOADS` lower in `.env`
- Use `ytdl-format` to download lower quality
- Consider running on a more powerful machine

### Configuration Issues

#### Spotify integration not working

1. Verify credentials in `.env`:
   ```bash
   SPOTIFY_CLIENT_ID=your_id
   SPOTIFY_CLIENT_SECRET=your_secret
   ```
2. Check if credentials are correct at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
3. Restart backend: `docker compose restart backend`
4. Check logs for authentication errors

#### YouTube not finding tracks

1. Try different search queries in the UI
2. Check if yt-dlp can access YouTube: `docker compose exec backend yt-dlp --version`
3. Try using a proxy if available
4. Report specific track names that fail

### Streaming Issues

#### Can't connect to Subsonic API from mobile app

1. Verify `BACKEND_URL` is accessible from your phone
2. If using behind reverse proxy, ensure Subsonic paths are configured
3. Check firewall/port forwarding settings
4. Try with `SUBSONIC_LEGACY_AUTH=true` for older clients

#### Remote access not working

- If using Tailscale: Ensure Tailscale is running on both server and client
- If using port forwarding: Verify ports are open with [canyouseeme.org](https://canyouseeme.org)
- Check reverse proxy configuration for CORS issues

## 💬 Real-Time Support

### Email

For urgent issues or security concerns, contact [bl4nk44@pm.me](mailto:bl4nk44@pm.me).

## 📚 Learning Resources

- **[Official Wiki](https://github.com/Bl4nk44/Audiovault/wiki)** - Setup guides and tutorials
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Backend framework
- **[React Documentation](https://react.dev/)** - Frontend framework
- **[yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)** - Video downloader

## 🔍 Searching for Help

### Before asking, try:

1. **Search existing issues**: [GitHub Issues](https://github.com/Bl4nk44/Audiovault/issues)
2. **Search discussions**: [GitHub Discussions](https://github.com/Bl4nk44/Audiovault/discussions)
3. **Check the Wiki**: [Project Wiki](https://github.com/Bl4nk44/Audiovault/wiki)
4. **Read CONTRIBUTING.md**: [Development Guide](CONTRIBUTING.md)

## 🎣 Contributing Solutions

If you've found a solution to a problem:

1. **Share in Discussions** - Help others in the Q&A section
2. **Create a Wiki entry** - Document the solution
3. **Submit a Pull Request** - Fix the code
4. **Improve documentation** - Update guides

## 🙋 Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this community, you agree to abide by its terms.

## 🌟 Troubleshooting Checklist

Before reporting an issue, please verify:

- [ ] I'm running the latest version of Audiovault
- [ ] I've checked existing issues and discussions
- [ ] I've checked the documentation/wiki
- [ ] I've tried restarting the containers: `docker compose restart`
- [ ] I've checked relevant logs: `docker compose logs backend`
- [ ] I've verified environment variables are correct
- [ ] I've verified network connectivity
- [ ] I have at least 2GB free disk space
- [ ] My OS and Docker are up to date

## 🌠 We're Here to Help!

Don't hesitate to reach out - we're all learning together and improving Audiovault. Your feedback is valuable!

---

**Questions?** Ask in [Discussions](https://github.com/Bl4nk44/Audiovault/discussions) 💫
