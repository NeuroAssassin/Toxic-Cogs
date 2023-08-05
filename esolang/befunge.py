from typing import List
from enum import Enum
import random
import io


# Utility
class Mode(Enum):
    LITERAL = 1
    STRING = 2


class Point:
    def __init__(self):
        self.x = 0
        self.y = 0

    def move(self, direction: List[int]) -> None:
        self.x += direction[0]
        self.y += direction[1]


DIRECTIONS = [[1, 0], [0, 1], [-1, 0], [0, -1]]


# Exceptions
class EmptyStack(SyntaxError):
    """Raised when the the stack is accessed in an empty state"""

    def __init__(self, message: str, codemap: List[List[str]], position: Point):
        super().__init__(
            message,
            ("program.befunge", position.y + 1, position.x + 1, "".join(codemap[position.y])),
        )


class UnknownSymbol(SyntaxError):
    def __init__(self, message: str, codemap: List[List[str]], position: Point):
        super().__init__(
            message,
            ("program.befunge", position.y + 1, position.x + 1, "".join(codemap[position.y])),
        )


class NoTermination(SyntaxError):
    def __init__(self, message: str, code: str):
        if len(code) > 50:
            code = code[-50:]
            ptr = 50
        else:
            ptr = len(code)
        super().__init__(
            message,
            ("program.befunge", 1, ptr, code),
        )


# Core classes


class Stack:
    def __init__(self, codemap: List[List[str]], pointer: Point):
        self._internal: List[int] = []
        self.codemap: List[List[str]] = codemap
        self.pointer = pointer

    def push(self, value: int) -> None:
        self._internal.append(value)

    def __pop(self) -> int:
        return self._internal.pop()

    def pop(self) -> int:
        try:
            return self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in pop call", self.codemap, self.pointer)

    def addition(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in addition call", self.codemap, self.pointer)
        self.push(a + b)

    def subtraction(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in subtraction call", self.codemap, self.pointer)
        self.push(a - b)

    def multiplication(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in multiplication call", self.codemap, self.pointer)
        self.push(a * b)

    def division(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in division call", self.codemap, self.pointer)
        self.push(a // b)

    def modulo(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in modulo call", self.codemap, self.pointer)
        self.push(a % b)

    def lnot(self) -> None:
        try:
            a = self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in logical not call", self.codemap, self.pointer)
        self.push(1 if a == 0 else 0)

    def greater(self) -> None:
        try:
            a, b = self.__pop(), self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in logical greater call", self.codemap, self.pointer)
        self.push(1 if b > a else 0)

    def underscore(self) -> List[int]:
        try:
            a = self.__pop()
        except IndexError:
            a = 0
        if a == 0:
            return [1, 0]
        else:
            return [-1, 0]

    def pipe(self) -> List[int]:
        try:
            a = self.__pop()
        except IndexError:
            a = 0
        if a == 0:
            return [0, 1]
        else:
            return [0, -1]

    def duplicate(self) -> None:
        try:
            a = self.__pop()
        except IndexError:
            a = 0
        self.push(a)
        self.push(a)

    def swap(self) -> None:
        try:
            a = self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in swap call", self.codemap, self.pointer)

        try:
            b = self.__pop()
        except IndexError:
            b = 0
        self.push(a)
        self.push(b)


class Befunge:
    @staticmethod
    def check_syntax(code: str) -> None:
        if "@" not in code:
            raise NoTermination("Program does not terminate", code)
        if code.count('"') % 2 != 0:
            raise NoTermination("Program has an un-ending stringmode segment", code)

    @staticmethod
    def buildcodemap(code: str) -> List[List[str]]:
        codemap = code.split("\n")
        max_segment = 0
        for index, segment in enumerate(codemap):
            codemap[index] = [x for x in segment]
            max_segment = max((max_segment, len(codemap[index])))

        for i in range(len(codemap)):
            try:
                if len(codemap[i]) == 0:
                    del codemap[i]
            except IndexError:
                # We have to catch this here because we are modifying the list
                # and so the indexes will become invalid
                break

        for index, segment in enumerate(codemap):
            if len(codemap[index]) < max_segment:
                codemap[index] = codemap[index] + ([" "] * (max_segment - len(codemap[index])))
        return codemap

    @staticmethod
    async def evaluate(code: str) -> io.StringIO:
        Befunge.check_syntax(code)

        codemap: List[List[str]] = Befunge.buildcodemap(code)
        pointer: Point = Point()
        stack: Stack = Stack(codemap, pointer)

        mode: int = Mode.LITERAL
        direction: List[int] = [1, 0]
        output = io.StringIO("")
        skip_next = False
        counter: int = 0

        while counter < 100000:
            try:
                assert pointer.y > -1
                row: List[str] = codemap[pointer.y]
            except (IndexError, AssertionError):
                if pointer.y == -1 and direction[1] == 1:
                    pointer.y += 1
                    continue
                elif pointer.y == -1 and direction[1] == -1:
                    pointer.y = len(codemap) - 1
                    continue
                elif pointer.y == len(codemap) and direction[1] == 1:
                    pointer.y = 0
                    continue
                elif pointer.y == len(codemap) and direction[1] == -1:
                    pointer.y = len(codemap) - 1
                    continue

            try:
                assert pointer.x > -1
                char: str = row[pointer.x]
            except (IndexError, AssertionError):
                if pointer.x == -1 and direction[0] == 1:
                    pointer.x += 1
                    continue
                elif pointer.x == -1 and direction[0] == -1:
                    pointer.x = len(row) - 1
                    continue
                elif pointer.x == len(row) and direction[0] == 1:
                    pointer.x = 0
                    continue
                elif pointer.x == len(row) and direction[0] == -1:
                    pointer.x = len(row) - 1
                    continue

            if skip_next:
                pointer.move(direction)
                skip_next = False
                continue

            if mode == Mode.LITERAL:
                if char == ">":
                    direction = [1, 0]
                elif char == "<":
                    direction = [-1, 0]
                elif char == "^":
                    direction = [0, -1]
                elif char == "v":
                    direction = [0, 1]
                elif char == "?":
                    direction = random.choice(DIRECTIONS)
                elif char == "+":
                    stack.addition()
                elif char == "-":
                    stack.subtraction()
                elif char == "*":
                    stack.multiplication()
                elif char == "/":
                    stack.division()
                elif char == "%":
                    stack.modulo()
                elif char == "!":
                    stack.lnot()
                elif char == "`":
                    stack.greater()
                elif char == "_":
                    direction = stack.underscore()
                elif char == "|":
                    direction = stack.pipe()
                elif char == ":":
                    stack.duplicate()
                elif char == "\\":
                    stack.swap()
                elif char == "$":
                    stack.pop()
                elif char == ".":
                    output.write(str(stack.pop()))
                    output.write(" ")
                elif char == ",":
                    output.write(chr(stack.pop()))
                elif char == "#":
                    skip_next = True
                elif char == "@":
                    return output, stack._internal
                elif char == '"':
                    mode = Mode.STRING
                elif char == " ":
                    pass
                elif char.isdigit():
                    stack.push(int(char))
                else:
                    raise UnknownSymbol(char, codemap, pointer)
            elif mode == Mode.STRING:
                if char == '"':
                    mode = Mode.LITERAL
                else:
                    stack.push(ord(char))
            pointer.move(direction)
            counter += 1
        return output, stack._internal
