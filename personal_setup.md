```
Preferences: Open User Settings (JSON)

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
  "C_Cpp.intelliSenseCacheSize": 512,
  "C_Cpp.workspaceParsingPriority": "low",
  "C_Cpp.default.browse.limitSymbolsToIncludedHeaders": true
}
```

In Remote Machine, run the script to generate 

```
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


Preferences: Open Keyboard Shortcuts (JSON) 
```
// Place your key bindings in this file to override the defaults
[
  {
    "key": "cmd+down",
    "command": "editor.action.goToDeclaration",
    "when": "isMac && editorTextFocus"
  },
  {
    "key": "ctrl+down",
    "command": "editor.action.goToDeclaration",
    "when": "!isMac && editorTextFocus"
  },
  {
    "key": "cmd+[",
    "command": "workbench.action.navigateBack",
    "when": "isMac"
  },
  {
    "key": "ctrl+[",
    "command": "workbench.action.navigateBack",
    "when": "!isMac"
  },
  {
    "key": "cmd+]",
    "command": "workbench.action.navigateForward",
    "when": "isMac"
  },
  {
    "key": "ctrl+]",
    "command": "workbench.action.navigateForward",
    "when": "!isMac"
  }
]
```
