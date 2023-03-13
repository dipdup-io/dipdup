import linecache
from typing import Optional
from typing import Type

import pretty_errors


class DipdupExceptionWriter(pretty_errors.ExceptionWriter):
    def write_code(
        self, filepath: str, line: int, module_globals: dict, is_final: bool, point_at: Optional[int] = None
    ) -> str:
        # NOTE: removed code print but kept logic for parse and print locals futher in pretty_errors code
        lines = []
        if filepath == '<stdin>':
            lines.append(str(line).rstrip())
            line = target_line = start = end = 0
        else:
            if is_final:
                target_line = self.config.lines_before
                start = line - self.config.lines_before
                end = line + self.config.lines_after
            else:
                target_line = self.config.trace_lines_before
                start = line - self.config.trace_lines_before
                end = line + self.config.trace_lines_after

            if start < 1:
                target_line -= 1 - start
                start = 1

            for i in range(start, end + 1):
                lines.append(linecache.getline(filepath, i, module_globals).rstrip())

        min_lead = None
        for line in lines:
            if line.strip() == '':
                continue
            c = 0
            while c < len(line) and line[c] in (' ', '\t'):
                c += 1
            if min_lead is None or c < min_lead:
                min_lead = c
        if min_lead is None:
            min_lead = 0
        if min_lead > 0:
            lines = [line[min_lead:] for line in lines]

        line_length = self.get_line_length()

        for i, line in enumerate(lines):
            if i == target_line:
                color = self.config.line_color
                if point_at is not None:
                    point_at -= min_lead + 1
            else:
                color = self.config.code_color
            color_length = self.visible_length(color)
            if self.config.truncate_code and len(line) + color_length > line_length:
                line = line[: line_length - color_length + 3] + '...'
            if i == target_line and point_at is not None:
                if point_at >= line_length:
                    point_at = line_length - 1
                start_char = point_at
                while start_char > 0 and line[start_char - 1] not in (' ', '\t'):
                    start_char -= 1
                end_char = point_at + 1
                while end_char < len(line) - 1 and line[end_char] not in (' ', '\t'):
                    end_char += 1

        return '\n'.join(lines)

    def write_location(self, path: str, line: str, function: str) -> None:
        # NOTE: printing all location concatinated in one line
        line_number = f' {line} '
        if 'python' in path:
            return
        self.output_text(
            [
                self.config.filename_color,
                path,
                self.config.line_number_color,
                line_number,
                self.config.function_color,
                function,
            ]
        )
        if self.config.display_link:
            self.write_link(path, line)

    def write_header(self) -> None:
        # NOTE: removed header
        pass

    def write_exception(self, exception_type: Type[Exception], exception_value: Exception) -> None:
        if exception_value and len(exception_value.args) > 0:
            output = [
                self.config.exception_color,
                self.exception_name(exception_type),
                ': ',
                self.config.exception_arg_color,
                ', '.join((str(x) for x in exception_value.args)),
            ]
        else:
            output = [self.config.exception_color, self.exception_name(exception_type)]

        self.output_text(output)


def invoke_excepthook() -> None:
    pretty_errors.configure(
        filename_display=pretty_errors.FILENAME_FULL,
        truncate_code=True,
        line_number_first=True,
        line_color=pretty_errors.RED + '> ' + pretty_errors.default_config.line_color,
        code_color='  ' + pretty_errors.default_config.line_color,
        display_locals=False,  # TODO: rewrite locals logic
        display_arrow=False,
        full_line_newline=False,
        line_length=200,
        show_suppressed=True,
    )

    pretty_errors.exception_writer = DipdupExceptionWriter()
