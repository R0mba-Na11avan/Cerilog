<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/R0mba-Na11avan/Cerilog/main/docs/images/cerilog-logo.png">
    <img src="https://raw.githubusercontent.com/R0mba-Na11avan/Cerilog/main/docs/images/cerilog-logo-light.png" alt="Cerilog logo" width="320">
  </picture>
</p>

# Cerilog for VS Code

Language support for Cerilog (`.cel`) files.

- **Syntax highlighting** for keywords, numbers, operators, comments, module
  and instance names.
- **Error checking on save.** Errors and warnings from the compiler appear as
  squiggles and in the Problems panel, including hints.
- **▶ Compile** in the editor title bar compiles the current file to the
  selected target. The ⌄ menu next to it compiles once to `.sv` or `.v`
  without changing the selection.
- **Target switch** in the status bar (`Cerilog: SV` / `Cerilog: V`). Click it
  to choose SystemVerilog or Verilog-2005. The choice is saved per workspace,
  and checks use it too, so Verilog-only errors show up when you target `.v`.

## Requirements

The extension runs the Cerilog compiler, so install it first:

```bash
pip install cerilog
```

That puts a `cerilog` command on your PATH. If `cerilog` isn't found (for
example, Python's scripts folder isn't on PATH), set **Cerilog: Command** to
`python -m cerilog`.

## Install

**From a folder (no tools needed).** Link this folder into your extensions
directory, then restart VS Code:

```powershell
# Windows (PowerShell), from the repository root
New-Item -ItemType Junction -Path "$env:USERPROFILE\.vscode\extensions\cerilog" -Target "$PWD\editors\vscode"
```

```bash
# macOS / Linux
ln -s "$PWD/editors/vscode" ~/.vscode/extensions/cerilog
```

**As a .vsix package:**

```bash
cd editors/vscode
npx @vscode/vsce package
code --install-extension cerilog-0.1.0.vsix
```

To work on the extension itself, open `editors/vscode` in VS Code and press
F5 to launch a window with it loaded.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `cerilog.target` | `sv` | Output for ▶ and for checks: `sv` or `v` |
| `cerilog.outDir` | *(empty)* | Where ▶ writes output. Empty: next to the `.cel` file. Relative paths are resolved against the workspace folder |
| `cerilog.command` | `cerilog` | How to run the compiler, e.g. `python -m cerilog` |
| `cerilog.checkOnSave` | `true` | Check files when they are saved |

The raw compiler output is in the **Cerilog** output channel.
