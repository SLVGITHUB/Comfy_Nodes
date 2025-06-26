import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageOps
import shutil
import json
from urllib.parse import quote

class TelegramSender:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "content_type": (["video", "photo", "text", "audio"], {"default": "video"}),
                "telegram_bot_token": ("STRING", {"default": ""}),
                "chat_id": ("STRING", {"default": ""}),
            },
            "optional": {
                "video_input": ("*", {}),
                "photo_input": ("IMAGE",),
                "text_input": ("STRING", {"default": "", "multiline": True}),
                "audio_input": ("*", {}),
                "caption": ("STRING", {"default": ""}),
                "disable_notification": ("BOOLEAN", {"default": True}),
                "max_file_size": ("INT", {"default": 50, "min": 1, "max": 50}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "message_id")
    FUNCTION = "send_to_telegram"
    CATEGORY = "Communication/Telegram"

    def send_to_telegram(self, content_type, telegram_bot_token, chat_id, 
                        video_input=None, photo_input=None, text_input=None, audio_input=None,
                        caption="", disable_notification=True, max_file_size=50):
        
        # Проверка обязательных параметров
        if not telegram_bot_token:
            return ("error", "Bot token is required")
        if not chat_id:
            return ("error", "Chat ID is required")
        
        # Обработка в зависимости от типа контента
        if content_type == "text":
            return self._send_text(telegram_bot_token, chat_id, text_input, disable_notification)
        elif content_type == "photo":
            return self._send_photo(telegram_bot_token, chat_id, photo_input, caption, disable_notification, max_file_size)
        elif content_type == "video":
            return self._send_video(telegram_bot_token, chat_id, video_input, caption, disable_notification, max_file_size)
        elif content_type == "audio":
            return self._send_audio(telegram_bot_token, chat_id, audio_input, caption, disable_notification, max_file_size)
        else:
            return ("error", f"Unsupported content type: {content_type}")

    def _send_text(self, bot_token, chat_id, text, disable_notification):
        if not text:
            return ("error", "Text content is empty")
            
        params = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification
        }
        
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=params,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            if response_data.get("ok"):
                return ("success", str(response_data["result"]["message_id"]))
            else:
                error_msg = response_data.get("description", "Unknown error")
                return ("error", error_msg)
                
        except Exception as e:
            return ("error", str(e))

    def _send_photo(self, bot_token, chat_id, photo_input, caption, disable_notification, max_file_size):
        if photo_input is None:
            return ("error", "No photo input provided")
            
        # Сохраняем временное изображение
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, "telegram_photo.jpg")
        
        try:
            # Конвертируем tensor в изображение и сохраняем
            image = Image.fromarray(photo_input[0].numpy() * 255).convert("RGB")
            image.save(temp_path, quality=95)
            
            # Проверка размера файла
            file_size = os.path.getsize(temp_path) / (1024 * 1024)  # в MB
            if file_size > max_file_size:
                return ("error", f"File too large ({file_size:.2f}MB > {max_file_size}MB)")
            
            params = {
                "chat_id": chat_id,
                "disable_notification": disable_notification
            }
            if caption:
                params["caption"] = caption
                
            with open(temp_path, "rb") as photo_file:
                files = {"photo": photo_file}
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                    params=params,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                
                response_data = response.json()
                if response_data.get("ok"):
                    return ("success", str(response_data["result"]["message_id"]))
                else:
                    error_msg = response_data.get("description", "Unknown error")
                    return ("error", error_msg)
                    
        except Exception as e:
            return ("error", str(e))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _send_video(self, bot_token, chat_id, video_input, caption, disable_notification, max_file_size):
        if video_input is None:
            return ("error", "No video input provided")
            
        # Фильтрация входных данных от Video Combine
        if not isinstance(video_input, list) or len(video_input) < 2:
            return ("error", "Invalid Video Combine output format")
        
        # Выбираем последний MP4 файл (без -audio)
        mp4_files = [
            f for f in video_input[1] 
            if isinstance(f, str) 
            and f.lower().endswith('.mp4') 
            and '-audio' not in os.path.basename(f).lower()
        ]
        
        if not mp4_files:
            return ("error", "No valid MP4 files found in Video Combine output")
        
        video_path = mp4_files[-1]  # Берем последний подходящий файл

        # Проверка существования файла
        if not os.path.exists(video_path):
            return ("error", f"File not found: {video_path}")

        # Проверка размера файла
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # в MB
        if file_size > max_file_size:
            return ("error", f"File too large ({file_size:.2f}MB > {max_file_size}MB)")

        params = {
            "chat_id": chat_id,
            "supports_streaming": True,
            "disable_notification": disable_notification,
        }
        if caption:
            params["caption"] = caption

        try:
            with open(video_path, "rb") as video_file:
                files = {"video": (os.path.basename(video_path), video_file)}
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendVideo",
                    params=params,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                
                response_data = response.json()
                if response_data.get("ok"):
                    return ("success", str(response_data["result"]["message_id"]))
                else:
                    error_msg = response_data.get("description", "Unknown error")
                    return ("error", error_msg)
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Requests failed, trying CURL fallback... Error: {str(e)}")
            return self._try_curl_fallback(video_path, bot_token, chat_id, params, "sendVideo")
        except Exception as e:
            return ("error", str(e))

    def _send_audio(self, bot_token, chat_id, audio_input, caption, disable_notification, max_file_size):
        if audio_input is None:
            return ("error", "No audio input provided")
            
        # Фильтрация входных данных (аналогично видео)
        if not isinstance(audio_input, list) or len(audio_input) < 2:
            return ("error", "Invalid audio input format")
        
        # Ищем аудио файлы (mp3 или другие поддерживаемые форматы)
        audio_files = [
            f for f in audio_input[1] 
            if isinstance(f, str) 
            and any(f.lower().endswith(ext) for ext in ['.mp3', '.ogg', '.m4a', '.wav'])
        ]
        
        if not audio_files:
            return ("error", "No valid audio files found in input")
        
        audio_path = audio_files[-1]

        # Проверка существования файла
        if not os.path.exists(audio_path):
            return ("error", f"File not found: {audio_path}")

        # Проверка размера файла
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # в MB
        if file_size > max_file_size:
            return ("error", f"File too large ({file_size:.2f}MB > {max_file_size}MB)")

        params = {
            "chat_id": chat_id,
            "disable_notification": disable_notification,
        }
        if caption:
            params["caption"] = caption

        try:
            with open(audio_path, "rb") as audio_file:
                files = {"audio": (os.path.basename(audio_path), audio_file)}
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendAudio",
                    params=params,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                
                response_data = response.json()
                if response_data.get("ok"):
                    return ("success", str(response_data["result"]["message_id"]))
                else:
                    error_msg = response_data.get("description", "Unknown error")
                    return ("error", error_msg)
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Requests failed, trying CURL fallback... Error: {str(e)}")
            return self._try_curl_fallback(audio_path, bot_token, chat_id, params, "sendAudio")
        except Exception as e:
            return ("error", str(e))

    def _try_curl_fallback(self, file_path, bot_token, chat_id, params, method):
        """Альтернативный метод отправки через CURL"""
        try:
            # Подготовка команды CURL
            curl_cmd = [
                "curl", "-X", "POST",
                f"https://api.telegram.org/bot{bot_token}/{method}",
                "-F", f"chat_id={chat_id}",
                "-F", f"document=@{file_path}",
            ]
            
            # Добавляем дополнительные параметры
            if params.get("caption"):
                curl_cmd.extend(["-F", f"caption={params['caption']}"])
            if params.get("disable_notification"):
                curl_cmd.extend(["-F", "disable_notification=true"])
            if method == "sendVideo" and params.get("supports_streaming"):
                curl_cmd.extend(["-F", "supports_streaming=true"])

            # Выполняем команду
            result = subprocess.run(
                curl_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Парсим ответ
            response = json.loads(result.stdout)
            if response.get("ok"):
                return ("success", str(response["result"]["message_id"]))
            else:
                return ("error", response.get("description", "CURL: Unknown error"))
                
        except subprocess.CalledProcessError as e:
            error_msg = f"CURL failed: {e.stderr}" if e.stderr else "CURL command failed"
            print(f"❌ {error_msg}")
            return ("error", error_msg)
        except Exception as e:
            print(f"❌ Unexpected CURL error: {str(e)}")
            return ("error", str(e))

# Регистрация ноды
NODE_CLASS_MAPPINGS = {
    "TelegramSender": TelegramSender
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TelegramSender": "📤 Telegram Sender"
}
