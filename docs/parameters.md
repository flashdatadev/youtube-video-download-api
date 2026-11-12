# YouTube video, audio and clip parameters

Use these options with `submit_download`, or apply the same options to every ID in
`submit_bulk`. The official SDK validates supported request fields before HTTP submission.

## Media selection

| Option | Values | Default |
| --- | --- | --- |
| `download_type` | `audio_video`, `video`, `audio` | `audio_video` |
| `output_format` | `mp4`, `webm`, `mkv` for video; `m4a`, `mp3`, `opus` for audio | `mp4`; `m4a` for audio |
| `video_quality` | `best`, `worst`, or `<=`, `==`, `>=` with a supported height | `<=720` |
| `fps` | A comparison such as `<=30` or `==60` | Service default |
| `audio_language` | `default`, `original` | `default` |
| `audio_quality` | `best`, `320`, `256`, `192`, `128` | `best` |
| `upload_metadata` | `True` or `False` | `False` |
| `start_at`, `end_at` | `HH:MM:SS`; end later than start | Full video |
| `yt_dlp_format` | Advanced format-selector string | Omitted |

Supported video heights are 144, 360, 480, 720, 1080, 1440, 2160 and 4320.
Use `<=2160` to request up to 4K from a source with suitable formats. Exact selection
can fail if the source does not have that height.

Audio-only requests use an audio output format and omit `video_quality` and `fps`.
`audio_quality` applies to audio-only downloads. Video-only requests omit `audio_language`.
The `yt_dlp_format` selector overrides normal video quality, frame-rate and audio-language
selection; use it when the ordinary options do not express your choice.

## Clip example

```python
from flashdata import FlashData
from flashdata_download import submit_download

# Define storage using docs/storage.md.
with FlashData(api_key="your-flashdata-api-key") as client:
    job_id = submit_download(
        client,
        "YOUR_VIDEO_ID",
        storage=storage,
        checkpoint="output/clip.job.json",
        output_format="mp4",
        video_quality="<=720",
        start_at="00:00:10",
        end_at="00:00:40",
    )
    print(job_id)
```

When only `end_at` is set, the clip starts at `00:00:00`. Use
[examples/download_clip.py](../examples/download_clip.py) for a full submit-and-collect run.

## Video IDs and URLs

The local helper accepts bare IDs, `youtube.com/watch?v=...`, `youtu.be/...`,
`youtube.com/shorts/...`, `/live/...` and `/embed/...`. It converts them into the API's
required `video_id`. Playlist-only links and unrelated hostnames are rejected locally.
Bulk files contain IDs, not URLs, one per line.

Full contract: [YouTube Download API reference](https://flashdata.dev/docs/sources/youtube_download#parameters).
