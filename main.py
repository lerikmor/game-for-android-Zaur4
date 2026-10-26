from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
import random

# Размер поля
COLS, ROWS = 8, 8
CELL_SIZE = 55
# Типы "конфет" — просто цвета
COLORS = [
    (0.95, 0.3, 0.3),   # красный
    (0.3, 0.7, 0.95),   # синий
    (0.4, 0.85, 0.4),   # зелёный
    (0.95, 0.85, 0.3),  # жёлтый
    (0.8, 0.4, 0.9),    # фиолетовый
    (0.95, 0.6, 0.2),   # оранжевый
]


class Tile(Widget):
    """Одна клетка поля."""
    def __init__(self, color_idx, row, col, callback, **kwargs):
        super().__init__(**kwargs)
        self.color_idx = color_idx
        self.row = row
        self.col = col
        self.callback = callback
        self.size_hint = (None, None)
        self.size = (CELL_SIZE, CELL_SIZE)
        self.draw()

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*COLORS[self.color_idx])
            Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.6)
            Rectangle(pos=(self.pos[0]+3, self.pos[1]+3),
                      size=(self.size[0]-6, self.size[1]-6))

    def on_pos(self, *args):
        self.draw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.callback(self.row, self.col)
            return True
        return False


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected = None
        self.busy = False

        main = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Заголовок + счёт
        top = BoxLayout(size_hint_y=0.1)
        self.score_label = Label(text="Очки: 0", font_size='20sp',
                                 bold=True, color=(1, 1, 1, 1))
        top.add_widget(self.score_label)
        main.add_widget(top)

        # Поле
        self.board_holder = BoxLayout(size_hint_y=0.75)
        self.board = GridLayout(cols=COLS, rows=ROWS,
                                size_hint=(None, None),
                                spacing=2)
        self.board.width = COLS * CELL_SIZE
        self.board.height = ROWS * CELL_SIZE
        self.board.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.board_holder.add_widget(Widget())  # spacer слева
        self.board_holder.add_widget(self.board)
        self.board_holder.add_widget(Widget())  # spacer справа
        main.add_widget(self.board_holder)

        # Кнопка "Меню"
        back = Button(text="В меню", size_hint_y=0.1,
                      background_color=(0.3, 0.3, 0.5, 1))
        back.bind(on_press=self.go_menu)
        main.add_widget(back)

        self.add_widget(main)

        self.score = 0
        self.init_board()

    def init_board(self):
        # Заполняем без начальных совпадений
        while True:
            self.grid = [[random.randint(0, len(COLORS)-1)
                          for _ in range(COLS)] for _ in range(ROWS)]
            if not self.find_matches():
                break
        self.rebuild_ui()

    def rebuild_ui(self):
        self.board.clear_widgets()
        for r in range(ROWS):
            for c in range(COLS):
                t = Tile(self.grid[r][c], r, c, self.on_tile_tap)
                self.board.add_widget(t)

    def on_tile_tap(self, row, col):
        if self.busy:
            return
        if self.selected is None:
            self.selected = (row, col)
            self.highlight(row, col, True)
        else:
            r0, c0 = self.selected
            self.highlight(r0, c0, False)
            if abs(r0 - row) + abs(c0 - col) == 1:
                self.swap(r0, c0, row, col)
            self.selected = None

    def highlight(self, row, col, on):
        idx = row * COLS + col
        tile = self.board.children[ROWS*COLS - 1 - idx]
        if on:
            tile.canvas.clear()
            with tile.canvas:
                Color(1, 1, 1)
                Rectangle(pos=tile.pos, size=tile.size)
        else:
            tile.draw()

    def swap(self, r0, c0, r1, c1):
        self.grid[r0][c0], self.grid[r1][c1] = self.grid[r1][c1], self.grid[r0][c0]
        if self.find_matches():
            self.busy = True
            self.rebuild_ui()
            Clock.schedule_once(lambda dt: self.resolve(), 0.15)
        else:
            # Откат
            self.grid[r0][c0], self.grid[r1][c1] = self.grid[r1][c1], self.grid[r0][c0]
            self.rebuild_ui()

    def find_matches(self):
        matches = set()
        # Горизонтали
        for r in range(ROWS):
            run = 1
            for c in range(1, COLS):
                if self.grid[r][c] == self.grid[r][c-1]:
                    run += 1
                else:
                    if run >= 3:
                        for k in range(c-run, c):
                            matches.add((r, k))
                    run = 1
            if run >= 3:
                for k in range(COLS-run, COLS):
                    matches.add((r, k))
        # Вертикали
        for c in range(COLS):
            run = 1
            for r in range(1, ROWS):
                if self.grid[r][c] == self.grid[r-1][c]:
                    run += 1
                else:
                    if run >= 3:
                        for k in range(r-run, r):
                            matches.add((k, c))
                    run = 1
            if run >= 3:
                for k in range(ROWS-run, ROWS):
                    matches.add((k, c))
        return matches

    def resolve(self):
        matches = self.find_matches()
        if not matches:
            self.busy = False
            return

        self.score += len(matches) * 10
        self.score_label.text = f"Очки: {self.score}"

        # Удаляем и сдвигаем вниз
        for c in range(COLS):
            column = [self.grid[r][c] for r in range(ROWS)
                      if (r, c) not in matches]
            missing = ROWS - len(column)
            new_col = [random.randint(0, len(COLORS)-1)
                       for _ in range(missing)] + column
            for r in range(ROWS):
                self.grid[r][c] = new_col[r]

        self.rebuild_ui()
        Clock.schedule_once(lambda dt: self.resolve(), 0.2)

    def go_menu(self, *args):
        self.manager.current = 'menu'


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=30)

        title = Label(
            text="[b]ИГРА ОТ\nЗАУРА МАГКЕЕВА[/b]",
            markup=True,
            font_size='32sp',
            halign='center',
            valign='middle',
            color=(1, 1, 1, 1)
        )
        title.bind(size=lambda *a: setattr(title, 'text_size', title.size))
        layout.add_widget(title)

        play_btn = Button(
            text="ИГРАТЬ",
            font_size='26sp',
            size_hint=(1, 0.25),
            background_color=(0.2, 0.7, 0.3, 1)
        )
        play_btn.bind(on_press=self.start_game)
        layout.add_widget(play_btn)

        self.add_widget(layout)

    def start_game(self, *args):
        self.manager.current = 'game'


class ThreeInRowApp(App):
    def build(self):
        Window.clearcolor = (0.12, 0.12, 0.2, 1)
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        return sm


if __name__ == '__main__':
    ThreeInRowApp().run()
