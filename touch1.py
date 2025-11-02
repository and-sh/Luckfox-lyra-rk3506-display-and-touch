#!/usr/bin/env python3
import time
import random
import struct
import signal
import sys
import os
import fcntl
from PIL import Image, ImageDraw

class TouchPointScreensaver:
    def __init__(self):
        self.running = True
        self.width = 800
        self.height = 480
        self.stride = 3200
        self.fb_device = '/dev/fb0'
        
        # Создаем BGRX изображение (используем режим RGBA но интерпретируем как BGRX)
        self.image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        
        # Настройки анимации
        self.points_per_second = 30  # Скорость появления точек
        self.fade_interval = 0.01     # Интервал уменьшения яркости (10 раз в секунду)
        self.gaussian_variance = 10  # Дисперсия распределения Гаусса
        self.lut = [max(0, i % 256 - 1) for i in range(1024)]
        
        # Временные переменные
        self.last_point_time = 0
        self.last_fade_time = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        # Инициализация тачскрина
        self.touch_x = 0
        self.touch_y = 0
        self.touching = False
        
        # Создаем BGRX буфер для вывода
        self.bgrx_buffer = bytearray(self.stride * self.height)
        
        try:
            self.touch_device = open('/dev/input/event0', 'rb')
            flags = fcntl.fcntl(self.touch_device, fcntl.F_GETFL)
            fcntl.fcntl(self.touch_device, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        except Exception as e:
            print(f"Ошибка открытия тачскрина: {e}")
            self.touch_device = None
        
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        self.running = False
        print("\nЗавершение...")
    
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
    
    def read_touch_events(self):
        """Чтение событий тачскрина"""
        if not self.touch_device:
            return
            
        INPUT_EVENT_FORMAT = 'LLHHi'
        INPUT_EVENT_SIZE = struct.calcsize(INPUT_EVENT_FORMAT)
        
        EV_ABS = 0x03
        ABS_MT_POSITION_X = 0x35
        ABS_MT_POSITION_Y = 0x36
        BTN_TOUCH = 0x14a
        
        try:
            while True:
                data = self.touch_device.read(INPUT_EVENT_SIZE)
                if not data:
                    break
                    
                tv_sec, tv_usec, event_type, event_code, event_value = struct.unpack(INPUT_EVENT_FORMAT, data)
                
                if event_type == EV_ABS:
                    if event_code == ABS_MT_POSITION_X:
                        self.touch_x = event_value
                    elif event_code == ABS_MT_POSITION_Y:
                        self.touch_y = event_value
                elif event_type == 0x01 and event_code == BTN_TOUCH:  # EV_KEY + BTN_TOUCH
                    self.touching = (event_value == 1)
                    
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"Ошибка чтения тачскрина: {e}")
    
    def generate_random_bgrx_color(self):
        """Генерация случайного цвета в формате BGRX с яркостью 150-255"""
        # BGRX: Blue, Green, Red, X
        b = random.randint(150, 255)
        g = random.randint(150, 255)
        r = random.randint(150, 255)
        return (b, g, r, 0)  # BGRX формат
    
    def add_touch_points(self):
        """Добавление точек в месте касания с распределением Гаусса"""
        current_time = time.time()
        time_per_point = 1.0 / self.points_per_second
        
        if self.touching:
            # Добавляем несколько точек за один раз для равномерности
            points_to_add = 3 #min(3, int((current_time - self.last_point_time) / time_per_point))
            
            for _ in range(points_to_add):
                # Случайный радиус 1-5 пикселей
                radius = random.randint(1, 2)
                
                # Гауссовское распределение вокруг точки касания
                x = int(random.gauss(self.touch_x, self.gaussian_variance))
                y = int(random.gauss(self.touch_y, self.gaussian_variance))
                
                # Ограничиваем координаты экраном
                x = max(radius, min(self.width - radius - 1, x))
                y = max(radius, min(self.height - radius - 1, y))
                
                # Генерируем цвет в BGRX (но для PIL используем RGBA)
                b, g, r, x_val = self.generate_random_bgrx_color()
                # Для PIL используем RGBA: (r, g, b, 255)
                color = (r, g, b, 255)
                
                # Рисуем кружок сразу на изображении
                bbox = [
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius
                ]
                self.draw.ellipse(bbox, fill=color)
        
        self.last_point_time = current_time
    
    def fade_image(self):
        """Уменьшение яркости всего изображения на 1"""
        current_time = time.time()
        
        if current_time - self.last_fade_time >= self.fade_interval:
            self.image = self.image.point(self.lut)
            #self.image = im1
            self.draw = ImageDraw.Draw(self.image)
            
            self.last_fade_time = current_time
    
    
    def draw_info(self):
        """Рисование информации на изображении"""
        # Рисуем полупрозрачный фон для текста
        self.draw.rectangle([0, 0, 200, 60], fill=(0, 0, 0, 128))
        
        # Текст информации
        current_time = time.time()
        elapsed_total = current_time - self.start_time
        fps = self.frame_count / elapsed_total if elapsed_total > 0 else 0
        
        self.draw.text((5, 5), f"FPS: {fps:.1f}", fill=(255, 255, 255, 255))
        self.draw.text((5, 25), f"Touch: {self.touching}", fill=(255, 255, 255, 255))
        
        if self.touching:
            self.draw.text((5, 45), f"Pos: ({self.touch_x}, {self.touch_y})", 
                          fill=(255, 255, 255, 255))
    
    def run(self):
        """Основной цикл программы"""
        print("Запуск скринсейвера с точками касания и затуханием")
        print("Нажмите Ctrl+C для выхода")
        
        self.hide_cursor()
        self.last_point_time = time.time()
        self.last_fade_time = time.time()

        # print(self.lut)
        try:
            with open(self.fb_device, 'wb') as fb:
                while self.running:
                    start_time = time.time()
                    
                    # Читаем события тачскрина
                    self.read_touch_events()
                    
                    # Добавляем новые точки (рисуем сразу на изображении)
                    self.add_touch_points()
                    
                    # Рисуем информацию
                    self.draw_info()
                    
                    # Конвертируем изображение
                    bgrx_data = self.image.tobytes()
                    
                    # Выводим на экран
                    fb.seek(0)
                    fb.write(bgrx_data)
                    fb.flush()

                    # Уменьшаем яркость всего изображения
                    self.fade_image()
                    
                    self.frame_count += 1
                    
                    # Статистика в консоль
                    current_time = time.time()
                    elapsed_total = current_time - self.start_time
                    if elapsed_total >= 2.0:  # Каждые 2 секунды
                        fps = self.frame_count / elapsed_total
                        print(f"FPS: {fps:.1f}")
                        self.frame_count = 0
                        self.start_time = current_time
                    
                        
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            if self.touch_device:
                self.touch_device.close()
            self.show_cursor()
            print("Программа завершена")

if __name__ == "__main__":
    screensaver = TouchPointScreensaver()
    screensaver.run()
