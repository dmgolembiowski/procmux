from typing import Callable, List

from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit
from prompt_toolkit.widgets import Button, TextArea

from app.context import ProcMuxContext
from app.interpolation import Interpolation
from app.log import logger
from app.tui.focus import FocusManager
from app.tui.keybindings import register_app_wide_configured_keybindings, register_configured_keybinding
from app.tui.style import height_100, width_100


class CommandForm:
    def __init__(self,
                 focus_manager: FocusManager,
                 proc_idx: int,
                 on_start: Callable,
                 on_cancel: Callable):
        assert on_start
        assert on_cancel
        self._ctx = ProcMuxContext()
        self._focus_manager = focus_manager
        self._interpolations = self.get_interpolations_for_process_id(proc_idx)
        self._tab_idx = 0

        start_button = Button(
            text='Start',
            handler=lambda: on_start(self._collect_input_as_interpolations()))
        cancel_button = Button(
            text='Cancel',
            handler=on_cancel)
        prompt_template = self._ctx.config.layout.field_replacement_prompt
        self._text_inputs = [
            TextArea(
                height=1,
                prompt=prompt_template.replace('__FIELD_NAME__', interp.field),
                style="class:input-field",
                multiline=False,
                wrap_lines=False,
                text=interp.default_value,
                focus_on_click=True,
            ) for interp in self._interpolations
        ]
        self._focusable_components = [
            *self._text_inputs,
            start_button,
            cancel_button
        ]
        self._move_cursors_to_last_character()
        self._container = HSplit([
            *self._text_inputs,
            VSplit([
                start_button,
                cancel_button
            ])],
            width=width_100,
            height=height_100,
            key_bindings=self._get_keybindings())

    def _move_cursors_to_last_character(self):
        for ti in self._text_inputs:
            buff = ti.control.buffer
            buff.cursor_position = len(buff.document.current_line_after_cursor)

    def _get_keybindings(self):
        kb = KeyBindings()

        def next_input(_event):
            logger.info('next_input - focusing on next tab index')
            self._tab_idx = (self._tab_idx + 1) % len(self._focusable_components)
            current_input = self._focusable_components[self._tab_idx]
            app = get_app()
            app.layout.focus(current_input)

        kb = register_configured_keybinding('next_input', next_input, kb)
        return kb

    def __pt_container__(self):
        return self._container

    def _collect_input_as_interpolations(self):
        final_input_interpolations = []
        for input_field, interp in zip(self._text_inputs, self._interpolations):
            final_input_interpolations.append(Interpolation(
                field=interp.field,
                value=input_field.text,
                default_value=interp.default_value
            ))
        return final_input_interpolations

    @staticmethod
    def get_interpolations_for_process_id(proc_idx: int) -> List[Interpolation]:
        ctx = ProcMuxContext()
        proc_name = ctx.tui_state.process_name_list[proc_idx]
        proc = ctx.config.procs[proc_name]
        interpolations = proc.interpolations
        return interpolations