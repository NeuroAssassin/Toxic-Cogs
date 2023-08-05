import io


class COW:
    instruction_mapping = {
        0: "moo",
        1: "mOo",
        2: "moO",
        3: "mOO",
        4: "MOo",
        5: "MoO",
        6: "MOO",
        7: "MOO",
        8: "OOO",
        9: "MMM",
        10: "OOM",
    }

    @staticmethod
    def cleanup(code):
        return "".join(filter(lambda x: x in ["m", "o", "M", "O"], code))

    @staticmethod
    def getlines(code):
        return [code[i : i + 50] for i in range(0, len(code), 50)]

    @staticmethod
    def buildbracemap(code):
        temp_bracestack, bracemap = [], {}
        for position, command in enumerate(code):
            if command == "MOO":
                temp_bracestack.append(position)
            elif command == "moo":
                start = temp_bracestack.pop()
                bracemap[start] = position
                bracemap[position] = start
        if temp_bracestack:
            lines = COW.getlines("".join(code))
            raise SyntaxError(
                "Trailing MOO", ("program.moo", len(lines), len(lines[-1]), lines[-1])
            )
        return bracemap

    @staticmethod
    def evaluate(code):
        code = COW.cleanup(code)

        if len(code) % 3 != 0:
            lines = COW.getlines(code)
            raise SyntaxError(
                "Trailing command", ("program.moo", len(lines), len(lines[-1]), lines[-1])
            )
        code = [code[i : i + 3] for i in range(0, len(code), 3)]

        bracemap = COW.buildbracemap(code)
        cells, codeptr, cellptr, prev, registry = [0], 0, 0, -1, -1
        output = io.StringIO("")

        while codeptr < len(code):
            command = code[codeptr]
            if command == "moO":
                cellptr += 1
                if cellptr == len(cells):
                    cells.append(0)
            elif command == "mOo":
                cellptr = 0 if cellptr <= 0 else cellptr - 1
            elif command == "MoO":
                cells[cellptr] = cells[cellptr] + 1 if cells[cellptr] < 255 else 0
            elif command == "MOo":
                cells[cellptr] = cells[cellptr] - 1 if cells[cellptr] > 0 else 255
            elif command == "MOO":
                if cells[cellptr] == 0:
                    codeptr = bracemap[codeptr]
                else:
                    prev = cells[cellptr]
            elif command == "moo":
                if cells[cellptr] == 0:
                    prev = 0
                else:
                    if cells[cellptr] == prev:
                        lines = COW.getlines("".join(code))
                        errorptr = ((codeptr * 3) % 50) + 3
                        raise SyntaxError(
                            "Infinite loop: MOO/moo",
                            ("program.moo", len(lines), errorptr, lines[-1]),
                        )
                    else:
                        codeptr = bracemap[codeptr]
            elif command == "Moo":
                output.write(chr(cells[cellptr]))
            elif command == "mOO":
                try:
                    code[codeptr] = COW.instruction_mapping[cells[cellptr]]
                except KeyError:
                    lines = COW.getlines("".join(code))
                    errorptr = ((codeptr * 3) % 50) + 3
                    raise SyntaxError(
                        f"Invalid mOO execution in memory address {cellptr}: {cells[cellptr]}",
                        ("program.moo", len(lines), errorptr, lines[-1]),
                    )
                if code[codeptr] == "mOO":
                    lines = COW.getlines("".join(code))
                    errorptr = ((codeptr * 3) % 50) + 3
                    raise SyntaxError(
                        "Infinite loop: mOO", ("program.moo", len(lines), errorptr, lines[-1])
                    )
                continue
            elif command == "MMM":
                if registry == -1:
                    registry = cells[cellptr]
                else:
                    cells[cellptr] = registry
                    registry = -1
            elif command == "OOO":
                cells[cellptr] = 0
            elif command == "OOM":
                output.write(str(cells[cellptr]))
            else:
                lines = COW.getlines("".join(code))
                errorptr = ((codeptr * 3) % 50) + 3
                raise SyntaxError(
                    "Invalid COW command", ("program.moo", len(lines), errorptr, lines[-1])
                )

            codeptr += 1
        return output, cells
