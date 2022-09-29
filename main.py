from scene import *
import sound
from math import sin, cos, pi, ceil
from random import uniform as rnd, choice, randint
from colorsys import hsv_to_rgb
import sys
import random
from menu import *
A = Action
sys.setrecursionlimit(1000000)

CELLSTATE_FULL = 3
CELLSTATE_EMPTY = 2
CELLSTATE_NONE = 1
CELLSTATE_VOID = 0

MODE_CLASSIC = 0
MODE_DZEN = 1
MODE_TWO = 2

class Button(SpriteNode):
    def __init__(self, title, *args, **kwargs):
        
        SpriteNode.__init__(self, 'pzl:Button1', *args, **kwargs)
        if "parent" in kwargs:
            self.title_label = LabelNode(title, font=kwargs['parent'].font, color="black", position=(0, 1), parent=self)
        else:
            self.title_label = LabelNode(title, position=(0, 1), parent=self)
        self.title = title

class Form:
    def __init__(self, parent):
        self.parent = parent
        self.buts = []
    
    def add_button(self, title, position, on_click, **kwargs):
        self.buts.append(
            {
                "body": Button(title, position=position, parent=self.parent, **kwargs),
                "on_click": on_click
            })
    
    def on_tap(self, touch):
        for but in self.buts:
            if touch.location in but["body"].frame:
                but["on_click"](but)
                return True
        return False

class Explosion (Node):
    def __init__(self, brick, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)
        self.position = brick.position
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p = SpriteNode(brick.texture, scale=0.5, parent=self)
            p.position = brick.size.w/4 * dx, brick.size.h/4 * dy
            p.size = brick.size
            d = 0.6
            r = 30
            p.run_action(A.move_to(rnd(-r, r), rnd(-r, r), d))
            p.run_action(A.scale_to(0, d))
            p.run_action(A.rotate_to(rnd(-pi/2, pi/2), d))
        self.run_action(A.sequence(A.wait(d), A.remove()))

def tupsum(a, b):
    return (a[0] + b[0], a[1] + b[1])

class Brick (SpriteNode):
    def __init__(self, brick_type, *args, **kwargs):
        img = colors[brick_type]
        SpriteNode.__init__(self, img, *args, **kwargs)
        self.brick_type = brick_type
        self.is_on = True
    
    def destroy(self):
        self.remove_from_parent()
        self.is_on = False

class Obj:
    def __init__(self, position):
        self.position = position
    
    def move(self, delta):
        self.position = tupsum(self.position, delta)

class GObj(Obj):
    def __init__(self, position, elements, parent):
        super().__init__(position)
        self.elements = elements
        if parent is not None:
            for el in self.elements:
                parent.add_child(el[1])
        self.redraw()
        self.hide()
    
    def __setalpha(self, alpha):
        for el in self.elements:
            el[1].alpha = alpha
    
    def display(self):
        self.__setalpha(1)
        self.redraw()
    
    def hide(self):
        self.__setalpha(0)
    
    def redraw(self):
        for el in self.elements:
            el[1].position = tupsum(self.position, el[0])
    
    def destroy(self, eff=None):
        for el in self.elements:
            if eff:
                eff(el[1])
            el[1].remove_from_parent()

class Cell:
    def __init__(self, x, y, size, parent, default_state, color):
        emrect = ui.Path.rect(0, 0, size, size)
        em = ShapeNode(emrect, 'gray', 'gray')
        fu = ShapeNode(emrect, color, color)
        self.position = (x, y)
        self.empty = GObj((x, y), [((0, 0), em)], parent)
        self.full = GObj((x, y), [((0, 0), fu)], parent)
        self.parent = parent
        self.setstate(default_state)
    
    def setstate(self, state):
        if state == 3:
            self.empty.display()
            self.full.display()
        elif state == 2:
            self.empty.display()
            self.full.hide()
        elif state == 1:
            self.empty.hide()
            self.full.hide()
        self.state = state
    
    def destroy(self, eff=None):
        self.empty.destroy()
        self.full.destroy(eff if self.state == CELLSTATE_FULL else None)


class Net(Obj):
    def __init__(self, position, WxH, size, parent, margin=4, color='#00c6e6'):
        super().__init__(position)
        W, H = WxH
        self.parent = parent
        self.W = W
        self.H = H
        self.size = size
        self.net = [[Cell(i * size + margin + self.position[0], j * size + margin + self.position[1], size - margin, parent, CELLSTATE_NONE, color) for i in range(H)] for j in range(W)]
    
    def bounds(self, i, j):
        return (i >= 0) and (j >= 0) and (i < self.W) and (j < self.H)
    
    def getstate(self, i, j):
        if not self.bounds(i, j):
            return CELLSTATE_VOID
        return self.net[i][j].state
    
    def setstate(self, i, j, state):
        if not self.bounds(i, j):
            return False
        self.net[i][j].setstate(state)
        return True
    
    def destroy(self, eff=None):
        for els in self.net:
            for el in els:
                el.destroy(eff)
                
    def loc2ij(self, position):
        position = tupsum(position, (self.size // 2, self.size // 2))
        position = tupsum(position, (-self.position[0], -self.position[1]))
        i, j = position[0] // self.size, position[1] // self.size
        return int(j), int(i)
    
    def enum(self):
        for x in range(len(self.net)):
            for y in range(len(self.net[x])):
                yield x, y
    
    def count_stated(self, state):
        r = 0
        for x, y in self.enum():
            if self.getstate(x, y) == state:
                r += 1
        return r
    
    def full(self):
        return self.count_stated(CELLSTATE_EMPTY) == 0
            
    def nearempty(self, i, j):
        d = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for f in d:
            if self.getstate(f[0] + i, f[1] + j) == CELLSTATE_EMPTY:
                return True
        return False
    
    def clean(self):
        for x, y in self.enum():
            if self.getstate(x, y) == CELLSTATE_FULL:
                self.setstate(x, y, CELLSTATE_EMPTY)
    
    def setmultistate(self, arr, state):
        for el in arr:
            self.setstate(*el, state)
    
    @staticmethod
    def random(WxH, lenrange, steps):
        net = Net((0, 0), WxH, 1, None)
        W, H = WxH
        currcell = (W // 2 + random.randint(-2, 2), H // 2 + random.randint(-2, 2))
        startcell = currcell[:]
        net.setstate(*startcell, CELLSTATE_FULL)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        line = [startcell]
        for i in range(steps):
            s = random.randint(*lenrange)
            for j in range(s):
                dir = random.choice(directions)
                oncell = tupsum(currcell, dir)
                if net.getstate(*oncell) == CELLSTATE_NONE:
                    currcell = oncell
                    net.setstate(*oncell, CELLSTATE_FULL)
                    line.append(currcell[:])
                else:
                    break
        return net, startcell, line

    @staticmethod
    def common_side(i, j, i1, j1):
        return (i - i1) ** 2 + (j - j1) ** 2 == 1
    

class Game(Scene):
    def __init__(self):
        super().__init__()
    
    def menu_button_selected(self, title):
        self.study = title == self.STUDY
        if title in [self.modes[0], self.STUDY]:
            self.mode = MODE_CLASSIC
        elif title == self.modes[1]:
            self.mode = MODE_DZEN
        elif title == self.modes[2]:
            self.mode = MODE_TWO
        if self.mode == MODE_DZEN:
            self.game_time = self.dzen_time
            self.start_time = self.t
            self.background_color = '#103020'
        if self.study:
            self.level = 200
            self.times[-1] = 1800
            self.form.add_button("?", (100, self.size.h - 50), self.on_tap_reset, size=(40, 40))
        if self.mode == MODE_TWO:
            self.form.add_button(">", (100, self.size.h - 50), self.on_tap_reset, size=(40, 40))
        self.timel = LabelNode("", font=self.font, position=(self.size.w/2+300, self.size.h-40), parent=self)
        self.levell = LabelNode("", font=self.font, position=(self.size.w/2+50, self.size.h-40), parent=self)
        self.scorel = LabelNode("", font=self.font, position=(self.size.w/2-200, self.size.h-40), parent=self)
        self.reset_level(self.mode)
        self.update_labels()
        self.inited = True
        self.dismiss_modal_scene()

    
    def on_tap_reset(self, sender):
        self.game_time = 0
    
    def setup(self):
        self.inited = False
        self.modes = ["Классический", "Дзен", "Для двоих"]
        self.STUDY = "Тренировка"
        self.WxH = (15, 15)
        self.cellsize = 60
        self.net = 0
        self.game_on = True
        self.font = ('Chalkduster', 20)
        self.score = 0
        self.level = 0
        self.keystages = [15, 30, 45, 60, 80, 100]
        self.colors = ['#FF2222', '#FFEE00', '#55FF55', '#00C6E6', '#6666FF', '#FFFFFF', '#000000']
        self.times = [10, 11.5, 13, 14.5, 16, 17.5, 19]
        self.titles = ["Элементарно", "Легко", "Средне", "Сложно", "Хардкор", "Экстрим", "Ультра"]
        self.dzen_time = 60
        
        self.form = Form(self)
        self.effect_node = EffectNode(parent=self)
        self.game_node = Node(parent=self.effect_node)
        self.menu = MenuScene("Выбор режима", "", ["Тренировка"] + self.modes)
        self.present_modal_scene(self.menu)
        
    
    def update_labels(self):
        if self.game_on:
            self.timel.text = "Время: " + str(round(self.time_left(), 1)) + "s"
        else:
            self.timel.text = "КОНЕЦ"
        self.levell.text = "Уровень: " + str(self.level) + (" (" + self.get_title(self.level) + ")" if self.mode == MODE_CLASSIC else "")
        self.scorel.text = "Очки: " + str(self.score)
    
    def time_left(self, t=None):
        if t is None:
            return -(self.t - self.start_time) + self.game_time
        else:
            self.game_time = t + (self.t - self.start_time)
    
    
    def update(self):
        if not self.inited:
            return
        if self.game_on:
            self.game_on = self.time_left() > 0
            if not self.game_on and self.study:
                self.time_show_start = self.t
                self.net.clean()
                self.net.setstate(*self.start, CELLSTATE_FULL)
                self.current = self.start[:]
            self.update_labels()
            
        elif self.study:
            time_spent = self.t - self.time_show_start
            r = int(time_spent / 0.25)
            if r < len(self.answer):
                self.net.setstate(*self.answer[r], CELLSTATE_FULL)

    
    def get_stage(self, d):
        r = 0
        for i in range(len(self.keystages)):
            if d < self.keystages[i]:
                return r
            r += 1
        return r
    
    def get_color(self, d): 
        return self.colors[self.get_stage(d)]
    
    def get_start_time(self, d):
        return self.times[self.get_stage(d)]
    
    def get_title(self, d):
        return self.titles[self.get_stage(d)]
    
    def popupt(self, text, position_, font_=("Arial", 30), color_="white"):
        label = LabelNode(text, font=font_, color=color_, parent=self, position=position_)
        label.run_action(A.sequence(A.wait(1), A.call(label.remove_from_parent)))
    
    def eff_explosion(self, ch):
        self.game_node.add_child(Explosion(ch))
    
    def reset_net(self, diff, color):
        pattern, start, self.answer = Net.random(self.WxH, (1, 1), int(diff / 1.8) + 7)
        left = (int(self.size.w) - self.WxH[0] * self.cellsize) // 2
        top = (int(self.size.h) - self.WxH[1] * self.cellsize) // 2
        self.net = Net((left, top), self.WxH, self.cellsize, self, color=color)
        for x in range(self.WxH[0]):
            for y in range(self.WxH[1]):
                self.net.setstate(x, y, CELLSTATE_EMPTY if pattern.getstate(x, y) == CELLSTATE_FULL else CELLSTATE_NONE)
        self.net.setstate(*start, CELLSTATE_FULL)
        self.start = start
        self.current = start[:]
        self.line = [self.start]
    
    def get_num(self, max):
        for i in range(max):
            if random.random() < 0.5:
                return i
        return i
    
    def __reset_level_cl(self):
        self.reset_net(self.level, self.get_color(self.level) if not self.study else random.choice(self.colors))
        self.game_time = self.get_start_time(self.level)
        self.start_time = self.t
    
    def __reset_level_dz(self):
        diff = self.get_num(7) * 15
        self.reset_net(diff, self.get_color(diff))
    
    def reset_level(self, mode):
        if self.net:
            self.net.destroy(self.eff_explosion)
        if mode == MODE_CLASSIC:
            self.__reset_level_cl()
        elif mode == MODE_DZEN:
            self.__reset_level_dz()
    
    def win(self, mode):
        self.score += self.count_score(self.net, self.t - self.start_time, self.level)
        self.level += 1
        if mode == MODE_DZEN:
            self.game_time += self.net.count_stated(CELLSTATE_FULL) / 7
            if self.dzen_time < self.time_left():
                self.time_left(self.dzen_time)
        self.reset_level(mode)
        self.update_labels()
    
    def count_score(self, net, time_left, level):
        r = 0
        for x, y in net.enum():
            r += net.getstate(x, y) == CELLSTATE_FULL
        return int(r * time_left ** 0.3 * (level + 1) ** 0.3)
    
    def touch_began(self, touch, tap=True):
        if self.form.on_tap(touch):
            return
        if not self.game_on:
            return
        i, j = self.net.loc2ij(touch.location)
        if i == self.current[0] and j == self.current[1]:
            return
        if self.net.getstate(i, j) == CELLSTATE_FULL:
            if not tap:
                x = len(self.line) - 2
                if self.line[x][0] == i and self.line[x][1] == j:
                    if Net.common_side(*self.line[x], *self.current):
                        self.line = self.line[:x+1]
                        self.net.clean()
                        self.net.setmultistate(self.line, CELLSTATE_FULL)
                        self.current = self.line[-1][:]
            else:
                for x in range(len(self.line)):
                    if self.line[x][0] == i and self.line[x][1] == j:
                        self.line = self.line[:x+1]
                        self.net.clean()
                        self.net.setmultistate(self.line, CELLSTATE_FULL)
                        self.current = self.line[-1][:]
                        break
        if Net.common_side(*self.current, i, j) and self.net.getstate(i, j) == CELLSTATE_EMPTY:
            self.net.setstate(i, j, CELLSTATE_FULL)
            self.current = (i, j)
            self.line.append((i, j))
        if self.net.full():
            self.win(self.mode)
        '''
        if not self.net.nearempty(*self.current):
            self.net.clean()
            self.net.setstate(*self.start, CELLSTATE_FULL)
            self.current = self.start[:]
        '''
    
    def touch_moved(self, touch):
        self.touch_began(touch, False)
        

run(Game(), LANDSCAPE, show_fps=True)
