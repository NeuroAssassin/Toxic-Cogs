import io


class Brainfuck:
    @staticmethod
    def cleanup(code):
        return "".join(filter(lambda x: x in [".", "[", "]", "<", ">", "+", "-"], code))

    @staticmethod
    def getlines(code):
        return [code[i : i + 50] for i in range(0, len(code), 50)]

    @staticmethod
    def buildbracemap(code):
        temp_bracestack, bracemap = [], {}
        for position, command in enumerate(code):
            if command == "[":
                temp_bracestack.append(position)
            elif command == "]":
                start = temp_bracestack.pop()
                bracemap[start] = position
                bracemap[position] = start
        return bracemap

    @staticmethod
    def evaluate(code):
        code = Brainfuck.cleanup(list(code))
        bracemap = Brainfuck.buildbracemap(code)
        cells, codeptr, cellptr, prev = [0], 0, 0, -1

        output = io.StringIO("")

        while codeptr < len(code):
            command = code[codeptr]
            if command == ">":
                cellptr += 1
                if cellptr == len(cells):
                    cells.append(0)
            elif command == "<":
                cellptr = 0 if cellptr <= 0 else cellptr - 1
            elif command == "+":
                cells[cellptr] = cells[cellptr] + 1 if cells[cellptr] < 255 else 0
            elif command == "-":
                cells[cellptr] = cells[cellptr] - 1 if cells[cellptr] > 0 else 255
            elif command == "[":
                if cells[cellptr] == 0:
                    codeptr = bracemap[codeptr]
                else:
                    prev = cells[cellptr]
            elif command == "]":
                if cells[cellptr] == 0:
                    prev = 0
                else:
                    if cells[cellptr] == prev:
                        lines = Brainfuck.getlines("".join(code))
                        errorptr = codeptr % 50
                        raise SyntaxError(
                            f"Infinite loop: []", ("program.bf", len(lines), errorptr, lines[-1])
                        )
                    else:
                        codeptr = bracemap[codeptr]
            elif command == ".":
                output.write(chr(cells[cellptr]))

            codeptr += 1
        return output, cells
