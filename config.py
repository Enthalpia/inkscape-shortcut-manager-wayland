from pathlib import Path

config = {
    # Font that's used to add text in inkscape
    'font': 'monospace',
    'font_size': 10,
    'hyprland_config_file': Path('~/.config/inkscape-shortcut-manager/inkscape-shortcut-hyprland').expanduser(),
    'storage_dir': Path('~/.local/share/inkscape-shortcut-manager/').expanduser(),
    'socket_port': 65432,
    'group_max_interval': 100, # ms, the maximum interval between key presses to be considered as part of the same group
    'window_class': 'org.inkscape.Inkscape', # the window class of Inkscape, used to determine when to capture key presses
}
