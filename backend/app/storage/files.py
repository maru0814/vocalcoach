import os
from pathlib import Path

from fastapi import UploadFile


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def save_upload_file(uploads_dir: str, recording_id: int, audio_file: UploadFile) -> str:
    """
    保存先パス（文字列）を返す。MVPでは拡張子のみ元ファイル名から推定する。
    """
    ensure_dir(uploads_dir)
    _, ext = os.path.splitext(audio_file.filename or "")
    ext = ext.lower() if ext else ".audio"

    filename = f"{recording_id}{ext}"
    file_path = os.path.join(uploads_dir, filename)

    # UploadFile は SpooledTemporaryFile をラップしているので、読み切りて保存する
    with open(file_path, "wb") as f:
        f.write(audio_file.file.read())

    return file_path

