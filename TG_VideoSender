import os
import requests
import json
from pathlib import Path
from typing import Tuple
import time
import hashlib

class TelegramVideoSender:
    def __init__(self):
        self.last_trigger = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bot_token": ("STRING", {"default": ""}),
                "chat_id": ("STRING", {"default": ""}),
                "output_folder": ("STRING", {"default": "G:\\COMFY\\ComfyUI_windows_portable\\ComfyUI\\output"}),
                "send_as_video_note": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "force_resend": ("BOOLEAN", {"default": False}),
                "trigger": ("BOOLEAN", {"default": False, "label_on": "Send Now", "label_off": "Wait"}),
            },
            "optional": {
                "video_path": ("STRING", {"default": "", "forceInput": True}),
                "caption": ("STRING", {"multiline": True, "default": ""}),
                "disable_notification": ("BOOLEAN", {"default": False}),
                "duration": ("INT", {"default": 0, "min": 0, "max": 60}),
                "length": ("INT", {"default": 360, "min": 1, "max": 1080}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("status", "response_json", "seed", "trigger")
    FUNCTION = "send_video"
    CATEGORY = "Media/Telegram"
    OUTPUT_NODE = True

    def find_latest_mp4(self, folder_path: str) -> Tuple[str, float, str]:
        """Находит самый свежий MP4 файл в указанной папке и возвращает его хеш"""
        if not os.path.exists(folder_path):
            return "", 0, ""
            
        latest_file = ""
        latest_time = 0
        file_hash = ""
        
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.lower().endswith('.mp4'):
                mod_time = entry.stat().st_mtime
                if mod_time > latest_time:
                    latest_time = mod_time
                    latest_file = entry.path
                    with open(latest_file, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
        return latest_file, latest_time, file_hash

    def convert_to_circle_video(self, input_path: str) -> str:
        """Конвертирует видео в квадратный формат для кружков"""
        # Здесь должна быть конвертация с помощью ffmpeg
        return input_path

    def send_video(self, bot_token: str, chat_id: str, output_folder: str,
                  send_as_video_note: bool = False, seed: int = 0,
                  force_resend: bool = False, trigger: bool = False,
                  video_path: str = "", caption: str = "",
                  disable_notification: bool = False, duration: int = 0,
                  length: int = 360) -> Tuple[str, str, int, bool]:
        
        # Если триггер не активен, пропускаем выполнение
        if not trigger and self.last_trigger == trigger:
            return ("waiting: Trigger not activated", "{}", seed, trigger)
        
        self.last_trigger = trigger

        # Используем переданный путь к видео или ищем последний файл
        if video_path and os.path.exists(video_path):
            mp4_path = video_path
            mod_time = os.path.getmtime(video_path)
            with open(video_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
        else:
            mp4_path, mod_time, file_hash = self.find_latest_mp4(output_folder)
            if not mp4_path:
                return ("error: No MP4 files found", json.dumps({
                    "folder": output_folder,
                    "exists": os.path.exists(output_folder)
                }), seed, trigger)

        # Создаем уникальный ключ для этого файла и параметров
        params_hash = hashlib.md5(
            f"{file_hash}{send_as_video_note}{caption}{duration}{length}".encode()
        ).hexdigest()
        
        # Проверяем, был ли уже отправлен этот файл с такими параметрами
        sent_marker_file = os.path.join(output_folder, f".sent_{params_hash}")
        
        if not force_resend and os.path.exists(sent_marker_file):
            return ("skipped: File already sent with these parameters", json.dumps({
                "file": mp4_path,
                "already_sent": True,
                "marker_file": sent_marker_file
            }), seed, trigger)

        try:
            # Проверяем размер файла
            file_size = os.path.getsize(mp4_path) / (1024 * 1024)  # в MB
            max_size = 50 if not send_as_video_note else 10
            
            if file_size > max_size:
                return (f"error: File too large (max {max_size}MB)", json.dumps({
                    "file": mp4_path,
                    "size_mb": file_size,
                    "max_allowed": max_size
                }), seed, trigger)

            # Для видео-кружка проверяем длительность
            if send_as_video_note and duration > 60:
                duration = 60

            # Если отправляем как кружок, конвертируем видео
            if send_as_video_note:
                mp4_path = self.convert_to_circle_video(mp4_path)
                if not mp4_path:
                    return ("error: Failed to convert video to circle format", "{}", seed, trigger)

            # Подготовка запроса
            api_method = "sendVideoNote" if send_as_video_note else "sendVideo"
            url = f"https://api.telegram.org/bot{bot_token}/{api_method}"
            
            with open(mp4_path, 'rb') as video_file:
                files = {'video_note' if send_as_video_note else 'video': video_file}
                data = {
                    "chat_id": chat_id,
                    "disable_notification": str(disable_notification).lower(),
                    "supports_streaming": str(not send_as_video_note).lower(),
                }
                
                if not send_as_video_note and caption:
                    data["caption"] = caption
                
                if send_as_video_note:
                    data["duration"] = str(duration)
                    data["length"] = str(length)

                # Отправка видео
                response = requests.post(url, data=data, files=files, timeout=30)
                response_data = response.json()
                
                if response.ok and response_data.get("ok"):
                    # Создаем маркер об успешной отправке
                    with open(sent_marker_file, 'w') as f:
                        f.write(json.dumps({
                            "sent_time": time.time(),
                            "params": {
                                "send_as_video_note": send_as_video_note,
                                "caption": caption,
                                "duration": duration,
                                "length": length
                            }
                        }))
                    
                    return ("success", json.dumps({
                        "file": mp4_path,
                        "modified_time": time.ctime(mod_time),
                        "size_mb": file_size,
                        "type": "video_note" if send_as_video_note else "video",
                        "response": response_data,
                        "seed": seed
                    }), seed, trigger)
                else:
                    error_msg = response_data.get('description', 'Unknown error')
                    return (f"error: {error_msg}", json.dumps(response_data), seed, trigger)
                    
        except Exception as e:
            return (f"error: {str(e)}", "{}", seed, trigger)

NODE_CLASS_MAPPINGS = {
    "TelegramVideoSender": TelegramVideoSender
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TelegramVideoSender": "📤 Telegram Video Sender (Triggerable)"
}
