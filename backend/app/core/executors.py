from concurrent.futures import ThreadPoolExecutor

# Dedicated executor for heavy yt-dlp operations
# Adjust max_workers based on expected load and CPU cores
stream_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="stream_worker")
