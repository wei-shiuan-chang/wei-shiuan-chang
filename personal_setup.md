# Personal setup

## Git branch in the terminal prompt

### macOS — `~/.zshrc`

This Mac uses Zsh. Add the following to `~/.zshrc` (the configuration currently used here):

```zsh
# Load Zsh's built-in version control helper.
autoload -Uz vcs_info
# Refresh Git information before each prompt, including after branch changes.
precmd_vcs_info() { vcs_info }
precmd_functions+=( precmd_vcs_info )
# Expand the Git information variable each time the prompt is displayed.
setopt prompt_subst
# Display the branch name in cyan, inside parentheses.
zstyle ':vcs_info:git:*' formats '%F{cyan}(%b)%f '
# Green user@host, blue directory, Git branch, then the prompt symbol.
PROMPT='%F{green}%n@%m%f %F{blue}%~%f ${vcs_info_msg_0_}%# '
```

Reload with `source ~/.zshrc`.

### Linux / Windows Bash — `~/.bashrc`

For Bash on Linux, WSL, or Git Bash, add the following at the end of `~/.bashrc`, after any existing `PS1` assignment:

```bash
# Optional: enabled by default in modern Bash; explicitly keep bracketed paste on.
# Treat pasted text as one block so pasted newlines do not execute immediately.
# Bash only: Zsh handles bracketed paste itself and does not need this command.
bind 'set enable-bracketed-paste on'

# Helper for PS1; the Git command could also be placed directly in PS1.
parse_git_branch() {
    local branch
    # Get the current branch; print nothing outside Git or with detached HEAD.
    branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || return
    printf '(%s) ' "$branch"
}

# Normally enabled by default; ensures PS1 evaluates the function each time.
shopt -s promptvars
# Green user@host, blue directory, cyan branch, then the prompt symbol.
# Single quotes defer $(parse_git_branch) until each prompt is displayed.
PS1='\[\e[32m\]\u@\h\[\e[0m\] \[\e[34m\]\w\[\e[0m\] \[\e[36m\]$(parse_git_branch)\[\e[0m\]\$ '
```

Reload with `source ~/.bashrc`. On Windows, use this in WSL or Git Bash; PowerShell uses a different configuration.

Both prompts show `user@host path (branch)` inside a Git repository and omit the branch outside one. The Bash version also omits it when HEAD is detached.

## Ubuntu GNOME — Apply a monitor layout at login

1. Press the **Windows/Super** key, search for **Startup Applications**, and open it. You can also press **Alt+F2** and run `gnome-session-properties`.
2. Click **Add**, name the entry **Monitor layout**, and paste your full `xrandr` command into the **Command** field.
3. Save the entry. The command runs each time you log in to your X11 desktop.

[Ubuntu Startup Applications help](https://help.ubuntu.com/stable/ubuntu-help/startup-applications.html.en)

## Ubuntu GNOME — Remap the left modifier keys

Use these steps in the Ubuntu GNOME desktop session. Skip this section in browser mode.

1. Open **Tweaks** and go to **Keyboard & Mouse**.
2. Open **Additional Layout Options**, then expand **Ctrl position**.
3. Check **Left Alt as Ctrl, Left Ctrl as Win, Left Win as Left Alt**.

## Windows — Remap the left modifier keys

| Physical key | Maps to |
| --- | --- |
| Left Win | Left Alt |
| Left Ctrl | Left Win |
| Left Alt | Left Ctrl |

## VS Code

Open the Command Palette with `Cmd+Shift+P` on macOS or `Ctrl+Shift+P` on Windows/Linux.

### User settings

Run **Preferences: Open User Settings (JSON)** and merge the following into your existing settings. The `C_Cpp` options require the Microsoft C/C++ extension.

```jsonc
{
  // Workbench preferences
  "workbench.editor.tabActionLocation": "left",
  "workbench.editor.enablePreview": false,
  "workbench.colorTheme": "Solarized Light",
  "chat.viewSessions.orientation": "stacked",

  // Editor preferences
  "editor.occurrencesHighlight": "multiFile",
  "editor.selectionHighlight": true,
  "editor.inlayHints.enabled": "on",
  "editor.gotoLocation.multipleDefinitions": "goto",
  "editor.minimap.enabled": false,
  "references.preferredLocation": "view",

  // Git history
  "git.blame.editorDecoration.enabled": true,
  "git.blame.statusBarItem.enabled": true,

  // File Watching & Search
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/build/tmp/**": true,
    "**/build/sstate-cache/**": true,
    "**/build/downloads/**": true
  },
  "search.exclude": {
    "**/build/tmp/**": true,
    "**/build/sstate-cache/**": true,
    "**/build/downloads/**": true
  },
  "C_Cpp.files.exclude": {
    "**/build/tmp/": true,
    "**/build/sstate-cache/": true,
    "**/build/downloads/": true,
    "**/oe-workdir/": true,
    "**/oe-logs/": true
  },

  // Optional: C/C++ inlay hints for C/C++ workspaces.
  // Remove these if you only want hints in workspaces that configure them locally.
  "C_Cpp.inlayHints.parameterNames.enabled": true,
  "C_Cpp.inlayHints.referenceOperator.enabled": true,
  "C_Cpp.inlayHints.autoDeclarationTypes.enabled": true,
  "C_Cpp.inlayHints.parameterNames.suppressWhenArgumentContainsName": false,
  "C_Cpp.inlayHints.autoDeclarationTypes.showOnLeft": true,

  // Optional: add parentheses when completing C/C++ functions.
  "C_Cpp.autocompleteAddParentheses": true,

  // Optional: C/C++ indexing performance preferences.
  // Cache size limits disk cache, not RAM. Enable or adjust if needed.
  // "C_Cpp.intelliSenseCacheSize": 512,
  // "C_Cpp.workspaceParsingPriority": "low",
  // "C_Cpp.default.browse.limitSymbolsToIncludedHeaders": true
}
```

### Remote OpenBMC workspace settings

When connected to the remote machine, run **Preferences: Open Workspace Settings (JSON)** and merge these settings into `.vscode/settings.json`. The paths below are an example from the existing Yocto build; update the username, build target, recipe directory, and compiler version to match your build. Generate `compile_commands.json` through the project's build workflow before configuring its path.

```jsonc
{
  // =========================================================
  // File Watching & Search
  // =========================================================
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/build/tmp/**": true,
    "**/build/sstate-cache/**": true,
    "**/build/downloads/**": true
  },

  "search.exclude": {
    "**/build/tmp/**": true,
    "**/build/sstate-cache/**": true,
    "**/build/downloads/**": true
  },

  "C_Cpp.files.exclude": {
    "**/build/tmp/": true,
    "**/build/sstate-cache/": true,
    "**/build/downloads/": true,
    "**/oe-workdir/": true,
    "**/oe-logs/": true
  },

  // =========================================================
  // C/C++ IntelliSense - Yocto Cross Compilation
  // =========================================================
  "C_Cpp.default.compileCommands": "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/bmcweb-1.0+git/compile_commands.json",

  "C_Cpp.default.compilerPath": "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot-native/usr/bin/arm-openbmc-linux-gnueabi/arm-openbmc-linux-gnueabi-g++",

  "C_Cpp.default.intelliSenseMode": "linux-gcc-arm",
  "C_Cpp.default.cppStandard": "c++23",

  "C_Cpp.default.systemIncludePath": [
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot-native/usr/lib/arm-openbmc-linux-gnueabi/gcc/arm-openbmc-linux-gnueabi/16.1.0/include",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot-native/usr/lib/arm-openbmc-linux-gnueabi/gcc/arm-openbmc-linux-gnueabi/16.1.0/include-fixed",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot/usr/include/c++/16.1.0",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot/usr/include/c++/16.1.0/arm-openbmc-linux-gnueabi",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot/usr/include/c++/16.1.0/backward",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot/usr/lib/arm-openbmc-linux-gnueabi/16.1.0/include",
    "/home/vanessa/projects/aspeed/openbmc/build/evb-ast2600/tmp/work/armv7ahf-vfpv4d16-openbmc-linux-gnueabi/bmcweb/1.0+git/recipe-sysroot/usr/include"
  ],

  // =========================================================
  // C/C++ Symbol Navigation
  // =========================================================
  "C_Cpp.default.browse.path": [
    "${workspaceFolder}/redfish-core",
    "${workspaceFolder}/http",
    "${workspaceFolder}/include",
    "${workspaceFolder}/src",
    "${workspaceFolder}/config",
    "${workspaceFolder}/features/google",
    "${workspaceFolder}/features/ibm",
    "${workspaceFolder}/features/kvm",
    "${workspaceFolder}/features/openbmc_rest",
    "${workspaceFolder}/features/serial",
    "${workspaceFolder}/features/virtual_media",
    "${workspaceFolder}/features/webui_login",
    "${workspaceFolder}/test"
  ],

  // =========================================================
  // C/C++ Inlay Hints
  // =========================================================
  "C_Cpp.inlayHints.parameterNames.enabled": true,
  "C_Cpp.inlayHints.referenceOperator.enabled": true,
  "C_Cpp.inlayHints.autoDeclarationTypes.enabled": true,
  "C_Cpp.inlayHints.parameterNames.suppressWhenArgumentContainsName": false,
  "C_Cpp.inlayHints.autoDeclarationTypes.showOnLeft": true,

  // =========================================================
  // C/C++ Autocomplete
  // =========================================================
  "C_Cpp.autocompleteAddParentheses": true,

  // =========================================================
  // Performance Optimization (Optional)
  // =========================================================
  // Previously used to reduce resource consumption when
  // cpptools was indexing large OpenBMC projects.
  //
  // Enable only if performance becomes an issue again.
  //
  // intelliSenseCacheSize: Limits disk cache size, not RAM.
  // workspaceParsingPriority: Lowers background parsing priority.
  // limitSymbolsToIncludedHeaders: Already true by default.
  //
  "C_Cpp.intelliSenseCacheSize": 512,
  "C_Cpp.workspaceParsingPriority": "low",
  "C_Cpp.default.browse.limitSymbolsToIncludedHeaders": true,
}
```


### Keyboard shortcuts

Run **Preferences: Open Keyboard Shortcuts (JSON)** and merge these entries into the existing array. The Windows/Linux bindings below override the usual Shift+arrow text selection shortcuts.

```jsonc
// Place your key bindings in this file to override the defaults
[
  // macOS
  {
    "key": "cmd+down",
    "command": "editor.action.goToDeclaration",
    "when": "isMac && editorTextFocus"
  },
  {
    "key": "cmd+[",
    "command": "workbench.action.navigateBack",
    "when": "isMac"
  },
  {
    "key": "cmd+]",
    "command": "workbench.action.navigateForward",
    "when": "isMac"
  },

  // Linux / Windows
  {
    "key": "ctrl+down",
    "command": "editor.action.goToDeclaration",
    "when": "!isMac && editorTextFocus"
  },
  {
    "key": "shift+down",
    "command": "editor.action.goToDeclaration",
    "when": "!isMac && editorTextFocus"
  },
  {
    "key": "shift+left",
    "command": "workbench.action.navigateBack",
    "when": "!isMac && editorTextFocus"
  },
  {
    "key": "shift+right",
    "command": "workbench.action.navigateForward",
    "when": "!isMac && editorTextFocus"
  }
]
```
