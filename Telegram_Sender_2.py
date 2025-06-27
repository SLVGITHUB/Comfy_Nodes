import os
import tempfile
import shutil
import json
from datetime import datetime
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import requests
import imageio.v2 as imageio
from scipy.io.wavfile import write as wav_write

class TelegramSender:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chat_id": ("STRING", {"default": "", "multiline": False}),
                "bot_token": ("STRING", {"default": "", "multiline": False}),
                "text": ("STRING", {"default": "", "multiline": True}),
                "bold": ("BOOLEAN", {"default": False}),
                "code": ("BOOLEAN", {"default": False}),
                "disable_notification": ("BOOLEAN", {"default": False}),
                "protect_content": ("BOOLEAN", {"default": False}),
                "image_format": (["PNG", "JPEG", "WebP"], {"default": "PNG"}),
                "png_compress_level": ("INT", {"default": 4, "min": 0, "max": 9, "step": 1}),
                "jpeg_quality": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1}),
                "webp_lossless": ("BOOLEAN", {"default": False}),
                "webp_quality": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "image": ("IMAGE",),       # форма: (H, W, 3)
                "video": ("VIDEO",),       # форма: (F, H, W, 3)
                "audio": ("AUDIO",),       # {'waveform': tensor, 'sample_rate': int}
                "video_url": ("STRING", {"default": "", "multiline": False}),
                "file_path": ("STRING", {"default": "", "multiline": False}),  # <<< Новое поле
            },
            "hidden": {"prompt": "PROMPT"},
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_NODE = True
    FUNCTION = "send_to_telegram"
    CATEGORY = "tools"

    def send_to_telegram(
        self, chat_id, bot_token, text, bold, code, disable_notification,
        protect_content, image_format, png_compress_level, jpeg_quality,
        webp_lossless, webp_quality, prompt, image=None, video=None, audio=None,
        video_url=None, file_path=None
    ):
        temp_dir = tempfile.mkdtemp()
        cur_date = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
        files_to_send = []

        formatted_text = text
        if bold:
            formatted_text = f"**{formatted_text}**"
        if code:
            formatted_text = f"```{text}```"

        # === Обработка изображения ===
        if image is not None:
            img_tensor = image.squeeze().cpu().numpy()
            img_tensor = np.clip(255.0 * img_tensor, 0, 255).astype(np.uint8)
            img = Image.fromarray(img_tensor)

            metadata = PngInfo()
            metadata.add_text("prompt", json.dumps(prompt))
            file_path_img = os.path.join(temp_dir, f"ComfyUI_{cur_date}_img.{image_format.lower()}")
            img.save(file_path_img, **{
                "PNG": {"compress_level": png_compress_level},
                "JPEG": {"quality": jpeg_quality},
                "WebP": {"lossless": webp_lossless, "quality": webp_quality}
            }.get(image_format, {}))
            files_to_send.append(("photo", file_path_img))

        # === Обработка видео ===
        if video is not None:
            if isinstance(video, dict):
                video_tensor = video.get("samples")
            else:
                video_tensor = video

            if video_tensor is not None:
                video_tensor = video_tensor.cpu().numpy()
                video_tensor = np.clip(255.0 * video_tensor, 0, 255).astype(np.uint8)

                file_path_video = os.path.join(temp_dir, f"ComfyUI_{cur_date}_video.mp4")
                imageio.mimsave(file_path_video, video_tensor, fps=24, format="mp4")
                files_to_send.append(("video", file_path_video))

        # === Обработка аудио ===
        if audio is not None:
            if isinstance(audio, dict):
                waveform = audio.get("waveform")
                sample_rate = audio.get("sample_rate", 44100)
            else:
                waveform = audio
                sample_rate = 44100

            if waveform is not None:
                audio_array = waveform.squeeze().cpu().numpy()
                audio_int16 = (audio_array * np.iinfo(np.int16).max).astype(np.int16)

                if len(audio_int16.shape) == 1:
                    audio_int16 = audio_int16[np.newaxis, :]

                file_path_audio = os.path.join(temp_dir, f"ComfyUI_{cur_date}_audio.wav")
                wav_write(file_path_audio, rate=sample_rate, data=audio_int16.T)
                files_to_send.append(("audio", file_path_audio))

        # === Обработка видео по ссылке ===
        if video_url:
            try:
                response = requests.get(video_url, stream=True)
                response.raise_for_status()
                file_extension = os.path.splitext(video_url)[1] or ".mp4"
                file_path_url = os.path.join(temp_dir, f"ComfyUI_{cur_date}_video_url{file_extension}")

                with open(file_path_url, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)

                files_to_send.append(("video", file_path_url))
            except Exception as e:
                print(f"[ERROR] Failed to download video from URL: {e}")

        # === Обработка файла по пути (например, из VideoCombine) ===
        if file_path and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()

            dest_path = os.path.join(temp_dir, os.path.basename(file_path))
            shutil.copy(file_path, dest_path)

            media_type = "document"
            if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                media_type = "photo"
            elif ext in [".mp4", ".avi", ".mov", ".gif"]:
                media_type = "video"
            elif ext in [".mp3", ".wav", ".ogg"]:
                media_type = "audio"

            files_to_send.append((media_type, dest_path))

        # === Если нет медиа — отправляем только текст ===
        if not files_to_send:
            response = self.send_telegram_media(
                bot_token=bot_token,
                method="sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": formatted_text,
                    "parse_mode": "Markdown",
                    "disable_notification": disable_notification,
                    "protect_content": protect_content,
                }
            )
        else:
            for media_type, path in files_to_send:
                with open(path, "rb") as f:
                    files = {media_type: f}
                    data = {
                        "chat_id": chat_id,
                        "caption": formatted_text,
                        "parse_mode": "Markdown",
                        "disable_notification": disable_notification,
                        "protect_content": protect_content,
                    }

                    method_map = {
                        "photo": "sendPhoto",
                        "video": "sendVideo",
                        "audio": "sendAudio",
                        "document": "sendDocument"
                    }

                    method = method_map.get(media_type, "sendDocument")
                    self.send_telegram_media(bot_token, method, data=data, files=files)

        shutil.rmtree(temp_dir)
        return ("Telegram message sent successfully",)

    def send_telegram_media(self, bot_token, method, data=None, files=None):
        url = f"https://api.telegram.org/bot{bot_token}/{method}"
        response = requests.post(url, data=data, files=files)
        response.raise_for_status()
        return response.json()
