# Inkscape shortcut manager for Hyprland

*A shortcut manager that speeds up drawing (mathematical) figures in [Inkscape](https://inkscape.org/).*

Inspired by https://github.com/gillescastel/inkscape-shortcut-manager which is for X, hereby rewritten for full compatibility with Wayland. Currently only supports Hyprland https://hypr.land/.

## Features

- Send Inkscape shortcut events from Hyprland bindings to automate common tools.
- Edit text in a floating `nvim` window and paste the result back into Inkscape as native SVG clipboard content. Press `t` to add new text, select and press `shift+t` to edit
- Paste styles by typing multiple characters, see https://castel.dev/post/lecture-notes-2/
- Hyprland-aware: bindings are only active when inkscape is at focus.

## Prerequisites

- Python 3.14+ (older versions not tested)
- Hyprland and `hyprctl`
- `kitty` terminal
- `nvim` (Neovim)
- `wl-clipboard` (`wl-copy`/`wl-paste`)
- `wtype` (for synthetic key events)

Optional (useful for troubleshooting): `jq` (JSON processor)

On Arch Linux you can install these with:

```bash
sudo pacman -S python kitty neovim wl-clipboard wtype hyprland jq
```

## Quick Start

1. Clone the repository.
1. In the installation folder, run
    ```bash
    pip install -r requirements.txt
    ```
1. Edit `config.py` to set your `storage_dir`, `socket_port`, `font`, and other preferences.
1. Run
    ```bash
    mkdir -p ~/.config/inkscape-shortcut-manager/
    ```
1. In ~/.config/hypr/hyprland.conf add
    ```hyprlang
    windowrule {
        name = kitty-float
        match:class = kitty-float
        float = on
    }
    ```
    and
    ```hyprlang
    source = ~/.config/inkscape-shortcut-manager/inkscape-shortcut-hyprland.conf
    ```

1. Run
    ```bash
    python3 main.py -g
    ```
    to generate config file
1. Start the manager:

    ```bash
    python3 main.py
    ```
1. Press Ctrl+C to stop it.
1. Enjoy

## Configuration

- `config.py`: main configuration (paths, ports, font size).
- `global_var.py`: runtime constants including clipboard target names.

## Troubleshooting

- Window doesn't open: ensure `kitty` is in your `PATH`:

```bash
command -v kitty
```

- Clipboard empty or paste fails: check `wl-paste` output and available targets:

```bash
wl-paste -l
wl-paste -t image/x-inkscape-svg
```

- Hyprland dispatch commands not working: inspect clients and monitors:

```bash
hyprctl clients -j | jq .
hyprctl monitors -j | jq .
```

## License

See the `LICENSE` file.

----

