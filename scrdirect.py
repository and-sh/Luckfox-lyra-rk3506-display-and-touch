#!/usr/bin/env python3
import time
import math
import struct
import signal
import sys

# Настройки
WIDTH = 800
HEIGHT = 480
STRIDE = 3200
FB_DEVICE = '/dev/fb0'

class NoConversionScreensaver:
    def __init__(self):
        self.running = True
        self.frame_count = 0
        self.start_time = time.time()
        
        # Параметры шарика
        self.ball_x = WIDTH // 2
        self.ball_y = HEIGHT // 2
        self.ball_dx = 3
        self.ball_dy = 2
        self.ball_radius = 30
        
        # ЗАРАНЕЕ создаем BGRX буфер
        self.fb_buffer = bytearray(STRIDE * HEIGHT)
        
        # ЗАРАНЕЕ вычисляем цвета в BGRX формате
        self.ball_color = struct.pack('BBBB', 0, 255, 0, 0)  # Зеленый: B=0, G=255, R=0, X=0
        self.bg_color = struct.pack('BBBB', 0, 0, 0, 0)      # Черный
        
        # Memoryview для быстрого доступа
        self.mv = memoryview(self.fb_buffer)
        
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

    def clear_buffer_fast(self):
        """Быстрая очистка буфера"""
        # Заполняем нулями (черный цвет в BGRX)
        self.mv[:] = b'\x00' * len(self.fb_buffer)

    def draw_ball_direct_bgrx(self, x, y, radius):
        """Рисуем шарик напрямую в BGRX буфере"""
        x_int, y_int, r_int = int(x), int(y), int(radius)
        
        # Оптимизированный алгоритм рисования круга
        r_squared = r_int * r_int
        for dy in range(-r_int, r_int + 1):
            for dx in range(-r_int, r_int + 1):
                if dx * dx + dy * dy <= r_squared:
                    px = x_int + dx
                    py = y_int + dy
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        pos = (py * STRIDE) + (px * 4)
                        self.mv[pos:pos+4] = self.ball_color

    def draw_frame_no_conversion(self):
        """Отрисовка БЕЗ КОНВЕРТАЦИИ - сразу в BGRX"""
        # Очищаем буфер
        self.clear_buffer_fast()
        
        # Рисуем шарик
        self.draw_ball_direct_bgrx(self.ball_x, self.ball_y, self.ball_radius)
        
        return self.fb_buffer

    def update_physics(self):
        """Обновление физики"""
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        if self.ball_x <= self.ball_radius or self.ball_x >= WIDTH - self.ball_radius:
            self.ball_dx = -self.ball_dx
        if self.ball_y <= self.ball_radius or self.ball_y >= HEIGHT - self.ball_radius:
            self.ball_dy = -self.ball_dy

    def run(self):
        """Основной цикл БЕЗ КОНВЕРТАЦИИ"""
        print("Запуск скринсейвера БЕЗ конвертации...")
        print("Нажмите Ctrl+C для выхода")
        
        self.hide_cursor()
        last_fps_time = time.time()
        frame_count = 0
        
        try:
            with open(FB_DEVICE, 'wb') as fb:
                while self.running:
                    frame_start = time.time()
                    
                    # Обновляем физику
                    self.update_physics()
                    
                    # Рисуем кадр БЕЗ КОНВЕРТАЦИИ
                    frame_data = self.draw_frame_no_conversion()
                    
                    # Выводим
                    fb.seek(0)
                    fb.write(frame_data)
                    fb.flush()
                    
                    # Считаем FPS
                    frame_count += 1
                    current_time = time.time()
                    
                    if current_time - last_fps_time >= 1.0:
                        fps = frame_count / (current_time - last_fps_time)
                        print(f"FPS: {fps:.1f}")
                        frame_count = 0
                        last_fps_time = current_time
                    
                    # Ограничиваем FPS
                    '''frame_time = time.time() - frame_start
                    if frame_time < 0.033:  # ~30 FPS
                        time.sleep(0.033 - frame_time)
                    '''    
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            self.show_cursor()

def main():
    screensaver = NoConversionScreensaver()
    screensaver.run()

if __name__ == "__main__":
    main()
