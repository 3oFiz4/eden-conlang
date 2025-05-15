from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.document import Document
from prompt_toolkit.application.current import get_app

words = ['thought', 'try', 'to', 'thine', 'tomb', 'think', 'those', 'the']

class WordCompleter(Completer):
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor.lower()
        if not text:
            return
        for word in words:
            if word.startswith(text):
                yield Completion(word, start_position=-len(text))


def main():
    session = PromptSession()
    completer = WordCompleter()
    kb = KeyBindings()

    @kb.add('c-c')
    def _(event):
        """Exit on Ctrl-C"""
        event.app.exit()

    # The prompt_toolkit's default behavior already supports arrow key navigation in completions.
    # So no extra key bindings for arrow keys are necessary.

    print("Start typing (Ctrl-C to exit):")
    while True:
        try:
            text = session.prompt('> ', completer=completer, complete_while_typing=True, key_bindings=kb)
            print(f'You selected: {text}')
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    print("Goodbye!")


if __name__ == '__main__':
    main()
