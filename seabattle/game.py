# coding: utf-8

from __future__ import unicode_literals

import random
import re

from transliterate import translit

EMPTY = 0
SHIP = 1
BLOCKED = 2
HIT = 3
MISS = 4


class BaseGame(object):
    position_patterns = [re.compile('^([a-zа-я]+)(\d+)$', re.UNICODE),  # a1
                         re.compile('^([a-zа-я]+)\s+(\w+)$', re.UNICODE),  # a 1; a один
                         re.compile('^(\w+)\s+(\w+)$', re.UNICODE),  # a 1; a один; 7 10
                         ]

    str_letters = ['а', 'б', 'в', 'г', 'д', 'е', 'ж', 'з', 'и', 'к']
    str_numbers = ['один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять', 'десять']

    letters_mapping = {
        'the': 'з',
        'за': 'з',
        'уже': 'ж',
        'трень': '3',
    }

    default_ships = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

    def __init__(self):
        self.size = 0
        self.ships = None
        self.field = []
        self.enemy_field = []

        self.ships_count = 0
        self.enemy_ships_count = 0

        self.last_shot_position = None
        self.last_enemy_shot_position = None
        self.numbers = None
        
        self.shot_queue = []
        self.previous_shots = []

    def start_new_game(self, size=10, field=None, ships=None, numbers=None):
        assert(size <= 10)
        assert(len(field) == size ** 2 if field is not None else True)

        self.size = size
        self.numbers = numbers if numbers is not None else False

        if ships is None:
            self.ships = self.default_ships
        else:
            self.ships = ships

        if field is None:
            self.generate_field()
        else:
            self.field = field

        self.enemy_field = [EMPTY] * self.size ** 2

        self.ships_count = self.enemy_ships_count = len(self.ships)
        print '%s' % self.enemy_ships_count

        self.last_shot_position = None
        self.last_enemy_shot_position = None

        self.generate_shot_queue()

    def generate_field(self):
        raise NotImplementedError()

    def generate_shot_queue(self):
        raise NotImplementedError()

    def block_ship_surround_cells(self, position):
        raise NotImplementedError()

    def target_shot_queue_to_ship(self, position):
        raise NotImplementedError()

    def print_field(self):
        mapping = ['0', '1', 'x']

        print '-' * (self.size + 2)
        for y in range(self.size):
            print '|%s|' % ''.join(mapping[x] for x in self.field[y * self.size: (y + 1) * self.size])
        print '-' * (self.size + 2)

    def handle_enemy_shot(self, position):
        index = self.calc_index(position)

        if self.field[index] in (SHIP, HIT):
            self.field[index] = HIT

            if self.is_dead_ship(index):
                self.ships_count -= 1
                return 'kill'
            else:
                return 'hit'
        else:
            return 'miss'

    def is_dead_ship(self, last_index):
        x, y = self.calc_position(last_index)
        x -= 1
        y -= 1

        def _line_is_dead(line, index):
            def _tail_is_dead(tail):
                for i in tail:
                    if i == HIT:
                        continue
                    elif i == SHIP:
                        return False
                    else:
                        return True
                return True

            return _tail_is_dead(line[index:]) and _tail_is_dead(line[index::-1])

        return (
            _line_is_dead(self.field[x::self.size], y) and
            _line_is_dead(self.field[y * self.size:(y + 1) * self.size], x)
        )

    def is_end_game(self):
        return self.is_victory() or self.is_defeat()

    def is_victory(self):
        return self.enemy_ships_count < 1

    def is_defeat(self):
        return self.ships_count < 1

    def do_shot(self):
        raise NotImplementedError()

    def repeat(self):
        return self.convert_from_position(self.last_shot_position, numbers=True)

    def reset_last_shot(self):
        self.last_shot_position = None

    def handle_enemy_reply(self, message):
        if self.last_shot_position is None:
            return

        index = self.calc_index(self.last_shot_position)

        if message in ['hit', 'kill']:
            self.enemy_field[index] = SHIP
            self.target_shot_queue_to_ship(self.last_shot_position)
            print 'SHIP'

            if message == 'kill':
                self.enemy_ships_count -= 1
                self.block_ship_surround_cells(self.last_shot_position)
                print 'KILL'

        elif message == 'miss':
            self.enemy_field[index] = MISS

    def calc_index(self, position):
        x, y = position

        if x > self.size or y > self.size:
            raise ValueError('Wrong position: %s %s' % (x, y))

        return (y - 1) * self.size + x - 1

    def calc_position(self, index):
        y = index / self.size + 1
        x = index % self.size + 1

        return x, y

    def convert_to_position(self, position):
        position = position.lower()
        for pattern in self.position_patterns:
            match = pattern.match(position)

            if match is not None:
                break
        else:
            raise ValueError('Can\'t parse entire position: %s' % position)

        bits = match.groups()

        def _try_letter(bit):
            # проверяем особые случаи неправильного распознования STT
            bit = self.letters_mapping.get(bit, bit)

            # преобразуем в кириллицу
            bit = translit(bit, 'ru')

            try:
                return self.str_letters.index(bit) + 1
            except ValueError:
                raise

        def _try_number(bit):
            # проверяем особые случаи неправильного распознования STT
            bit = self.letters_mapping.get(bit, bit)

            if bit.isdigit():
                return int(bit)
            else:
                try:
                    return self.str_numbers.index(bit) + 1
                except ValueError:
                    raise

        x = bits[0].strip()
        try:
            x = _try_letter(x)
        except ValueError:
            try:
                x = _try_number(x)
            except ValueError:
                raise ValueError('Can\'t parse X point: %s' % x)

        y = bits[1].strip()
        try:
            y = _try_number(y)
        except ValueError:
            raise ValueError('Can\'t parse Y point: %s' % y)

        return x, y

    def convert_from_position(self, position, numbers=None):
        numbers = numbers if numbers is not None else self.numbers

        if numbers:
            x = position[0]
        else:
            x = self.str_letters[position[0] - 1]

        y = position[1]

        return '%s, %s' % (x, y)


class Game(BaseGame):
    """Реализация игры с ипользованием обычного random"""

    def generate_field(self):
        """Метод генерации поля"""
        self.field = [0] * self.size ** 2

        for length in self.ships:
            self.place_ship(length)

        for i in range(len(self.field)):
            if self.field[i] == BLOCKED:
                self.field[i] = EMPTY

    def place_ship(self, length):
        def _try_to_place():
            x = random.randint(1, self.size)
            y = random.randint(1, self.size)
            direction = random.choice([1, self.size])

            index = self.calc_index((x, y))
            values = self.field[index:None if direction == self.size else index + self.size - index % self.size:direction][:length]

            if len(values) < length or any(values):
                return False

            for i in range(length):
                current_index = index + direction * i

                for j in [0, 1, -1]:
                    if (j != 0
                            and current_index % self.size in (0, self.size - 1)
                            and (current_index + j) % self.size in (0, self.size - 1)):
                        continue

                    for k in [0, self.size, -self.size]:
                        neighbour_index = current_index + k + j

                        if (neighbour_index < 0
                                or neighbour_index >= len(self.field)
                                or self.field[neighbour_index] == SHIP):
                            continue

                        self.field[neighbour_index] = BLOCKED

                self.field[current_index] = SHIP

            return True

        while not _try_to_place():
            pass

    def generate_shot_queue(self):
        """
        Генерируем очередь стрельбы
        """

        positions = []
        if self.size == 10:
            positions = [(1, 4), (2, 3), (3, 2), (4, 1), (1, 8), (2, 7), (3, 6), (4, 5), (5, 4), (6, 3), (7, 2), (8, 1),
            (3, 10), (4, 9), (5, 8), (6, 7), (7, 6), (8, 5), (9, 4), (10, 3), (7, 10), (8, 9), (9, 8), (10, 7), (1, 2), (2, 1),
            (1, 6), (2, 5), (3, 4), (2, 5), (1, 6), (1, 10), (2, 9), (3, 8), (4, 7), (5, 6), (6, 5), (7, 4), (8, 3), (9, 2), (10, 1),
            (5, 10), (6, 9), (7, 8), (8, 7), (9, 6), (10, 5), (9, 10), (10, 9), (1, 1), (1, 3), (2, 2)]
        else:
            positions = []


        for i in range(self.size):
            for j in range(self.size):
                if (i, j) not in positions:
                    positions.append((i,j))

        for position in positions:
            self.shot_queue.append(self.calc_index(position))
    
    def block_ship_surround_cells(self, position):
        x, y = position

        rows = range(max(0, x - 1), min(x + 2, self.size))
        cols = range(max(0, y - 1), min(y + 2, self.size))

        for row in rows:
            for col in cols:
                index = self.calc_index((row, col))
                if index in self.shot_queue:
                    self.shot_queue.remove(index)
    
    def target_shot_queue_to_ship(self, position):

        x, y = position

        positions_to_add = [
            (x - 1, y), (x + 1, y), 
            (x - 2, y), (x + 2, y), 
            (x - 3, y), (x + 3, y), 
            (x, y - 1), (x, y + 1), 
            (x, y - 2), (x, y + 2), 
            (x, y - 3), (x, y + 3), 
        ]
        
        for pos in positions_to_add:

            row, col = pos
            if row > self.size or col > self.size or row <= 0 or col <= 0:
                continue

            try:
                index = self.calc_index(position)
            except:
                continue

            self.shot_queue.insert(0, index)

        def remove_duplicates(values):
            output = []
            seen = set()
            for value in values:
                if value not in seen:
                    output.append(value)
                    seen.add(value)
            return output

        self.shot_queue = remove_duplicates(self.shot_queue)

    def do_shot(self):
        """Метод выбора координаты выстрела.

        ЕГО И НУЖНО ЗАМЕНИТЬ НА СВОЙ АЛГОРИТМ
        """

        try:    
            self.print_field()
        except:
            pass

        print "queue %s" % self.shot_queue

        for i in self.shot_queue:
            if i not in self.previous_shots:
                index = self.shot_queue.pop(0)
                self.previous_shots.append(index)
                break
            else:
                self.shot_queue.remove(i)
                continue
                
        self.last_shot_position = self.calc_position(index)
        return self.convert_from_position(self.last_shot_position)
