import pygame
import sys
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple

# ============================================================
# Mini VS Code Configuration & Theme
# ============================================================
pygame.init()
pygame.font.init()
pygame.key.set_repeat(400, 40)
FONT = pygame.font.SysFont("Courier", 14)

BG = (30, 30, 30)
PANEL_BG = (15, 15, 15)
SIDEBAR_BG = (43, 43, 43)
TAB_BG = (20, 20, 20)
TAB_ACTIVE = (30, 30, 30)
BORDER = (65, 65, 68)
TEXT = (210, 210, 210)
MUTED = (130, 130, 130)
BLUE = (0, 122, 204)
HIGHLIGHT = (38, 79, 120)
HOVER = (45, 45, 48)
INPUT_BG = (60, 60, 65)
STATUS_BG = (0, 122, 204)
CLOSE_HOVER = (200, 80, 80)

# Syntax highlight colors (VS Code Dark+ inspired)
COLOR_DEFAULT = (212, 212, 212)
COLOR_KEYWORD = (86, 156, 214)
COLOR_STRING = (206, 145, 120)
COLOR_COMMENT = (106, 153, 85)
COLOR_NUMBER = (181, 206, 168)
COLOR_BUILTIN = (78, 201, 176)
COLOR_OPERATOR = (212, 212, 212)

SIDEBAR_W = 48
STATUS_H = 22
TAB_H = 32
ROW_H = 22
TAB_W = 140

PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
}

PYTHON_BUILTINS = {
    "print", "len", "range", "str", "int", "float", "list", "dict",
    "set", "tuple", "bool", "type", "isinstance", "hasattr", "getattr",
    "setattr", "open", "input", "map", "filter", "zip", "enumerate",
    "sorted", "reversed", "sum", "min", "max", "abs", "round", "any",
    "all", "super", "object", "Exception", "ValueError", "TypeError",
    "KeyError", "IndexError", "AttributeError", "ImportError", "OSError",
}


def safe_name(path: Path) -> str:
    return path.name or str(path)


# ============================================================
# Simple Python Syntax Highlighter
# ============================================================
def tokenize_python(line: str) -> List[Tuple[str, Tuple[int, int, int]]]:
    if not line:
        return [("", COLOR_DEFAULT)]

    tokens: List[Tuple[str, Tuple[int, int, int]]] = []
    i = 0
    n = len(line)

    while i < n:
        if line[i] == "#":
            tokens.append((line[i:], COLOR_COMMENT))
            break

        if line[i] in "\"'":
            quote = line[i]
            if i + 2 < n and line[i:i + 3] == quote * 3:
                end = line.find(quote * 3, i + 3)
                if end == -1:
                    tokens.append((line[i:], COLOR_STRING))
                    break
                tokens.append((line[i:end + 3], COLOR_STRING))
                i = end + 3
                continue
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == quote:
                    j += 1
                    break
                j += 1
            tokens.append((line[i:j], COLOR_STRING))
            i = j
            continue

        if line[i].isdigit() or (line[i] == "." and i + 1 < n and line[i + 1].isdigit()):
            j = i
            while j < n and (line[j].isdigit() or line[j] in ".eExX_"):
                j += 1
            tokens.append((line[i:j], COLOR_NUMBER))
            i = j
            continue

        if line[i].isalpha() or line[i] == "_":
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            if word in PYTHON_KEYWORDS:
                tokens.append((word, COLOR_KEYWORD))
            elif word in PYTHON_BUILTINS:
                tokens.append((word, COLOR_BUILTIN))
            else:
                tokens.append((word, COLOR_DEFAULT))
            i = j
            continue

        tokens.append((line[i], COLOR_OPERATOR))
        i += 1

    return tokens


# ============================================================
# Explorer Panel (with scroll)
# ============================================================
class Explorer:
    def __init__(self, root: Optional[Path] = None):
        self.root = (root or Path.cwd()).resolve()
        self.expanded = {self.root}
        self.selected: Optional[Path] = None
        self.scroll_y = 0
        self.row_h = ROW_H
        self.creating: Optional[str] = None
        self.create_name = ""
        self.error = ""
        self.rendered_rows: list[tuple[pygame.Rect, Path]] = []
        self.btn_file_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_dir_rect = pygame.Rect(0, 0, 0, 0)
        self.content_h = 0
        self.view_h = 0

    def children(self, directory: Path):
        try:
            items = list(directory.iterdir())
        except (PermissionError, OSError):
            return []
        items.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        return items

    def get_items(self):
        result = []

        def walk(path: Path, depth: int):
            result.append((path, depth))
            if path.is_dir() and path in self.expanded:
                for child in self.children(path):
                    walk(child, depth + 1)

        walk(self.root, 0)
        return result

    def toggle(self, path: Path):
        if not path.is_dir():
            return
        if path in self.expanded:
            self.expanded.discard(path)
        else:
            self.expanded.add(path)

    def selected_directory(self) -> Path:
        if self.selected:
            if self.selected.is_dir():
                return self.selected
            return self.selected.parent
        return self.root

    def start_create(self, kind: str):
        self.creating = kind
        self.error = ""
        self.create_name = ""

    def cancel_create(self):
        self.creating = None
        self.create_name = ""
        self.error = ""

    def finish_create(self):
        if not self.creating:
            return None
        name = self.create_name.strip()
        if not name:
            self.cancel_create()
            return None
        base = self.selected_directory()
        target = base / name
        try:
            if target.exists():
                self.error = "Already exists!"
                return None
            if self.creating == "file":
                target.touch()
            else:
                target.mkdir(parents=True, exist_ok=True)
            self.expanded.add(base)
            self.selected = target
            self.cancel_create()
            return target
        except Exception as e:
            self.error = str(e)[:20]
            return None

    def handle_scroll(self, dy: int):
        max_scroll = max(0, self.content_h - self.view_h)
        self.scroll_y = max(0, min(max_scroll, self.scroll_y - dy * 40))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos_local: tuple[int, int]):
        surface.fill(PANEL_BG)
        self.rendered_rows.clear()
        self.view_h = surface.get_height()

        pygame.draw.rect(surface, TAB_BG, (0, 0, surface.get_width(), 30))
        title = font.render("EXPLORER", True, TEXT)
        surface.blit(title, (8, 7))

        btn_f = font.render("[+F]", True, BLUE if self.creating == "file" else MUTED)
        btn_d = font.render("[+D]", True, BLUE if self.creating == "folder" else MUTED)
        surface.blit(btn_f, (surface.get_width() - 65, 7))
        surface.blit(btn_d, (surface.get_width() - 35, 7))
        self.btn_file_rect = pygame.Rect(surface.get_width() - 65, 7, 25, 20)
        self.btn_dir_rect = pygame.Rect(surface.get_width() - 35, 7, 25, 20)

        y_start = 34
        if self.creating:
            y_start += 32
        if self.error:
            y_start += 20

        items = self.get_items()
        self.content_h = y_start + len(items) * self.row_h + 10
        max_scroll = max(0, self.content_h - self.view_h)
        self.scroll_y = max(0, min(max_scroll, self.scroll_y))

        content_rect = pygame.Rect(0, 34, surface.get_width(), surface.get_height() - 34)
        surface.set_clip(content_rect)

        y = 34 - self.scroll_y
        lx, ly = mouse_pos_local

        if self.creating:
            box = pygame.Rect(6, y, surface.get_width() - 12, 26)
            pygame.draw.rect(surface, INPUT_BG, box, border_radius=3)
            pygame.draw.rect(surface, BLUE, box, 1, border_radius=3)
            label = "F: " if self.creating == "file" else "D: "
            txt = font.render(label + self.create_name + "|", True, TEXT)
            surface.blit(txt, (box.x + 6, box.y + 4))
            y += 32

        if self.error:
            err_txt = font.render(self.error, True, (255, 100, 100))
            surface.blit(err_txt, (8, y))
            y += 20

        for path, depth in items:
            row_rect = pygame.Rect(0, y, surface.get_width(), self.row_h)
            self.rendered_rows.append((row_rect, path))

            if row_rect.collidepoint(lx, ly) and y >= 30:
                pygame.draw.rect(surface, HOVER, row_rect)
            if path == self.selected:
                pygame.draw.rect(surface, HIGHLIGHT, row_rect)

            icon = ("▼ " if path in self.expanded else "▶ ") if path.is_dir() else "  "
            color = TEXT if path.is_file() else BLUE
            lbl = font.render(icon + safe_name(path), True, color)
            surface.blit(lbl, (8 + (depth * 12), y + 2))
            y += self.row_h

        surface.set_clip(None)

        if self.content_h > self.view_h:
            track_h = self.view_h - 34
            thumb_h = max(20, int(track_h * (self.view_h / self.content_h)))
            thumb_y = 34 + int((self.scroll_y / max_scroll) * (track_h - thumb_h)) if max_scroll else 34
            pygame.draw.rect(surface, (50, 50, 50), (surface.get_width() - 6, 34, 4, track_h))
            pygame.draw.rect(surface, (100, 100, 100), (surface.get_width() - 6, thumb_y, 4, thumb_h))


# ============================================================
# Document Management
# ============================================================
@dataclass
class Document:
    path: Path
    buffer: list[str] = field(default_factory=list)
    caret_row: int = 0
    caret_col: int = 0
    dirty: bool = False
    scroll_y: int = 0

    def __post_init__(self):
        if self.path.exists() and self.path.is_file():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.buffer = f.read().splitlines()
            except Exception:
                self.buffer = ["Error opening file."]
        if not self.buffer:
            self.buffer = [""]

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.buffer))
            self.dirty = False
        except Exception:
            pass

    def insert_text(self, text: str):
        line = self.buffer[self.caret_row]
        self.buffer[self.caret_row] = line[:self.caret_col] + text + line[self.caret_col:]
        self.caret_col += len(text)
        self.dirty = True

    def insert_newline(self):
        line = self.buffer[self.caret_row]
        self.buffer[self.caret_row] = line[:self.caret_col]
        self.buffer.insert(self.caret_row + 1, line[self.caret_col:])
        self.caret_row += 1
        self.caret_col = 0
        self.dirty = True

    def delete_backspace(self):
        if self.caret_col > 0:
            line = self.buffer[self.caret_row]
            self.buffer[self.caret_row] = line[:self.caret_col - 1] + line[self.caret_col:]
            self.caret_col -= 1
            self.dirty = True
        elif self.caret_row > 0:
            prev_line = self.buffer[self.caret_row - 1]
            cur_line = self.buffer[self.caret_row]
            self.caret_col = len(prev_line)
            self.buffer[self.caret_row - 1] = prev_line + cur_line
            self.buffer.pop(self.caret_row)
            self.caret_row -= 1
            self.dirty = True

    def is_python(self) -> bool:
        if self.path.suffix.lower() in {".py", ".pyw", ".pyi"}:
            return True
        text = "\n".join(self.buffer[:30])
        hints = ("def ", "import ", "from ", "class ", "print(", "if __name__")
        return any(h in text for h in hints)


# ============================================================
# Editor Panel (with scroll + close X on tabs)
# ============================================================
class EditorPanel:
    def __init__(self):
        self.tabs: list[Document] = []
        self.active_idx: Optional[int] = None
        self.tab_close_rects: list[tuple[pygame.Rect, int]] = []
        self.view_h = 0

    def open_file(self, path: Path):
        if path.is_dir():
            return
        for i, t in enumerate(self.tabs):
            if t.path == path:
                self.active_idx = i
                return
        doc = Document(path)
        self.tabs.append(doc)
        self.active_idx = len(self.tabs) - 1

    def close_tab(self, idx: int):
        if idx < 0 or idx >= len(self.tabs):
            return
        self.tabs.pop(idx)
        if not self.tabs:
            self.active_idx = None
        else:
            if self.active_idx is None or self.active_idx >= len(self.tabs):
                self.active_idx = len(self.tabs) - 1
            elif idx < self.active_idx:
                self.active_idx -= 1
            elif idx == self.active_idx:
                self.active_idx = min(idx, len(self.tabs) - 1)

    def handle_scroll(self, dy: int):
        if self.active_idx is None:
            return
        doc = self.tabs[self.active_idx]
        content_h = len(doc.buffer) * ROW_H + 20
        max_scroll = max(0, content_h - max(1, self.view_h - TAB_H))
        doc.scroll_y = max(0, min(max_scroll, doc.scroll_y - dy * 40))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int] = (0, 0)):
        surface.fill(BG)
        self.view_h = surface.get_height()
        self.tab_close_rects.clear()
        pygame.draw.rect(surface, TAB_BG, (0, 0, surface.get_width(), TAB_H))

        if not self.tabs or self.active_idx is None:
            msg = font.render("Click [+F] in Explorer to create a file or click an existing one.", True, MUTED)
            surface.blit(msg, (20, 50))
            return

        mx, my = mouse_pos

        for i, tab in enumerate(self.tabs):
            tx = i * TAB_W
            bg_c = TAB_ACTIVE if i == self.active_idx else TAB_BG
            pygame.draw.rect(surface, bg_c, (tx, 0, TAB_W - 2, TAB_H))
            name = safe_name(tab.path) + ("*" if tab.dirty else "")
            lbl = font.render(name[:10], True, TEXT if i == self.active_idx else MUTED)
            surface.blit(lbl, (tx + 6, 8))

            close_rect = pygame.Rect(tx + TAB_W - 22, 8, 16, 16)
            self.tab_close_rects.append((close_rect, i))
            hovering_close = close_rect.collidepoint(mx, my)
            x_color = CLOSE_HOVER if hovering_close else MUTED
            if hovering_close:
                pygame.draw.rect(surface, (60, 30, 30), close_rect, border_radius=2)
            x_lbl = font.render("x", True, x_color)
            surface.blit(x_lbl, (close_rect.x + 3, close_rect.y - 1))

        doc = self.tabs[self.active_idx]
        content_h = len(doc.buffer) * ROW_H + 20
        max_scroll = max(0, content_h - max(1, self.view_h - TAB_H))
        doc.scroll_y = max(0, min(max_scroll, doc.scroll_y))

        body_rect = pygame.Rect(0, TAB_H, surface.get_width(), surface.get_height() - TAB_H)
        surface.set_clip(body_rect)

        gy = TAB_H + 8 - doc.scroll_y
        for idx, line in enumerate(doc.buffer):
            if gy + ROW_H < TAB_H or gy > surface.get_height():
                gy += ROW_H
                continue

            num_lbl = font.render(f"{idx + 1:3}", True, MUTED)
            surface.blit(num_lbl, (4, gy))

            x = 40
            for segment, color in tokenize_python(line):
                if segment:
                    src_lbl = font.render(segment, True, color)
                    surface.blit(src_lbl, (x, gy))
                    x += font.size(segment)[0]

            if idx == doc.caret_row:
                cx = 40 + font.size(line[:doc.caret_col])[0]
                pygame.draw.line(surface, BLUE, (cx, gy), (cx, gy + ROW_H - 4), 2)
            gy += ROW_H

        surface.set_clip(None)

        if content_h > (self.view_h - TAB_H):
            track_h = self.view_h - TAB_H
            thumb_h = max(20, int(track_h * ((self.view_h - TAB_H) / content_h)))
            thumb_y = TAB_H + int((doc.scroll_y / max_scroll) * (track_h - thumb_h)) if max_scroll else TAB_H
            pygame.draw.rect(surface, (50, 50, 50), (surface.get_width() - 6, TAB_H, 4, track_h))
            pygame.draw.rect(surface, (100, 100, 100), (surface.get_width() - 6, thumb_y, 4, thumb_h))


# ============================================================
# Interactive Shell Terminal (with scroll + cls)
# ============================================================
class ShellTerminal:
    def __init__(self):
        self.cwd = os.getcwd()
        self.prompt = f"{self.cwd}>"
        self.current_input = ""
        self.output_history: list[str] = [
            "Microsoft Windows Mini-Shell Simulator [Version 1.0]",
            "Type any valid system commands. Use cls or clear to clear.",
        ]
        self.scroll_y = 0
        self.content_h = 0
        self.view_h = 0

    def push_command(self):
        cmd = self.current_input.strip()
        full_line = f"{self.prompt}{self.current_input}"
        self.output_history.append(full_line)

        if cmd:
            cmd_lower = cmd.lower()
            if cmd_lower in ("cls", "clear"):
                self.output_history.clear()
                self.current_input = ""
                self.scroll_y = 0
                return

            cmd_parts = cmd.split()
            if cmd_parts[0].lower() == "cd":
                if len(cmd_parts) > 1:
                    target_dir = " ".join(cmd_parts[1:])
                    try:
                        os.chdir(os.path.join(self.cwd, target_dir))
                        self.cwd = os.getcwd()
                        self.prompt = f"{self.cwd}>"
                    except Exception as e:
                        self.output_history.append(f"The system cannot find the path specified: {e}")
                else:
                    self.output_history.append(os.getcwd())
            else:
                try:
                    res = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, cwd=self.cwd, timeout=5
                    )
                    if res.stdout:
                        out = res.stdout.rstrip("\n")
                        if out:
                            self.output_history.extend(out.splitlines())
                    if res.stderr:
                        err = res.stderr.rstrip("\n")
                        if err:
                            self.output_history.extend(err.splitlines())
                except Exception as e:
                    self.output_history.append(f"Command execution error: {e}")

        self.current_input = ""
        self.scroll_y = 10**9

    def handle_keydown(self, event: pygame.event.Event):
        if event.key == pygame.K_RETURN:
            self.push_command()
        elif event.key == pygame.K_BACKSPACE:
            self.current_input = self.current_input[:-1]
        else:
            if event.unicode and event.unicode.isprintable():
                self.current_input += event.unicode

    def handle_scroll(self, dy: int):
        max_scroll = max(0, self.content_h - self.view_h)
        self.scroll_y = max(0, min(max_scroll, self.scroll_y - dy * 40))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, is_focused: bool):
        surface.fill(PANEL_BG)
        self.view_h = surface.get_height()
        pygame.draw.line(surface, BORDER, (0, 0), (surface.get_width(), 0), 1)

        if is_focused:
            pygame.draw.rect(surface, HIGHLIGHT, (0, 1, surface.get_width(), 3))

        lines_to_show = list(self.output_history)
        lines_to_show.append(f"{self.prompt}{self.current_input}_")

        self.content_h = len(lines_to_show) * ROW_H + 20
        max_scroll = max(0, self.content_h - self.view_h)
        if self.scroll_y > max_scroll:
            self.scroll_y = max_scroll

        surface.set_clip(pygame.Rect(0, 4, surface.get_width(), surface.get_height() - 4))

        cy = 10 - self.scroll_y
        for line in lines_to_show:
            if cy + ROW_H >= 0 and cy < surface.get_height():
                lbl = font.render(line[:120], True, TEXT)
                surface.blit(lbl, (12, cy))
            cy += ROW_H

        surface.set_clip(None)

        if self.content_h > self.view_h:
            track_h = self.view_h - 4
            thumb_h = max(20, int(track_h * (self.view_h / self.content_h)))
            thumb_y = 4 + int((self.scroll_y / max_scroll) * (track_h - thumb_h)) if max_scroll else 4
            pygame.draw.rect(surface, (50, 50, 50), (surface.get_width() - 6, 4, 4, track_h))
            pygame.draw.rect(surface, (100, 100, 100), (surface.get_width() - 6, thumb_y, 4, thumb_h))


# ============================================================
# Main App
# ============================================================
def main():
    screen = pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
    pygame.display.set_caption("Mini VS Code Workspace Studio")
    clock = pygame.time.Clock()

    explorer = Explorer()
    editor = EditorPanel()
    shell = ShellTerminal()

    exp_ratio = 0.25
    shell_height = 200

    drag_h_divider = False
    drag_v_divider = False
    active_focus = "editor"

    while True:
        w, h = screen.get_size()
        mx, my = pygame.mouse.get_pos()

        exp_w = int(w * exp_ratio)
        edt_w = w - SIDEBAR_W - exp_w
        edt_h = h - STATUS_H - shell_height
        shell_y = edt_h

        h_div_x = SIDEBAR_W + exp_w
        v_div_y = shell_y

        rect_sidebar = pygame.Rect(0, 0, SIDEBAR_W, h - STATUS_H)
        rect_explorer = pygame.Rect(SIDEBAR_W, 0, exp_w, h - STATUS_H)
        rect_editor = pygame.Rect(h_div_x, 0, edt_w, edt_h)
        rect_shell = pygame.Rect(h_div_x, v_div_y, edt_w, shell_height)

        on_h_divider = abs(mx - h_div_x) < 6 and my < h - STATUS_H
        on_v_divider = abs(my - v_div_y) < 6 and mx >= h_div_x

        if drag_h_divider or on_h_divider:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)
        elif drag_v_divider or on_v_divider:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENS)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEWHEEL:
                if rect_explorer.collidepoint(mx, my):
                    explorer.handle_scroll(event.y)
                elif rect_editor.collidepoint(mx, my):
                    editor.handle_scroll(event.y)
                elif rect_shell.collidepoint(mx, my):
                    shell.handle_scroll(event.y)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if on_h_divider:
                        drag_h_divider = True
                    elif on_v_divider:
                        drag_v_divider = True
                    else:
                        if rect_explorer.collidepoint(mx, my):
                            active_focus = "explorer"
                            lx, ly = mx - SIDEBAR_W, my

                            if explorer.btn_file_rect.collidepoint(lx, ly):
                                explorer.start_create("file")
                            elif explorer.btn_dir_rect.collidepoint(lx, ly):
                                explorer.start_create("folder")
                            else:
                                row_clicked = False
                                for row_rect, path in explorer.rendered_rows:
                                    if row_rect.collidepoint(lx, ly):
                                        explorer.selected = path
                                        row_clicked = True
                                        if path.is_dir():
                                            explorer.toggle(path)
                                        else:
                                            editor.open_file(path)
                                            active_focus = "editor"
                                        break
                                if not row_clicked and explorer.creating:
                                    explorer.cancel_create()

                        elif rect_editor.collidepoint(mx, my):
                            active_focus = "editor"
                            if explorer.creating:
                                explorer.cancel_create()
                            lx, ly = mx - h_div_x, my

                            closed = False
                            for close_rect, idx in editor.tab_close_rects:
                                if close_rect.collidepoint(lx, ly):
                                    editor.close_tab(idx)
                                    closed = True
                                    break

                            if not closed and ly < TAB_H and editor.tabs:
                                idx = lx // TAB_W
                                if 0 <= idx < len(editor.tabs):
                                    editor.active_idx = idx

                        elif rect_shell.collidepoint(mx, my):
                            active_focus = "shell"
                            if explorer.creating:
                                explorer.cancel_create()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    drag_h_divider = False
                    drag_v_divider = False

            elif event.type == pygame.MOUSEMOTION:
                if drag_h_divider:
                    target_x = mx - SIDEBAR_W
                    exp_ratio = max(0.1, min(0.6, target_x / w))
                elif drag_v_divider:
                    target_height = h - STATUS_H - my
                    shell_height = max(80, min(h - 150, target_height))

            elif event.type == pygame.KEYDOWN:
                if active_focus == "explorer" and explorer.creating:
                    if event.key == pygame.K_RETURN:
                        explorer.finish_create()
                    elif event.key == pygame.K_ESCAPE:
                        explorer.cancel_create()
                    elif event.key == pygame.K_BACKSPACE:
                        explorer.create_name = explorer.create_name[:-1]
                    else:
                        if event.unicode and event.unicode.isprintable():
                            explorer.create_name += event.unicode

                elif active_focus == "shell":
                    shell.handle_keydown(event)

                elif active_focus == "editor" and editor.active_idx is not None:
                    doc = editor.tabs[editor.active_idx]
                    if event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        doc.save()
                    elif event.key == pygame.K_w and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        editor.close_tab(editor.active_idx)
                    elif event.key == pygame.K_BACKSPACE:
                        doc.delete_backspace()
                    elif event.key == pygame.K_RETURN:
                        doc.insert_newline()
                    elif event.key == pygame.K_LEFT:
                        doc.caret_col = max(0, doc.caret_col - 1)
                    elif event.key == pygame.K_RIGHT:
                        doc.caret_col = min(len(doc.buffer[doc.caret_row]), doc.caret_col + 1)
                    elif event.key == pygame.K_UP:
                        doc.caret_row = max(0, doc.caret_row - 1)
                        doc.caret_col = min(len(doc.buffer[doc.caret_row]), doc.caret_col)
                    elif event.key == pygame.K_DOWN:
                        doc.caret_row = min(len(doc.buffer) - 1, doc.caret_row + 1)
                        doc.caret_col = min(len(doc.buffer[doc.caret_row]), doc.caret_col)
                    else:
                        if event.unicode and event.unicode.isprintable():
                            doc.insert_text(event.unicode)

        screen.fill(BG)
        pygame.draw.rect(screen, SIDEBAR_BG, rect_sidebar)

        exp_surf = pygame.Surface((exp_w, h - STATUS_H))
        explorer.draw(exp_surf, FONT, (mx - SIDEBAR_W, my))
        screen.blit(exp_surf, (SIDEBAR_W, 0))

        edt_surf = pygame.Surface((edt_w, edt_h))
        editor.draw(edt_surf, FONT, (mx - h_div_x, my))
        if active_focus == "editor" and editor.active_idx is not None:
            pygame.draw.rect(edt_surf, HIGHLIGHT, (0, 0, edt_w, edt_h), 1)
        screen.blit(edt_surf, (h_div_x, 0))

        con_surf = pygame.Surface((edt_w, shell_height))
        shell.draw(con_surf, FONT, is_focused=(active_focus == "shell"))
        screen.blit(con_surf, (h_div_x, v_div_y))

        pygame.draw.line(screen, BORDER, (h_div_x, 0), (h_div_x, h - STATUS_H), 2)
        pygame.draw.line(screen, BORDER, (h_div_x, v_div_y), (w, v_div_y), 2)

        pygame.draw.rect(screen, STATUS_BG, (0, h - STATUS_H, w, STATUS_H))
        lbl_status = FONT.render(
            f" FOCUS: {active_focus.upper()} | Ctrl+S: Save | Ctrl+W: Close tab | Scroll: mouse wheel | {shell.cwd}",
            True, TEXT
        )
        screen.blit(lbl_status, (5, h - STATUS_H + 3))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()