from typing import List
import io


# Exceptions
class EmptyStack(SyntaxError):
    """Raised when the the stack is accessed in an empty state"""

    def __init__(self, message: str, code: str, pointer: int):
        if pointer > 50:
            line = pointer // 50
            start = line * 50
            code = code[start : start + 50]
            pointer %= 50
        else:
            line = 0
        super().__init__(
            message,
            ("program.ws", line + 1, pointer + 1, code),
        )


class InvalidNumber(SyntaxError):
    """Raised when a number fails to be parsed"""

    def __init__(self, message: str, code: str, pointer: int):
        if pointer > 50:
            line = pointer // 50
            start = line * 50
            code = code[start : start + 50]
            pointer %= 50
        else:
            line = 0
        super().__init__(
            message,
            ("program.ws", line + 1, pointer + 1, code),
        )


# Core classes


class Stack:
    def __init__(self, code: str):
        self._internal: List[int] = []
        self.code = code
        self.pointer: int = 0

    def push(self, value: int) -> None:
        self._internal.append(value)

    def __pop(self) -> int:
        return self._internal.pop()

    def pop(self) -> int:
        try:
            return self.__pop()
        except IndexError:
            raise EmptyStack("Empty stack in pop call", self.code, self.pointer)

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
            raise EmptyStack("Empty stack in swap call", self.code, self.pointer)

        try:
            b = self.__pop()
        except IndexError:
            b = 0
        self.push(a)
        self.push(b)

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


class Whitespace:
    @staticmethod
    def clean_syntax(code: str) -> str:
        if code.startswith("```\n"):
            code = code[4:]
        if code.endswith("\n```"):
            code = code[:-4]
        code = "".join(filter(lambda x: x in ["\u2001", " ", "\n"], code))
        code = code.replace("\u2001", "t").replace(" ", "s").replace("\n", "l")
        return code

    @staticmethod
    def parse_to_number(stack: Stack, number: str) -> int:
        try:
            sign = 1 if number[0] == "s" else -1

            number = number[1:].replace("s", "0").replace("t", "1")
            number = int(number, 2)
            return number * sign
        except IndexError:
            raise InvalidNumber(
                "Incorrect number: must be at least two chars", stack.code, stack.pointer
            )

    @staticmethod
    def evaluate(code: str) -> io.StringIO:
        code: str = Whitespace.clean_syntax(code)
        stack: Stack = Stack(code)
        command: str = ""
        param: str = ""

        output: io.StringIO = io.StringIO("")

        while stack.pointer <= len(code):
            print(command)
            print(stack._internal)
            try:
                target = code[stack.pointer]
            except IndexError:
                target = ""
            if command == "ss":
                if target == "l":
                    number = Whitespace.parse_to_number(stack, param)
                    stack.push(number)
                    command, param = "", ""
                elif target:
                    param += target
                else:
                    raise InvalidNumber(
                        "Incorrect stack push: No argument supplied", stack.code, stack.pointer
                    )
                stack.pointer += 1
                continue
            elif command == "sls":
                stack.duplicate()
                command, param = "", ""
            elif command == "slt":
                stack.swap()
                command, param = "", ""
            elif command == "sll":
                stack.pop()
                command, param = "", ""
            elif command == "tsss":
                stack.addition()
                command, param = "", ""
            elif command == "tsst":
                stack.subtraction()
                command, param = "", ""
            elif command == "tssl":
                stack.multiplication()
                command, param = "", ""
            elif command == "tsts":
                stack.division()
                command, param = "", ""
            elif command == "tstt":
                stack.modulo()
                command, param = "", ""
            elif command == "tlss":
                output.write(chr(stack.pop()))
                command, param = "", ""
            elif command == "tlst":
                output.write(str(stack.pop()))
                command, param = "", ""
            command += target
            stack.pointer += 1
        return output
