import string
import sys
import time
from config import config
from utils import HyprlandPlugin
import os
import parser
import threading
import signal
import global_var
    
class Manager():
    def __init__(self, config):
        self.config = config
        # Initialize parsers (managed by Parsers wrapper)
        self.parsers = parser.Parsers(config)

    def start(self):
        # Start all parser components via the Parsers wrapper
        self.parsers.start()

    # def find_all_keybindings(self):
    #     # This is a placeholder function. You would need to implement the logic to find all keybindings from Inkscape.
    #     key_list = list(string.ascii_lowercase)
    #     key_list += ["SHIFT+" + c for c in string.ascii_lowercase]
    #     key_list += ["Space"]
    #     return key_list

def main():
    manager = Manager(config)
    # if there is args --generate-config, then generate the config file and exit
    if len(sys.argv) > 1 and sys.argv[1] in {"--generate-config", "--gen-config", "-g"}:
        hyprland_config = HyprlandPlugin.generate_hyprland_config()
        hyprland_config_file = str(manager.config['hyprland_config_file'])
        with open(hyprland_config_file + ".real.conf", 'w') as f:
            f.write(hyprland_config)
            print(f"Generated Hyprland config file at {hyprland_config_file + '.conf'}\n")
            print("Please include this file in your Hyprland config with the following line:")
            print(f"source = {hyprland_config_file + '.conf'}\n")
            print("Also, run \'hyprctl reload\' to apply the changes.")
        with open(hyprland_config_file + ".blank.conf", 'w') as f:
            f.write("# This is a blank config file used to disable the Inkscape keybindings when Inkscape is not active.\n")
        # Create a soft link to the blank config file by default
        if os.path.exists(hyprland_config_file + '.conf'):
            os.remove(hyprland_config_file + '.conf')
        os.symlink(hyprland_config_file + ".blank.conf", hyprland_config_file + '.conf', target_is_directory=False)
        return
    # reload hyprland to apply the config changes
    HyprlandPlugin.reload_hyprland()
    manager.start()

    try:
        # Keep the main thread alive while background threads run.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Graceful shutdown with watchdog: attempt an orderly stop, then
        # force-terminate the process if threads are still stuck.
        def shutdown_and_watch(mgr, timeout=5.0):
            print("Stopping...")
            try:
                mgr.parsers.stop()
            except Exception:
                pass

            end = time.time() + timeout
            alive = []
            while time.time() < end:
                alive = [t for t in threading.enumerate() if t is not threading.main_thread() and t.is_alive()]
                if not alive:
                    break
                time.sleep(0.1)

            if alive:
                print("Threads still alive after timeout; forcing termination.")
                pid = os.getpid()
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            else:
                print("Stopped.")

        shutdown_and_watch(manager, timeout=20.0)

        # Reset keybindings to default (blank config) on exit
        global_var.IS_INKSCAPE_ACTIVE = False
        HyprlandPlugin.toggle_config_file()  # Ensure config is reset to blank on exit
        time.sleep(1)  # Give it a moment to apply


if __name__ == '__main__':
    main()
