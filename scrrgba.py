#!/usr/bin/env python3
import time
import math
import struct
import signal
import sys
from PIL import Image, ImageDraw, ImageFont

class CorrectColorScreensaver:
    def __init__(self):
        self.running = True
        self.width = 800
        self.height = 480
        self.stride = 3200
        self.fb_device = '/dev/fb0'
        
        # Создаем RGBA изображение
        self.image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        
        # Цвета в формате (R, G, B, A) но интерпретируем как (B, G, R, X)
        # Поэтому:
        # - Для синего: R=0, G=0, B=255 → BGRX: B=255, G=0, R=0
        # - Для зеленого: R=0, G=255, B=0 → BGRX: B=0, G=255, R=0  
        # - Для красного: R=255, G=0, B=0 → BGRX: B=0, G=0, R=255
        
        self.ball_color = (0, 255, 0, 255)    # Зелёный в BGRX: R=0, G=255, B=0
        self.bg_color = (0, 0, 0, 0)          # Черный
        self.text_color = (0, 0, 255, 255)    # Красный в BGRX: R=255, G=0, B=0
        
        # Параметры анимации
        self.ball_x = self.width // 2
        self.ball_y = self.height // 2
        self.ball_dx = 3
        self.ball_dy = 2
        self.ball_radius = 30
        
        self.frame_count = 0
        self.start_time = time.time()

        # Настраиваем шрифты
        self.setup_fonts()        
        
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def setup_fonts(self):
        """Настройка шрифтов разных размеров"""
        try:
            # Пробуем загрузить доступные шрифты
            self.font_small = ImageFont.load_default()
            
            # Пытаемся создать увеличенный шрифт
            try:
                # Для более новых версий PIL
                self.font_large = ImageFont.truetype("DejaVuSans.ttf", 24)
            except:
                try:
                    # Альтернативный шрифт
                    self.font_large = ImageFont.truetype("arial.ttf", 24)
                except:
                    # Создаем псевдо-крупный шрифт через масштабирование
                    self.font_large = ImageFont.load_default()
                    
        except Exception as e:
            print(f"Ошибка загрузки шрифтов: {e}")
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()



    def signal_handler(self, signum, frame):
        self.running = False
    
    def hide_cursor(self):
        try:
            with open('/dev/tty0', 'w') as tty:
                tty.write('\033[?25l')
        except:
            pass
    
    def show_cursor(self):
        try:
            with open('/dev/tty0', 'w') as tty:
                tty.write('\033[?25h')
        except:
            pass

    def update_physics(self):
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        if self.ball_x <= self.ball_radius or self.ball_x >= self.width - self.ball_radius:
            self.ball_dx = -self.ball_dx
        if self.ball_y <= self.ball_radius or self.ball_y >= self.height - self.ball_radius:
            self.ball_dy = -self.ball_dy

    def draw_frame(self):
        # Очищаем
        self.draw.rectangle([0, 0, self.width, self.height], fill=self.bg_color)
        
        # Рисуем шарик
        ball_bbox = [
            self.ball_x - self.ball_radius,
            self.ball_y - self.ball_radius,
            self.ball_x + self.ball_radius,
            self.ball_y + self.ball_radius
        ]
        self.draw.ellipse(ball_bbox, fill=self.ball_color)
        
        # FPS текст
        current_time = time.time()
        #if current_time - self.last_fps_time >= 0.5:
        fps = self.frame_count / (current_time - self.last_fps_time)
        self.draw.rectangle([0, 0, 120, 30], fill=self.bg_color)
        self.draw.text((5, 2), f"FPS: {fps:.1f}", fill=self.text_color, font=self.font_large)
        self.last_fps_time = current_time
        self.frame_count = 0
        
        # Конвертируем
        rgba_data = self.image.tobytes()
        return rgba_data

    def run(self):
        print("Запуск скринсейвера с мгновенной конвертацией RGBA->BGRX")
        
        self.hide_cursor()
        self.last_fps_time = time.time()
        self.frame_count = 0
        
        try:
            with open(self.fb_device, 'wb') as fb:
                while self.running:
                    start_time = time.time()
                    
                    self.update_physics()
                    frame_data = self.draw_frame()
                    
                    fb.seek(0)
                    fb.write(frame_data)
                    fb.flush()
                    
                    self.frame_count += 1
                    
                    # Ограничение FPS
                    elapsed = time.time() - start_time
                    '''
                    if elapsed < 0.016:
                        time.sleep(0.016 - elapsed)
                    '''                        
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            self.show_cursor()

if __name__ == "__main__":
    screensaver = CorrectColorScreensaver()
    screensaver.run()
