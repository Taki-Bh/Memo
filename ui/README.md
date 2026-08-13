# Aurora — AI Assistant Desktop UI

A production-structured PySide6 desktop shell for an AI assistant: glass +
neumorphic dark theme, a 20/80 sidebar/conversation split, a genuinely
auto-expanding chat composer, Markdown-rendered AI messages, and a fully
**Qt Designer–editable** layout (`.ui` files, not hand-rolled widget
positioning).

```
ai_assistant_ui/
├── main.py                       # entry point, wires everything together
├── requirements.txt
├── ui/                            # Qt Designer forms — edit these visually
│   ├── main_window.ui             # QMainWindow + 20/80 QSplitter
│   ├── sidebar.ui                 # left panel: branding, search, list, utilities, profile
│   ├── chat_view.ui                # right panel: header, message scroll area, composer slot
│   └── composer.ui                 # the floating input capsule
├── widgets/                       # Python: logic + custom Qt Designer–promotable widgets
│   ├── ui_loader.py                # CustomUiLoader — resolves promoted widgets at runtime
│   ├── glass_button.py             # GlassButton(QPushButton) — hover glow animation
│   ├── auto_resize_text_edit.py    # AutoResizeTextEdit(QPlainTextEdit) — the composer's core
│   ├── conversation_item.py        # ConversationItem — one sidebar row + context menu
│   ├── chat_message.py             # ChatMessage — user/AI bubble, Markdown via QTextBrowser
│   ├── typing_indicator.py         # TypingIndicator — animated "Thinking..." row
│   ├── sidebar.py                  # Sidebar — loads sidebar.ui, owns conversation list logic
│   ├── chat_view.py                # ChatView — loads chat_view.ui, owns message list + empty state
│   └── composer.py                 # Composer — loads composer.ui, owns send/char-count logic
└── styles/
    └── theme.qss                   # single centralized stylesheet — colors, glass, neumorphism
```

## 1. Architecture, in one paragraph

`main_window.ui` is a bare `QMainWindow` containing one `QSplitter` with two
empty container widgets (`sidebarContainer`, `chatViewContainer`) — that's
the whole 20/80 split, done with a real Qt layout rather than hardcoded
geometry. `main.py` loads that form with `QUiLoader`, then instantiates two
custom composite widgets — `Sidebar` and `ChatView` — and drops them into
those containers. `Sidebar` and `ChatView` are themselves thin Python
classes whose *only* job is to load their own `.ui` file (`sidebar.ui`,
`chat_view.ui`) and attach behavior (signals/slots) to the widgets defined
there. `ChatView` in turn embeds a `Composer`, which loads `composer.ui`.
Every leaf widget that needs custom behavior (`AutoResizeTextEdit`,
`GlassButton`) is a real promoted-widget class referenced from the `.ui`
XML's `<customwidgets>` block, resolved at load time by `CustomUiLoader`
(see `widgets/ui_loader.py`) — so nothing is built with hundreds of lines
of programmatic `addWidget` calls, and everything stays editable visually.

## 2. Running it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The app launches with demo conversations in the sidebar and a mock
assistant (`MockAssistant` in `main.py`) that echoes a Markdown-formatted
reply ~900ms after you send a message, so you can see the typing indicator,
message rendering, and composer reset all working live. Replace
`MockAssistant.reply_to()` with a real API call (streaming or not) when
you're ready — everything else is already decoupled from it via Qt
signals (`ChatView.messageSent`, `ChatView.add_ai_message(...)`).

## 3. Editing the UI in Qt Designer

Open any form directly:

```bash
pyside6-designer ui/main_window.ui
pyside6-designer ui/sidebar.ui
pyside6-designer ui/chat_view.ui
pyside6-designer ui/composer.ui
```

(`pyside6-designer` ships with the `PySide6` pip package. On some
platforms it's `pyside6-designer.exe` or found via `python -m PySide6.scripts.pyside_tool designer`.)

Because custom widgets (`GlassButton`, `AutoResizeTextEdit`) are declared
in each form's `<customwidgets>` block with a `header` pointing at the
Python module, Designer will show them as their real class in the widget
tree and object inspector — you can select `messageInput`, see it's an
`AutoResizeTextEdit`, and edit its plain-widget properties (size policy,
tooltip, etc.) directly. Designer can't preview our animated/behavioral
code, but every layout, margin, spacing, size, and text property is fully
editable and will apply immediately the next time you run `main.py` — no
recompilation step, since `main.py` loads `.ui` files at runtime via
`QUiLoader` rather than a generated `_ui.py` file.

**No `pyside6-uic` build step is required.** If you'd prefer compiled
`_ui.py` modules (marginally faster startup, static type hints), you can
run `pyside6-uic ui/composer.ui -o ui_composer.py` etc., but you'd then
need to register promoted widgets via `pyside6-uic`'s own promotion
mechanism instead of `CustomUiLoader`.

## 4. Changing the 20/80 sidebar/conversation ratio

Two things control this:

1. **Runtime enforcement** — `main.py`:
   ```python
   SIDEBAR_RATIO = 0.20
   CHAT_RATIO = 0.80
   ```
   `AuroraApp._apply_split_ratio()` calls `rootSplitter.setSizes([...])`
   using these on startup. Change the numbers, done.

2. **Design-time starting point / bounds** — `ui/main_window.ui`, on
   `sidebarContainer`: `minimumSize` (currently 220px) caps how far a user
   can drag the splitter shut. `ui/sidebar.ui`'s root widget also sets
   `minimumSize`/`maximumSize` (220–420px) as a second safety bound. Both
   are plain Designer properties — select the widget in the Property
   Editor and change them, no code required.

If you want the ratio to persist across resizes rather than just on
launch, connect `QSplitter.splitterMoved` (already wired to a no-op in
`main.py`) to save the user's chosen sizes, or call `_apply_split_ratio()`
from a `resizeEvent` override on the main window.

## 5. Changing colors, spacing, shadows, and the glass effect

Everything visual lives in **`styles/theme.qss`** — one file, loaded once
in `main.py` via `app.setStyleSheet(...)`. It's organized into clearly
commented sections (Sidebar / Chat view / Composer) and every rule targets
either an `objectName` (`#conversationItem`, `#composerCard`, ...) or a
dynamic property (`[role="user"]`, `[selected="true"]`, `[active="true"]`).

- **Palette**: the values are called out at the top of the file as a
  comment; search-and-replace the hex/rgba values to retheme everything at
  once (e.g. swap `#5CC8FF` for a different accent).
- **Glass effect**: controlled by the `background-color: rgba(255,255,255,X)`
  + `border: 1px solid rgba(255,255,255,Y)` pairs on `#Sidebar`,
  `#composerCard`, `#messageBubble`, etc. Raise the alpha for a more
  opaque "frosted" look, lower it for more transparency. Qt's QSS doesn't
  support true backdrop blur, so the "glass" look here comes from
  layered semi-transparent panels over the dark background gradient
  rather than a live blur filter — if you need a literal blur-behind
  effect, that requires either a platform-native window backdrop API or
  rendering the background content into a `QGraphicsBlurEffect`-processed
  pixmap, which is a bigger architectural change.
- **Neumorphism / depth**: currently expressed via subtle border +
  background contrast (see `#newConversationButton`, `#sendButton[active="true"]`).
  To add real soft drop shadows, apply a `QGraphicsDropShadowEffect` in
  Python to a given widget (QSS `box-shadow` isn't supported by Qt) —
  a good place is `GlassButton.__init__` or `Composer.__init__` on
  `composerCard`.
- **Spacing/margins**: these are Designer properties on each layout
  (`leftMargin`, `spacing`, etc. in the `.ui` files) — not QSS. Adjust them
  visually in Designer or by hand in the XML.
- **Animation timing**: `AutoResizeTextEdit` (composer expand/collapse)
  and `GlassButton` (hover glow) both use `QPropertyAnimation` with
  `setDuration(...)` calls near the top of their `__init__` — tune those
  directly for snappier/slower motion.

## 6. How the auto-expanding composer works

`widgets/auto_resize_text_edit.py`'s `AutoResizeTextEdit` is a
`QPlainTextEdit` that:

1. Connects to `document().documentLayout().documentSizeChanged` — a real
   Qt signal that fires whenever the *laid-out* size of the document
   changes, whether that's from typed newlines, text wrapping, or content
   being pasted. This is layout-metric-driven, not a `\n`-counting
   heuristic, so long soft-wrapped paragraphs resize correctly too.
2. On that signal, measures `document().size().height()`, clamps it
   between `self.min_height` (52px) and `self.max_height` (220px), and
   animates `minimumHeight`/`maximumHeight` to the target with a 140ms
   `QPropertyAnimation` — smooth, no flicker, no timers.
3. Once the clamped target hits `max_height`, it flips on the vertical
   scrollbar (`ScrollBarAsNeeded`) so further typing scrolls internally
   instead of growing the widget further.
4. Overrides `resizeEvent` to re-run the same calculation, because
   *wrapping* depends on width — resizing the window can change how many
   visual lines the same text occupies even though the text itself hasn't
   changed.
5. Overrides `keyPressEvent` to intercept plain `Enter`/`Return` as "send"
   (emits `sendRequested`) while `Shift+Enter` falls through to the
   default behavior and inserts a newline. Toggle `self.send_on_enter` to
   change this policy.

`min_height` / `max_height` are plain instance attributes set in
`__init__` — the two numbers to change if you want a taller or shorter
composer.

## 7. Notes on Markdown / code rendering

AI messages render through `QTextBrowser.setMarkdown(...)` (`widgets/chat_message.py`),
which is Qt's own built-in CommonMark-ish renderer (Qt 5.14+/Qt6) —
headings, bold/italic, lists, tables, and fenced code blocks (rendered as
a monospaced, background-boxed block) all work with zero extra
dependencies. Qt does not syntax-highlight *inside* those code blocks by
default; if you want per-token coloring (keywords/strings/comments), the
clean extension point is a `QSyntaxHighlighter` subclass attached to
`ChatMessage.body.document()` — Qt's own "Code Editor" example is a good
reference implementation to adapt.

## 8. Dependencies

Just `PySide6`. No Markdown-parsing library, no icon-font package (icons
are Unicode glyphs styled through QSS, e.g. `✦`, `📎`, `⚙` — swap these for
an actual icon font or SVG resource set via `resources/` + a `.qrc` file
if you want pixel-perfect iconography instead).
