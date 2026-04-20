import subprocess
import os
import tempfile
import httpx
from src.storage.s3 import StorageService


async def extract_frames(video_s3_url: str, session_id: str) -> list[str]:
    """
    Download video from URL, extract 1 frame per 3 seconds via ffmpeg,
    upload to S3, return list of presigned URLs.
    """
    storage = StorageService()
    frame_urls = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Download video
        video_path = os.path.join(tmp_dir, "video.mp4")
        async with httpx.AsyncClient() as client:
            r = await client.get(video_s3_url)
            with open(video_path, "wb") as f:
                f.write(r.content)

        # Extract frames with ffmpeg
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf", "fps=1/3",
             os.path.join(tmp_dir, "frame_%03d.jpg"), "-y"],
            capture_output=True, timeout=120
        )

        # Upload frames to S3
        frame_files = sorted(f for f in os.listdir(tmp_dir) if f.endswith(".jpg"))
        for i, fname in enumerate(frame_files):
            frame_path = os.path.join(tmp_dir, fname)
            with open(frame_path, "rb") as f:
                data = f.read()
            key = f"{session_id}/frames/{i:03d}.jpg"
            await storage.upload(data, key, "image/jpeg")
            url = await storage.presigned_url(key, expires=86400)
            frame_urls.append(url)

    return frame_urls
