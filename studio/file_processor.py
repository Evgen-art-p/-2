# studio/file_processor.py
"""
Обработка загруженных файлов для агентов
Поддерживает: изображения, PDF, DOCX, TXT, MD
"""

import os
import base64
from pathlib import Path
from typing import List, Dict, Any
import mimetypes

# Для PDF
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# Для DOCX
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Для изображений
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class FileProcessor:
    """Обработчик загруженных файлов"""
    
    SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    SUPPORTED_DOCS = {'.pdf', '.docx', '.doc', '.txt', '.md'}
    SUPPORTED_VIDEO = {'.mp4', '.mov', '.avi', '.mkv'}
    
    def __init__(self, assets_dir: Path):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, uploaded_file, filename: str) -> Path:
        """
        Сохраняет загруженный файл
        uploaded_file - объект от NiceGUI upload
        """
        filepath = self.assets_dir / filename
        
        # Если это объект NiceGUI
        if hasattr(uploaded_file, 'read'):
            with open(filepath, 'wb') as f:
                f.write(uploaded_file.read())
        else:
            # Если это уже байты
            with open(filepath, 'wb') as f:
                f.write(uploaded_file)
        
        return filepath
    
    def get_file_info(self, filepath: Path) -> Dict[str, Any]:
        """Получает базовую информацию о файле"""
        stat = filepath.stat()
        ext = filepath.suffix.lower()
        
        info = {
            'name': filepath.name,
            'path': str(filepath),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'ext': ext,
            'mime_type': mimetypes.guess_type(filepath)[0] or 'unknown',
        }
        
        # Определяем тип
        if ext in self.SUPPORTED_IMAGES:
            info['type'] = 'image'
        elif ext in self.SUPPORTED_DOCS:
            info['type'] = 'document'
        elif ext in self.SUPPORTED_VIDEO:
            info['type'] = 'video'
        else:
            info['type'] = 'unknown'
        
        return info
    
    def extract_text_from_pdf(self, filepath: Path) -> str:
        """Извлекает текст из PDF"""
        if not HAS_PDF:
            return "[PDF support not installed: pip install PyPDF2]"
        
        try:
            text_parts = []
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                
                text_parts.append(f"PDF Document: {num_pages} pages")
                text_parts.append("=" * 50)
                
                for i, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(f"\n--- Page {i} ---\n{page_text}")
            
            return "\n".join(text_parts)
        except Exception as e:
            return f"[Error reading PDF: {e}]"
    
    def extract_text_from_docx(self, filepath: Path) -> str:
        """Извлекает текст из DOCX"""
        if not HAS_DOCX:
            return "[DOCX support not installed: pip install python-docx]"
        
        try:
            doc = Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            result = f"DOCX Document: {len(paragraphs)} paragraphs\n"
            result += "=" * 50 + "\n\n"
            result += "\n\n".join(paragraphs)
            
            return result
        except Exception as e:
            return f"[Error reading DOCX: {e}]"
    
    def extract_text_from_txt(self, filepath: Path) -> str:
        """Читает текстовый файл"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"Text File: {filepath.name}\n{'=' * 50}\n\n{content}"
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
                return f"Text File: {filepath.name}\n{'=' * 50}\n\n{content}"
            except Exception as e:
                return f"[Error reading text file: {e}]"
    
    def get_image_description(self, filepath: Path) -> Dict[str, Any]:
        """Получает информацию о картинке"""
        info = {}
        
        if not HAS_PIL:
            info['description'] = "[PIL not installed: pip install Pillow]"
            return info
        
        try:
            with Image.open(filepath) as img:
                info['width'] = img.width
                info['height'] = img.height
                info['format'] = img.format
                info['mode'] = img.mode
                info['description'] = f"Image: {img.width}x{img.height}, format: {img.format}"
        except Exception as e:
            info['description'] = f"[Error reading image: {e}]"
        
        return info
    
    def image_to_base64(self, filepath: Path) -> str:
        """Конвертирует картинку в base64 для vision API"""
        try:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return f"[Error encoding image: {e}]"
    
    def process_file(self, filepath: Path, analyze_images: bool = False) -> Dict[str, Any]:
        """
        Обрабатывает файл и возвращает результат
        
        analyze_images: если True, возвращает base64 для vision API
        """
        info = self.get_file_info(filepath)
        result = {'info': info}
        
        file_type = info['type']
        ext = info['ext']
        
        # Текстовые документы
        if file_type == 'document':
            if ext == '.pdf':
                result['content'] = self.extract_text_from_pdf(filepath)
            elif ext in {'.docx', '.doc'}:
                result['content'] = self.extract_text_from_docx(filepath)
            elif ext in {'.txt', '.md'}:
                result['content'] = self.extract_text_from_txt(filepath)
            else:
                result['content'] = f"[Unsupported document format: {ext}]"
        
        # Изображения
        elif file_type == 'image':
            img_info = self.get_image_description(filepath)
            result['image_info'] = img_info
            result['description'] = img_info.get('description', 'Image file')
            
            if analyze_images:
                result['base64'] = self.image_to_base64(filepath)
                result['needs_vision'] = True
        
        # Видео (пока только метаданные)
        elif file_type == 'video':
            result['content'] = f"[Video file: {info['name']}, size: {info['size_mb']} MB]"
            result['note'] = "Video analysis not yet implemented"
        
        # Неизвестный тип
        else:
            result['content'] = f"[Unknown file type: {ext}]"
        
        return result
    
    def process_all_files(self, analyze_images: bool = False) -> Dict[str, Any]:
        """
        Обрабатывает все файлы в assets_dir
        
        Возвращает:
        {
            'files': [...],  # Список обработанных файлов
            'summary': '...',  # Краткое описание
            'vision_images': [...]  # Картинки для vision API (если analyze_images=True)
        }
        """
        if not self.assets_dir.exists():
            return {
                'files': [],
                'summary': 'No files uploaded',
                'vision_images': []
            }
        
        files = [f for f in self.assets_dir.rglob('*') if f.is_file()]
        if not files:
            return {
                'files': [],
                'summary': 'No files uploaded',
                'vision_images': []
            }
        
        processed = []
        vision_images = []
        
        for filepath in files:
            if filepath.is_file():
                result = self.process_file(filepath, analyze_images)
                processed.append(result)
                
                if result.get('needs_vision'):
                    vision_images.append({
                        'name': result['info']['name'],
                        'base64': result.get('base64'),
                        'mime_type': result['info']['mime_type']
                    })
        
        # Формируем summary
        summary_parts = [f"Total files: {len(processed)}"]
        
        images = [f for f in processed if f['info']['type'] == 'image']
        docs = [f for f in processed if f['info']['type'] == 'document']
        videos = [f for f in processed if f['info']['type'] == 'video']
        
        if images:
            summary_parts.append(f"Images: {len(images)}")
        if docs:
            summary_parts.append(f"Documents: {len(docs)}")
        if videos:
            summary_parts.append(f"Videos: {len(videos)}")
        
        summary = " | ".join(summary_parts)
        
        return {
            'files': processed,
            'summary': summary,
            'vision_images': vision_images
        }
    
    def format_for_agent(self, analyze_images: bool = False) -> str:
        """
        Форматирует все файлы для добавления в промпт агента
        
        Возвращает красиво оформленный текст с содержимым файлов
        """
        result = self.process_all_files(analyze_images)
        
        if not result['files']:
            return ""
        
        output_parts = [
            "\n" + "=" * 70,
            "ЗАГРУЖЕННЫЕ ФАЙЛЫ",
            "=" * 70,
            f"\n{result['summary']}\n"
        ]
        
        for i, file_data in enumerate(result['files'], 1):
            info = file_data['info']
            # Показываем подпапку если файл в категорийной директории
            rel = Path(info['path']).parent.name
            folder_tag = f" [{rel}]" if rel not in ('assets',) else ""
            output_parts.append(f"\n--- Файл {i}: {info['name']}{folder_tag} ---")
            output_parts.append(f"Тип: {info['type']}, Размер: {info['size_mb']} MB")
            
            # Добавляем содержимое
            if 'content' in file_data:
                output_parts.append("\nСодержимое:")
                output_parts.append(file_data['content'])
            elif 'description' in file_data:
                output_parts.append(f"\n{file_data['description']}")
                if file_data.get('needs_vision'):
                    output_parts.append("(Изображение будет проанализировано через vision API)")
        
        output_parts.append("\n" + "=" * 70 + "\n")
        
        return "\n".join(output_parts)


# Вспомогательные функции для использования в UI

def create_processor_for_project(project_dir: Path) -> FileProcessor:
    """Создаёт процессор для конкретного проекта"""
    assets_dir = project_dir / "assets"
    return FileProcessor(assets_dir)


def get_files_context(project_dir: Path, analyze_images: bool = False) -> str:
    """
    Получает контекст файлов для добавления в промпт
    
    Использование в ui_workshop.py:
    ```python
    files_context = get_files_context(current_project_dir)
    full_prompt = f"{system_prompt}\n\n{files_context}\n\n{user_message}"
    ```
    """
    processor = create_processor_for_project(project_dir)
    return processor.format_for_agent(analyze_images)
