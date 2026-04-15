import string
import os
import time
import global_var
import subprocess
from pathlib import Path
from clipboard import copy as clipboard_copy
from utils import HyprlandPlugin, SVGPlugin
from text_mode import TextModeParser

class InkscapeProcess():
    def __init__(self, config, grouped_queue, log_queue):
        self.config = config
        self.grouped_queue = grouped_queue
        self.log_queue = log_queue
    
    def command_type(self, command):
        """ A simple heuristic to determine the type of command based on its content. This is used to route the command to the appropriate handler. """
        cmd_set = set(command)
        cmd_str = "".join(command)
        if cmd_str in {"f", "w", "r", "e"}:
            self.log_queue.put(f"Switched to tool for command: {command}")
            self.command_to_tool(cmd_str)
            return "tool"
        elif cmd_str in {"t", "SHIFT+t"}:
            # t is add new text, SHIFT+t is edit existing text
            self.log_queue.put(f"Entered text mode for command: {command}")
            self.text_mode(cmd_str)
            return "text"
        elif len(cmd_set) >= 2 and cmd_set.issubset({"s", "a", "d", "g", "h", "x", "e", "f", "b", "w", "Space"}):
            self.log_queue.put(f"Pasted style for command: {command}")
            self.paste_style(cmd_set)
            return "style"
        else:
            self.log_queue.put(f"Unrecognized command: {command}")
            subprocess.run(HyprlandPlugin.keybind_to_wtype(cmd_str))
            return "unrecognized"
    
    def command_to_tool(self, cmd_str):
        """ Map a command to the corresponding Inkscape tool. This is a simple mapping based on the command content. """
        if cmd_str == "f":
            subprocess.run(['wtype', 'b']) # Bazier tool
            self.grouped_queue.put("Bezier")
            return "Bezier"
        elif cmd_str == "w":
            subprocess.run(['wtype', 'p']) # Draw Pencil tool
            self.grouped_queue.put("Draw")
            return "draw"
        elif cmd_str == "r":
            subprocess.run(['wtype', 'r']) # Rectangle tool
            self.grouped_queue.put("Rectangle")
            return "Rectangle"
        elif cmd_str == "e":
            subprocess.run(['wtype', 'e']) # Eclipse tool
            self.grouped_queue.put("Eclipse")
            return "Eclipse"
        else:
            return None    

    def paste_style(self, combination):
        """Create an SVG clipboard payload describing the style implied by
        `combination` (a set of single-letter flags) and copy it to the
        clipboard with the Inkscape target. Optionally runs a paste command
        afterwards (configured via `config['paste_command']`).
        """
        # Pixel units used in the original implementation
        pt = 1.327
        w = 0.4 * pt
        thick_width = 0.8 * pt
        very_thick_width = 1.2 * pt

        style = {'stroke-opacity': 1}

        if {'s', 'a', 'd', 'g', 'h', 'x', 'e'} & combination:
            style['stroke'] = 'black'
            style['stroke-width'] = w
            style['marker-end'] = 'none'
            style['marker-start'] = 'none'
            style['stroke-dasharray'] = 'none'
        else:
            style['stroke'] = 'none'

        if 'g' in combination:
            w = thick_width
            style['stroke-width'] = w

        if 'h' in combination:
            w = very_thick_width
            style['stroke-width'] = w

        if 'a' in combination:
            style['marker-end'] = f'url(#marker-arrow-{w})'

        if 'x' in combination:
            style['marker-start'] = f'url(#marker-arrow-{w})'
            style['marker-end'] = f'url(#marker-arrow-{w})'

        if 'd' in combination:
            style['stroke-dasharray'] = f'{w},{2*pt}'

        if 'e' in combination:
            style['stroke-dasharray'] = f'{3*pt},{3*pt}'

        if 'f' in combination:
            style['fill'] = 'black'
            style['fill-opacity'] = 0.12

        if 'b' in combination:
            style['fill'] = 'black'
            style['fill-opacity'] = 1

        if 'w' in combination:
            style['fill'] = 'white'
            style['fill-opacity'] = 1

        if {'f', 'b', 'w'} & combination:
            style['marker-end'] = 'none'
            style['marker-start'] = 'none'

        if not {'f', 'b', 'w'} & combination:
            style['fill'] = 'none'
            style['fill-opacity'] = 1

        if style.get('fill') == 'none' and style.get('stroke') == 'none':
            return

        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" version="1.1">'
        ]

        # Add marker defs if necessary
        if (style.get('marker-end') and style['marker-end'] != 'none') or \
                (style.get('marker-start') and style['marker-start'] != 'none'):
            svg_parts.append(f'''
                <defs id="marker-defs">
                <marker
                id="marker-arrow-{w}"
                orient="auto-start-reverse"
                refY="0" refX="0"
                markerHeight="1.690" markerWidth="0.911">
                  <g transform="scale({(2.40 * w + 3.87)/(4.5*w)})">
                    <path
                       d="M -1.55415,2.0722 C -1.42464,1.29512 0,0.1295 0.38852,0 0,-0.1295 -1.42464,-1.29512 -1.55415,-2.0722"
                       style="fill:none;stroke:#000000;stroke-width:{0.6};stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:10;stroke-dasharray:none;stroke-opacity:1"
                       inkscape:connector-curvature="0" />
                   </g>
                </marker>
                </defs>
                ''')

        # Use compact style formatting (no spaces) like Inkscape produces
        style_string = ';'.join('{}:{}'.format(key, value)
                    for key, value in sorted(style.items(), key=lambda x: x[0]))
        # Provide min/max/geom attributes so Inkscape recognises the clipboard
        svg_parts.append(f'<inkscape:clipboard style="{style_string}" min="0,0" max="0,0" geom-min="0,0" geom-max="0,0" />')
        svg_parts.append('</svg>')

        svg = '\n'.join(svg_parts)

        self.log_queue.put(f"Generated SVG:\n{svg}\n")

        # Choose a clipboard target: inspect the full list of types
        # advertised by `wl-paste --list-types` and pick the best match
        # from a preference list. If none match, do an untyped copy.
        clipboard_copy(svg, target=global_var.INKSCAPE_TARGET)

        # Run paste command if configured, else default to typing Ctrl+Shift+V via wtype
        paste_cmd = self.config.get('paste_command', None)
        if paste_cmd:
            try:
                subprocess.run(paste_cmd)
            except Exception:
                try:
                    self.log_queue.put('Failed to run paste_command')
                except Exception:
                    pass
        else:
            # Best-effort: type Ctrl+Shift+v using wtype if available. This may
            # need adjusting depending on your environment's wtype syntax.
            try:
                subprocess.run(HyprlandPlugin.keybind_to_wtype("Ctrl+Shift+v"))
                self.log_queue.put('Typed Ctrl+Shift+v via wtype')
            except Exception:
                try:
                    subprocess.run(HyprlandPlugin.keybind_to_wtype("Ctrl+v"))
                except Exception:
                    pass

    def text_mode(self, cmd_str):
        """ Open a small nvim floating window for inputting text in inkscape, """
        # create a file in the storage directory.
        storage_dir = self.config['storage_dir'] / "tmp_text"
        os.makedirs(storage_dir, exist_ok=True)
        # use timestamp as the file name to avoid conflicts.
        self.log_queue.put(f"Storage directory for text mode: {storage_dir}")
        timestamp = int(time.time() * 1000)
        file_to_edit = storage_dir / f"tmp_{timestamp}.tex"
        self.log_queue.put(f"Created temporary file for text input: {file_to_edit}")

        is_edit_mode = False
        if cmd_str == "SHIFT+t":
            is_edit_mode = True
            subprocess.run(HyprlandPlugin.keybind_to_wtype("Ctrl+c")) # Copy existing text to clipboard
            self.log_queue.put("Copied existing text to clipboard for editing")
            time.sleep(0.5) # Wait a moment for clipboard to be populated
            # Read the Inkscape clipboard with a timeout to avoid blocking
            
            clip_raw = HyprlandPlugin.get_clipboard_content(target=global_var.INKSCAPE_TARGET)
            self.log_queue.put(f"Raw clipboard content: {clip_raw}")
            text_content = SVGPlugin.extract_tspan_text(clip_raw)

            try:
                with file_to_edit.open('w', encoding='utf-8') as f:
                    f.write(text_content)
            except Exception as e:
                self.log_queue.put(f"Failed to write temp file {file_to_edit}: {e}")
            else:
                self.log_queue.put(f"Pre-filled temporary file with existing text content: {text_content}")
            
            subprocess.run(HyprlandPlugin.keybind_to_wtype("Delete")) # Clear existing text in Inkscape to prepare for updated text after editing
            text_parser = TextModeParser(log_queue=self.log_queue, file_to_edit=file_to_edit, callback=lambda: self._on_text_mode_exit_edit(file_to_edit, clip_raw))
            text_parser.start()
        else:
            text_parser = TextModeParser(log_queue=self.log_queue, file_to_edit=file_to_edit, callback=lambda: self._on_text_mode_exit_new(file_to_edit))
            text_parser.start()

    def _on_text_mode_exit_new(self, file_to_edit):
        """ Callback function when the text mode window is closed. Read the content of the file and copy it to the clipboard, then delete the file. """
        try:
            with open(file_to_edit, "r") as f:
                content = f.read()
            
            self.log_queue.put(f"Content read from text mode file: {content}")

            svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg>
              <text
                style="font-size:{self.config['font_size']}px; font-family:'{self.config['font']}';-inkscape-font-specification:'{self.config['font']}, Normal';fill:#000000;fill-opacity:1;stroke:none;"
                xml:space="preserve"><tspan sodipodi:role="line" >{content}</tspan></text>
            </svg> """
            clipboard_copy(svg, target=global_var.INKSCAPE_TARGET)
            try:
                subprocess.run(HyprlandPlugin.keybind_to_wtype("Ctrl+v"))
                self.log_queue.put('Typed Ctrl+v via wtype for new text')
            except Exception:
                pass
            
        except Exception:
            pass
        finally:
            try:
                os.remove(file_to_edit)
            except Exception:
                pass
    
    def _on_text_mode_exit_edit(self, file_to_edit, original_xml=""):
        """ Callback function when the text mode window is closed. Read the content of the file and copy it to the clipboard, then delete the file. """
        try:
            with open(file_to_edit, "r") as f:
                content = f.read()
            self.log_queue.put(f"Content read from text mode file: {content}")
            svg = SVGPlugin.change_tspan_content(original_xml, content)
            self.log_queue.put(f"Generated SVG for edited text:\n{svg}\n")
            clipboard_copy(svg, target=global_var.INKSCAPE_TARGET)
            try:
                subprocess.run(HyprlandPlugin.keybind_to_wtype("Ctrl+Alt+v"))
                self.log_queue.put('Typed Ctrl+Alt+v via wtype for edited text')
            except Exception:
                pass
            
        except Exception:
            pass
        finally:
            try:
                os.remove(file_to_edit)
            except Exception:
                pass