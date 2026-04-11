import queue
import socket
import time
from utils import HyprlandPlugin
import global_var
from inkscape_command import InkscapeProcess
from parser_base import ParserBase

class Interceptor(ParserBase):
    """ This is a socket server that listens for messages from the Wayland (presently Hyprland) plugin and sends command to inkscape by wtype. """
    def __init__(self, config, intercept_queue, log_queue):
        super().__init__(log_queue, name='Interceptor')
        self.config = config
        self.sock = None
        # explicit target queues
        self.intercept_queue = intercept_queue

    def open_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # allow reuse of the address/port so quick restarts don't fail with
        # "Address already in use" when sockets are in TIME_WAIT
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass

        try:
            self.sock.bind(('localhost', self.config['socket_port']))
        except OSError as e:
            try:
                self.log_queue.put(f"Failed to bind socket: {e}")
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            raise

        self.sock.listen()
        # allow accept() to timeout periodically so we can check `self.running`
        self.sock.settimeout(1.0)
        self.running = True
        try:
            self.log_queue.put(f"Listening for Hyprland on port {self.config['socket_port']}...")
        except Exception:
            pass
    
    def close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            finally:
                self.sock = None
        self.running = False

    def start(self):
        # use ParserBase helper
        self._start_thread(self._listen_for_messages)
    
    def stop(self):
        # Close socket first so the accept() call will unblock.
        self.close_socket()
        # then stop thread via base helper
        self._stop_thread()
    

    def _listen_for_messages(self):
        self.open_socket()
        self.log_queue.put(f"Socket opened on port {self.config['socket_port']}. Press Ctrl+C to stop.")
        while self.running:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with conn:
                self.log_queue.put(f"Connected by {addr}")
                # set a timeout on the accepted connection so recv() doesn't block forever
                conn.settimeout(1.0)
                try:
                    data = conn.recv(1024)
                except socket.timeout:
                    # no data received within timeout; continue to check running flag
                    continue
                if not data:
                    continue
                # Strip trailing newlines/whitespace from messages received
                # over the socket (clients like `echo` add a newline).
                message = data.decode('utf-8').strip()
                self.log_queue.put(f"Received message: {message}")
                # Route message depending on whether Inkscape is active.
                try:
                    if global_var.IS_INKSCAPE_ACTIVE:
                        self.intercept_queue.put(message)
                    else:
                        pass
                except Exception:
                    pass
        self.close_socket()
        self.log_queue.put("Socket closed.")

class ShortcutParser(ParserBase):
    """ This class is responsible for parsing the raw messages received from the Wayland plugin and grouping them. It runs in a separate thread and communicates with the Inteceptor via input and output queues. Inputs with time intervals less than `group_max_interval` will be grouped together as a string. """
    def __init__(self, config, input_queue, output_queue, log_queue):
        super().__init__(log_queue, name='ShortcutParser')
        self.config = config
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.group = None # This is the group of the elements
    
    def start(self):
        self._start_thread(self._parse_shortcuts)

    def stop(self):
        self._stop_thread()

    def _parse_shortcuts(self):
        # Set a timer. If the timer exceeds `group_max_interval`, the current group will be sent to the output queue and a new group will be started by a new input trugger.
        timer = None
        # Poll interval for checking the queue and timer (seconds). Small value
        # ensures we detect group timeouts even when no new messages arrive.
        poll_interval = 0.05
        while self.running:
            try:
                message = self.input_queue.get(timeout=poll_interval)
            except queue.Empty:
                # No new message; check whether the current group expired.
                if timer and (time.time() - timer) > (self.config['group_max_interval'] / 1000):
                    if self.group:
                        self.output_queue.put(self.group)
                        try:
                            self.log_queue.put(f"Parsed group: {self.group}")
                        except Exception:
                            pass
                        self.group = None
                        timer = None
                continue

            # Received a message — always add to the current group. Interceptor
            # already routes messages to the appropriate queue depending on
            # whether Inkscape is active.
            if self.group:
                self.group += [message]
            else:
                self.group = [message]

            # reset the timer
            timer = time.time()

class InkscapeCommandParser(ParserBase):
    """ This class is responsible for parsing the grouped shortcuts and sending the corresponding commands to Inkscape. It runs in a separate thread and communicates with the ShortcutParser via input and output queues. """
    def __init__(self, config, input_queue, log_queue):
        super().__init__(log_queue, name='InkscapeCommandParser')
        self.config = config
        self.input_queue = input_queue
        self.inkscape_process = InkscapeProcess(config, input_queue, log_queue)
    def start(self):
        self._start_thread(self._parse_commands)

    def stop(self):
        self._stop_thread()

    def _parse_commands(self):
        while self.running:
            try:
                group = self.input_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            # For demonstration purposes, we just log the received group.
            # In a real implementation, this is where you would translate the
            # group into actual commands sent to Inkscape (e.g., via wtype).
            try:
                self.inkscape_process.command_type(group)
                self.log_queue.put(f"Received command group: {group}")
            except Exception:
                pass

class LogParser(ParserBase):
    """ This class is responsible for printing logs to the console. It runs in a separate thread and reads a log_queue. """
    def __init__(self, log_queue):
        super().__init__(log_queue, name='LogParser')

    def start(self):
        self._start_thread(self._print_logs)
    
    def stop(self):
        self._stop_thread()

    def _print_logs(self):
        while self.running:
            try:
                log_message = self.log_queue.get(timeout=1.0)
                print(log_message)
            except queue.Empty:
                continue

class WindowCaptureParser(ParserBase):
    """ This class is responsible for capturing the active window class and setting a flag whether the active window is Inkscape. It runs in a separate thread and only sets the flag """
    def __init__(self, config, log_queue):
        super().__init__(log_queue, name='WindowCaptureParser')
        self.config = config
        # Ensure the shared flag in the constants module is initialized
        global_var.IS_INKSCAPE_ACTIVE = False

    def start(self):
        self._start_thread(self._capture_window)
    
    def stop(self):
        self._stop_thread()

    def _capture_window(self):
        while self.running:
            active_window_class = HyprlandPlugin.active_window_class()
            if active_window_class == self.config['window_class']:
                if not global_var.IS_INKSCAPE_ACTIVE:
                    global_var.IS_INKSCAPE_ACTIVE = True
                    try:
                        self.log_queue.put("Inkscape is now active.")
                        HyprlandPlugin.toggle_config_file()
                    except Exception:
                        pass
            else:
                if global_var.IS_INKSCAPE_ACTIVE:
                    global_var.IS_INKSCAPE_ACTIVE = False
                    try:
                        self.log_queue.put("Inkscape is no longer active.")
                        HyprlandPlugin.toggle_config_file()
                    except Exception:
                        pass
            time.sleep(1.0)


class Parsers:
    """Wrapper to manage Interceptor, ShortcutParser and LogParser together.

    Usage:
        p = Parsers(config, intercept_queue, grouped_queue, log_queue)
        p.start()
        ...
        p.stop()
    """
    def __init__(self, config):
        self.config = config
        self.intercept_queue = queue.Queue()
        self.grouped_queue = queue.Queue()
        self.log_queue = queue.Queue()
        # instantiate components
        # Interceptor will route messages to intercept_queue or frontend_queue
        self.interceptor = Interceptor(config, self.intercept_queue, self.log_queue)
        self.shortcut_parser = ShortcutParser(config, self.intercept_queue, self.grouped_queue, self.log_queue)
        self.inkscape_command_parser = InkscapeCommandParser(config, self.grouped_queue, self.log_queue)
        self.window_capture_parser = WindowCaptureParser(config, self.log_queue)
        self.log_parser = LogParser(self.log_queue)

        # ordered list of components for deterministic start/stop
        self._components = [
            self.interceptor,
            self.shortcut_parser,
            self.inkscape_command_parser,
            self.window_capture_parser,
            self.log_parser,
        ]

    def start(self):
        # start components in defined order
        for c in self._components:
            try:
                c.start()
            except Exception:
                try:
                    self.log_queue.put(f"Failed to start {getattr(c, 'name', c.__class__.__name__)}")
                except Exception:
                    pass

    def stop(self):
        # stop in reverse order to allow parsers to flush
        for c in reversed(self._components):
            try:
                c.stop()
            except Exception:
                try:
                    self.log_queue.put(f"Failed to stop {getattr(c, 'name', c.__class__.__name__)}")
                except Exception:
                    pass