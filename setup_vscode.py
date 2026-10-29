#!/usr/bin/env python3
"""Configure workspace-local VS Code settings for an OpenBMC devtool source."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKIP_DISCOVERY_DIRS = {
    ".git",
    "package",
    "packages-split",
    "pseudo",
    "recipe-sysroot",
    "recipe-sysroot-native",
    "spdx",
    "temp",
}

CPP_SOURCE_PREFERENCE = (
    "redfish-core/src/redfish.cpp",
    "src/webserver_run.cpp",
)

PROJECT_MARKERS = {
    "C/C++": ("CMakeLists.txt", "meson.build", "configure.ac", "Makefile"),
    "JavaScript/TypeScript": ("package.json", "tsconfig.json"),
    "Python": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"),
    "Rust": ("Cargo.toml",),
    "Go": ("go.mod",),
    "Java": ("pom.xml", "build.gradle", "build.gradle.kts"),
}

CPP_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".c++"}


class SetupError(Exception):
    """An actionable setup error."""


def stale_toolchain_hint() -> str:
    return (
        " If this compilation database or build tree came from another "
        "machine or location, initialize this machine's OpenBMC build "
        "environment, run 'devtool build <recipe>' here, then rerun this "
        "script. Yocto compiler paths are machine- and build-location-specific."
    )


def strip_jsonc_comments(text: str) -> str:
    characters = list(text)
    index = 0
    in_string = False
    while index < len(characters):
        character = characters[index]
        if in_string:
            if character == "\\":
                index += 2
                continue
            if character == '"':
                in_string = False
            index += 1
            continue

        if character == '"':
            in_string = True
            index += 1
            continue
        if character == "/" and index + 1 < len(characters):
            next_character = characters[index + 1]
            if next_character == "/":
                characters[index] = characters[index + 1] = " "
                index += 2
                while index < len(characters) and characters[index] not in "\r\n":
                    characters[index] = " "
                    index += 1
                continue
            if next_character == "*":
                characters[index] = characters[index + 1] = " "
                index += 2
                while index + 1 < len(characters) and not (
                    characters[index] == "*" and characters[index + 1] == "/"
                ):
                    if characters[index] not in "\r\n":
                        characters[index] = " "
                    index += 1
                if index + 1 >= len(characters):
                    raise SetupError("Unterminated block comment in settings file.")
                characters[index] = characters[index + 1] = " "
                index += 2
                continue
        index += 1
    return "".join(characters)


def jsonc_to_json(text: str) -> str:
    characters = list(strip_jsonc_comments(text))
    index = 0
    in_string = False
    while index < len(characters):
        character = characters[index]
        if in_string:
            if character == "\\":
                index += 2
                continue
            if character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
        elif character == ",":
            next_index = index + 1
            while next_index < len(characters) and characters[next_index].isspace():
                next_index += 1
            if next_index < len(characters) and characters[next_index] in "}]":
                characters[index] = " "
        index += 1
    return "".join(characters)


def parse_jsonc(text: str) -> Any:
    return json.loads(jsonc_to_json(text))


def jsonc_value_spans(text: str) -> tuple[dict[str, tuple[int, int]], int]:
    cleaned = jsonc_to_json(text)
    decoder = json.JSONDecoder()
    root_start = len(cleaned) - len(cleaned.lstrip())
    if root_start >= len(cleaned) or cleaned[root_start] != "{":
        raise SetupError("VS Code settings must contain a JSON object.")

    spans: dict[str, tuple[int, int]] = {}
    index = root_start + 1
    while index < len(cleaned):
        while index < len(cleaned) and cleaned[index].isspace():
            index += 1
        if index < len(cleaned) and cleaned[index] == "}":
            root_end = index + 1
            break
        try:
            key, key_end = decoder.raw_decode(cleaned, index)
        except json.JSONDecodeError as error:
            raise SetupError(f"Invalid VS Code settings JSONC: {error}") from error
        if not isinstance(key, str):
            raise SetupError("VS Code settings keys must be strings.")
        index = key_end
        while index < len(cleaned) and cleaned[index].isspace():
            index += 1
        if index >= len(cleaned) or cleaned[index] != ":":
            raise SetupError(f"Expected ':' after VS Code setting {key!r}.")
        index += 1
        while index < len(cleaned) and cleaned[index].isspace():
            index += 1
        value_start = index
        try:
            _, index = decoder.raw_decode(cleaned, value_start)
        except json.JSONDecodeError as error:
            raise SetupError(f"Invalid value for VS Code setting {key!r}: {error}") from error
        spans[key] = (value_start, index)
        while index < len(cleaned) and cleaned[index].isspace():
            index += 1
        if index < len(cleaned) and cleaned[index] == ",":
            index += 1
        elif index < len(cleaned) and cleaned[index] == "}":
            root_end = index + 1
            break
        else:
            raise SetupError(f"Expected ',' or '}}' after VS Code setting {key!r}.")
    else:
        raise SetupError("Unterminated VS Code settings object.")
    return spans, root_end


def update_jsonc(
    original: str, settings: dict[str, Any], updated_keys: list[str] | set[str]
) -> str:
    spans, root_end = jsonc_value_spans(original)
    cleaned_comments = strip_jsonc_comments(original)
    opening_brace = cleaned_comments.find("{")
    root_line_start = original.rfind("\n", 0, opening_brace) + 1
    root_indent = original[root_line_start:opening_brace]
    if not root_indent.isspace() and root_indent:
        root_indent = ""
    property_indent = "  "
    for key, (start, _) in spans.items():
        line_start = original.rfind("\n", 0, start) + 1
        line = original[line_start:start]
        whitespace = line[: len(line) - len(line.lstrip())]
        if whitespace:
            property_indent = whitespace
        break

    replacements: list[tuple[int, int, str]] = []
    new_settings: list[str] = []
    for key in updated_keys:
        rendered = json.dumps(settings[key], indent=2, ensure_ascii=False)
        rendered = rendered.replace("\n", "\n" + property_indent)
        if key in spans:
            start, end = spans[key]
            replacements.append((start, end, rendered))
        else:
            new_settings.append(f"{property_indent}{json.dumps(key)}: {rendered}")

    result = original
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]

    if new_settings:
        spans_after_replacements, root_end_after_replacements = jsonc_value_spans(
            result
        )
        root_close = root_end_after_replacements - 1
        if spans_after_replacements:
            last_value_end = max(end for _, end in spans_after_replacements.values())
            source_without_comments = strip_jsonc_comments(result)
            between_value_and_close = source_without_comments[
                last_value_end:root_close
            ]
            comma_offset = between_value_and_close.find(",")
            if comma_offset >= 0:
                insertion_point = last_value_end + comma_offset + 1
                separator = ""
            else:
                insertion_point = last_value_end
                separator = ","
        else:
            insertion_point = root_close
            separator = ""
        insertion = (
            separator
            + "\n"
            + ",\n".join(new_settings)
            + "\n"
            + root_indent
        )
        result = result[:insertion_point] + insertion + result[insertion_point:]

    section_comments = (
        (
            {"files.exclude"},
            "// OpenBMC devtool workspace exclusions",
        ),
        (
            {
                "C_Cpp.default.compileCommands",
                "C_Cpp.default.compilerPath",
                "C_Cpp.default.intelliSenseMode",
                "C_Cpp.default.systemIncludePath",
                "C_Cpp.default.cStandard",
                "C_Cpp.default.cppStandard",
            },
            "// Machine-specific C/C++ paths: rerun this script on each machine.",
        ),
        (
            {
                "C_Cpp.inlayHints.parameterNames.enabled",
                "C_Cpp.inlayHints.referenceOperator.enabled",
                "C_Cpp.inlayHints.autoDeclarationTypes.enabled",
                "C_Cpp.inlayHints.parameterNames.suppressWhenArgumentContainsName",
                "C_Cpp.inlayHints.autoDeclarationTypes.showOnLeft",
            },
            "// C/C++ inlay hints",
        ),
        (
            {
                "C_Cpp.default.browse.path",
                "C_Cpp.default.browse.limitSymbolsToIncludedHeaders",
                "C_Cpp.files.exclude",
            },
            "// bmcweb C/C++ symbol navigation",
        ),
    )
    for keys, comment in section_comments:
        managed_keys = keys.intersection(updated_keys)
        if not managed_keys or comment in result:
            continue
        matching_positions = [
            result.find(json.dumps(key))
            for key in managed_keys
            if result.find(json.dumps(key)) >= 0
        ]
        if matching_positions:
            key_position = min(matching_positions)
            line_start = result.rfind("\n", 0, key_position) + 1
            result = (
                result[:line_start]
                + property_indent
                + comment
                + "\n"
                + result[line_start:]
            )
    return result


def resolved_entry_file(entry: dict[str, Any]) -> Path:
    directory = Path(entry["directory"])
    source = Path(entry["file"])
    if not source.is_absolute():
        source = directory / source
    return source.resolve()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def project_types(workspace: Path) -> list[str]:
    return [
        project_type
        for project_type, markers in PROJECT_MARKERS.items()
        if any((workspace / marker).is_file() for marker in markers)
    ]


def is_source_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    return (
        path.parent.name == "sources"
        and path.parent.parent.name == "workspace"
    ) or bool(project_types(path))


def discover_workspace(requested_workspace: Path | None) -> Path:
    if requested_workspace is not None:
        workspace = requested_workspace.expanduser().resolve()
        if not workspace.is_dir():
            raise SetupError(f"Source root is not a directory: {workspace}")
        return workspace

    current_directory = Path.cwd().resolve()
    if is_source_root(current_directory):
        return current_directory

    candidate_patterns = [
        "build/*/workspace/sources/*",
        "*/workspace/sources/*",
    ]
    if current_directory.name == "build":
        candidate_patterns.append("*/workspace/sources/*")
    if current_directory.parent.name == "build":
        candidate_patterns.append("workspace/sources/*")
    if current_directory.name == "sources":
        candidate_patterns.append("*")
    candidates = {
        candidate.resolve()
        for pattern in candidate_patterns
        for candidate in current_directory.glob(pattern)
        if candidate.is_dir()
    }
    if len(candidates) == 1:
        return candidates.pop()
    if len(candidates) > 1:
        paths = "\n".join(f"  {path}" for path in sorted(candidates))
        raise SetupError(
            "Multiple devtool source trees found. Choose one with --workspace:\n"
            + paths
        )
    script_workspace = Path(__file__).resolve().parent.parent
    if is_source_root(script_workspace):
        return script_workspace
    raise SetupError(
        "Could not identify a source root. Run from a devtool "
        "build/<machine>/workspace/sources/<recipe> directory, from an "
        "OpenBMC root with exactly one devtool source tree, or pass "
        "--workspace."
    )


def discover_source_roots(sources_directory: Path) -> list[Path]:
    sources_directory = sources_directory.expanduser().resolve()
    if (
        not sources_directory.is_dir()
        or sources_directory.name != "sources"
        or sources_directory.parent.name != "workspace"
    ):
        raise SetupError(
            "Multi-root setup must run from a build's "
            "workspace/sources directory or use --workspace to select it."
        )
    source_roots = sorted(
        path
        for path in sources_directory.iterdir()
        if path.is_dir() and is_source_root(path)
    )
    if not source_roots:
        raise SetupError(f"No devtool source trees found in {sources_directory}.")
    return source_roots


def discover_compile_databases(workspace: Path) -> list[Path]:
    candidates: set[Path] = set()
    roots = [workspace]
    oe_workdir = workspace / "oe-workdir"
    if oe_workdir.is_dir():
        roots.append(oe_workdir.resolve())
    if len(workspace.parents) >= 3:
        machine_build = workspace.parents[2]
        tmp_work = machine_build / "tmp/work"
        if tmp_work.is_dir():
            roots.append(tmp_work)

    for root in roots:
        if not root.is_dir():
            continue
        root_depth = len(root.parts)
        for current, directories, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.parts) - root_depth
            if root.name == "work":
                relative_parts = current_path.relative_to(root).parts
                if (
                    len(relative_parts) >= 2
                    and relative_parts[1] != workspace.name
                ):
                    directories[:] = []
                    continue
                if len(relative_parts) >= 6:
                    directories[:] = []
                    continue
            if depth >= 6:
                directories[:] = []
            else:
                directories[:] = [
                    name
                    for name in directories
                    if name not in SKIP_DISCOVERY_DIRS
                ]
            if "compile_commands.json" in files:
                candidates.add(
                    (current_path / "compile_commands.json").resolve()
                )
    return sorted(candidates)


def read_database(path: Path) -> list[dict[str, Any]]:
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SetupError(f"Cannot read compilation database {path}: {error}") from error
    if not isinstance(entries, list):
        raise SetupError(f"Compilation database is not a JSON array: {path}")
    return entries


def select_database(
    workspace: Path, explicit_path: Path | None
) -> tuple[Path, dict[str, Any]] | None:
    if explicit_path is not None:
        databases = [explicit_path.expanduser().resolve()]
    else:
        databases = discover_compile_databases(workspace)
    matches: list[tuple[Path, dict[str, Any], int]] = []

    for database in databases:
        if not database.is_file():
            continue
        entries = read_database(database)
        workspace_entries = [
            entry
            for entry in entries
            if isinstance(entry, dict)
            and isinstance(entry.get("directory"), str)
            and isinstance(entry.get("file"), str)
            and Path(entry["file"]).suffix.lower() in CPP_SOURCE_SUFFIXES
            and is_within(resolved_entry_file(entry), workspace)
        ]
        if not workspace_entries:
            continue

        selected = workspace_entries[0]
        entry_score = 1
        for preferred in CPP_SOURCE_PREFERENCE:
            preferred_entry = next(
                (
                    entry
                    for entry in workspace_entries
                    if resolved_entry_file(entry).as_posix().endswith(
                        preferred
                    )
                ),
                None,
            )
            if preferred_entry is not None:
                selected = preferred_entry
                entry_score = 100 - CPP_SOURCE_PREFERENCE.index(preferred)
                break
        if is_within(database, workspace):
            relative_database = database.relative_to(workspace)
            database_depth = len(relative_database.parts) - 1
            database_priority = 3000 - min(database_depth, 10) * 100
        elif is_within(database, workspace / "oe-workdir"):
            database_priority = 2000
        else:
            database_priority = 1000
        score = database_priority + entry_score
        matches.append((database, selected, score))

    if not matches:
        if explicit_path is None:
            return None
        searched = ", ".join(str(path) for path in databases) or "workspace and oe-workdir"
        raise SetupError(
            "No compile_commands.json with a translation unit from this "
            f"workspace was found (searched: {searched}). If this is a "
            "devtool source, run 'devtool build <recipe>' so the generated "
            "database uses this workspace, then retry. Pass "
            "--compile-commands explicitly only if that database contains "
            "translation units from this workspace."
        )

    best_score = max(score for _, _, score in matches)
    best = [(path, entry) for path, entry, score in matches if score == best_score]
    if len(best) != 1:
        paths = "\n".join(f"  {path}" for path, _ in best)
        raise SetupError(
            "More than one matching compilation database was found. "
            "Choose one with --compile-commands:\n" + paths
        )
    return best[0]


def command_arguments(entry: dict[str, Any]) -> list[str]:
    arguments = entry.get("arguments")
    if isinstance(arguments, list) and all(
        isinstance(argument, str) for argument in arguments
    ):
        return arguments
    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    raise SetupError("Selected compile database entry has no command/arguments.")


def compiler_search_paths(
    arguments: list[str], directory: Path, language: str
) -> list[str]:
    if not arguments:
        raise SetupError("Selected compilation command is empty.")
    compiler_token = arguments[0]
    compiler = Path(compiler_token)
    if not compiler.is_absolute():
        located = shutil.which(compiler_token)
        if located:
            compiler = Path(located)
        else:
            compiler = find_yocto_compiler(directory, compiler_token)
    compiler = compiler.resolve()
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise SetupError(
            f"Compiler is not executable: {compiler}.{stale_toolchain_hint()}"
        )

    target_flags = extract_target_flags(arguments[1:])
    command = [
        str(compiler),
        *target_flags,
        "-E",
        "-v",
        "-x",
        language,
        "-",
        "-o",
        os.devnull,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=directory,
            input="",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SetupError(
            f"Could not query compiler include paths: {error}."
            f"{stale_toolchain_hint()}"
        ) from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SetupError(
            f"Compiler include-path query failed ({result.returncode}):\n"
            f"{detail}\n{stale_toolchain_hint().strip()}"
        )

    output = result.stdout + result.stderr
    start_marker = "#include <...> search starts here:"
    end_marker = "End of search list."
    if start_marker not in output or end_marker not in output:
        raise SetupError(
            "Compiler did not report a recognizable system include search list. "
            f"Command was: {shlex.join(command)}"
        )
    search_section = output.split(start_marker, 1)[1].split(end_marker, 1)[0]
    include_paths: list[str] = []
    for line in search_section.splitlines():
        include_path = line.strip().removesuffix(" (framework directory)")
        if include_path and Path(include_path).is_dir():
            normalized = str(Path(include_path).resolve())
            if normalized not in include_paths:
                include_paths.append(normalized)
    if not include_paths:
        raise SetupError(
            "Compiler returned no existing system include paths."
            f"{stale_toolchain_hint()}"
        )
    return include_paths


def find_yocto_compiler(directory: Path, compiler_name: str) -> Path:
    for ancestor in (directory, *directory.parents):
        native_bin = ancestor / "recipe-sysroot-native/usr/bin"
        if native_bin.is_dir():
            for candidate in native_bin.glob(f"*/{compiler_name}"):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate
    raise SetupError(
        f"Compiler {compiler_name!r} is not on PATH and could not be found "
        "under recipe-sysroot-native/usr/bin. Set up the Yocto environment "
        "or pass a usable compilation database."
    )


def extract_target_flags(arguments: list[str]) -> list[str]:
    flags: list[str] = []
    paired_options = {"--sysroot", "-isysroot", "-B"}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in paired_options:
            if index + 1 >= len(arguments):
                raise SetupError(f"Missing argument after {argument}")
            flags.extend((argument, arguments[index + 1]))
            index += 2
            continue
        if argument.startswith(
            (
                "--sysroot=",
                "-march=",
                "-mcpu=",
                "-mfpu=",
                "-mfloat-abi=",
                "-mabi=",
                "-std=",
                "-B",
            )
        ) or argument in {"-mthumb", "-marm", "-EB", "-EL"}:
            flags.append(argument)
        index += 1
    return flags


def intellisense_mode(compiler: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            [str(compiler), "-dumpmachine"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SetupError(f"Could not query compiler target: {error}") from error
    target = result.stdout.strip().lower()
    if result.returncode != 0 or not target:
        target = compiler.name.lower()
    if "aarch64" in target or "arm64" in target:
        return "linux-gcc-arm64"
    if re.search(r"(^|[-_])arm(v[0-9].*)?([-_]|$)", target) or "arm-" in target:
        return "linux-gcc-arm"
    if "x86_64" in target or "amd64" in target:
        return "linux-gcc-x64"
    if "i686" in target or "i386" in target:
        return "linux-gcc-x86"
    raise SetupError(
        f"Cannot infer a C/C++ IntelliSense mode from compiler target {target!r}."
    )


def selected_compiler(arguments: list[str], directory: Path) -> Path:
    if not arguments:
        raise SetupError("Selected compilation command is empty.")
    compiler_token = arguments[0]
    compiler = Path(compiler_token)
    if not compiler.is_absolute():
        located = shutil.which(compiler_token)
        compiler = Path(located) if located else find_yocto_compiler(
            directory, compiler_token
        )
    compiler = compiler.resolve()
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise SetupError(
            f"Compiler is not executable: {compiler}.{stale_toolchain_hint()}"
        )
    return compiler


def language_standard(arguments: list[str], language: str) -> str | None:
    def is_matching_standard(argument: str) -> bool:
        if not argument.startswith("-std="):
            return False
        is_cpp_standard = "++" in argument
        return is_cpp_standard if language == "c++" else not is_cpp_standard

    standards = [
        argument.removeprefix("-std=")
        for argument in arguments
        if is_matching_standard(argument)
    ]
    return standards[-1] if standards else None


def build_settings(
    workspace: Path,
    database: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    arguments = command_arguments(entry)
    directory = Path(entry["directory"]).resolve()
    source = resolved_entry_file(entry)
    language = "c" if source.suffix.lower() == ".c" else "c++"
    compiler = selected_compiler(arguments, directory)
    system_includes = compiler_search_paths(arguments, directory, language)
    settings: dict[str, Any] = {
        "C_Cpp.default.compileCommands": str(database),
        "C_Cpp.default.compilerPath": str(compiler),
        "C_Cpp.default.intelliSenseMode": intellisense_mode(
            compiler, arguments
        ),
        "C_Cpp.default.systemIncludePath": system_includes,
        "C_Cpp.exclusionPolicy": "checkFolders",
    }
    settings.update(
        {
            "C_Cpp.inlayHints.parameterNames.enabled": True,
            "C_Cpp.inlayHints.referenceOperator.enabled": True,
            "C_Cpp.inlayHints.autoDeclarationTypes.enabled": True,
            "C_Cpp.inlayHints.parameterNames.suppressWhenArgumentContainsName": False,
            "C_Cpp.inlayHints.autoDeclarationTypes.showOnLeft": True,
        }
    )
    standard = language_standard(arguments, language)
    if standard is not None:
        standard_key = (
            "C_Cpp.default.cStandard"
            if language == "c"
            else "C_Cpp.default.cppStandard"
        )
        settings[standard_key] = standard

    if (workspace / "redfish-core").is_dir() and (
        workspace / "meson.build"
    ).is_file():
        browse_roots = [
            "redfish-core",
            "http",
            "include",
            "src",
            "config",
            "features/google",
            "features/ibm",
            "features/kvm",
            "features/openbmc_rest",
            "features/serial",
            "features/virtual_media",
            "features/webui_login",
            "test",
        ]
        settings["C_Cpp.default.browse.path"] = [
            "${workspaceFolder}/" + relative
            for relative in browse_roots
            if (workspace / relative).is_dir()
        ]
        settings["C_Cpp.default.browse.limitSymbolsToIncludedHeaders"] = True
        settings["C_Cpp.files.exclude"] = {
            "**/oe-workdir/**": True,
            "**/oe-logs/**": True,
            "**/features/redfish/**": True,
        }
    return settings


def merge_settings(
    existing: dict[str, Any], generated: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(existing)
    for key in ("C_Cpp.files.exclude", "files.exclude"):
        previous_excludes = merged.get(key, {})
        generated_excludes = generated.get(key)
        if isinstance(previous_excludes, dict) and isinstance(
            generated_excludes, dict
        ):
            merged_excludes = dict(previous_excludes)
            merged_excludes.update(generated_excludes)
            generated = dict(generated)
            generated[key] = merged_excludes
    merged.update(generated)
    return merged


def write_settings(
    path: Path,
    settings: dict[str, Any],
    updated_keys: list[str],
    original: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    content = update_jsonc(original or "{}\n", settings, updated_keys)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as output:
            output.write(content)
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    except OSError:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def configure_workspace(
    workspace: Path, explicit_database: Path | None, dry_run: bool
) -> None:
    detected_projects = project_types(workspace)
    generated: dict[str, Any] = {
        "files.exclude": {
            "**/oe-workdir/**": True,
            "**/oe-logs/**": True,
        }
    }
    selected = select_database(workspace, explicit_database)
    if selected is not None:
        database, entry = selected
        generated.update(build_settings(workspace, database, entry))
    settings_path = workspace / ".vscode/settings.json"
    existing: dict[str, Any] = {}
    original_settings: str | None = None
    if settings_path.exists():
        try:
            original_settings = settings_path.read_text(encoding="utf-8")
            if original_settings.strip():
                loaded = parse_jsonc(original_settings)
            else:
                original_settings = "{}\n"
                loaded = {}
        except (OSError, json.JSONDecodeError) as error:
            raise SetupError(
                f"Cannot read existing VS Code settings {settings_path}: {error}"
            ) from error
        except SetupError as error:
            raise SetupError(
                f"Cannot read existing VS Code settings {settings_path}: {error}"
            ) from error
        if not isinstance(loaded, dict):
            raise SetupError(
                f"Existing settings must be a JSON object: {settings_path}"
            )
        existing = loaded
    merged = merge_settings(existing, generated)
    preview_content = update_jsonc(
        original_settings or "{}\n", merged, list(generated)
    )
    if dry_run:
        print(preview_content, end="")
        print(
            f"\nSource: {workspace}",
            f"Detected project types: {', '.join(detected_projects) or 'none'}",
            (
                f"C/C++ compilation database: {database}"
                if selected is not None
                else "C/C++ settings: unchanged (no matching compilation database)"
            ),
            f"Dry run: would update {settings_path}",
            sep="\n",
            file=sys.stderr,
        )
    else:
        write_settings(settings_path, merged, list(generated), original_settings)
        print(f"Updated {settings_path}")
        print(f"Source: {workspace}")
        print(f"Detected project types: {', '.join(detected_projects) or 'none'}")
        if selected is not None:
            print(f"Compilation database: {database}")
            print(f"Translation unit: {resolved_entry_file(entry)}")
        else:
            print(
                "No matching C/C++ compilation database; "
                "C/C++ settings were left unchanged."
            )


def configure_multi_root(sources_directory: Path, dry_run: bool) -> None:
    source_roots = discover_source_roots(sources_directory)
    for source_root in source_roots:
        configure_workspace(source_root, None, dry_run)

    workspace_file = sources_directory.resolve() / "devtool-sources.code-workspace"
    folders = [
        {"path": f"./{source_root.name}"}
        for source_root in source_roots
    ]
    existing: dict[str, Any] = {}
    original_workspace: str | None = None
    if workspace_file.exists():
        try:
            original_workspace = workspace_file.read_text(encoding="utf-8")
            loaded = parse_jsonc(original_workspace)
        except (OSError, json.JSONDecodeError, SetupError) as error:
            raise SetupError(
                f"Cannot read existing workspace file {workspace_file}: {error}"
            ) from error
        if not isinstance(loaded, dict):
            raise SetupError(
                f"Existing workspace file must be a JSON object: {workspace_file}"
            )
        existing = loaded
    merged = dict(existing)
    merged["folders"] = folders
    if dry_run:
        print(
            json.dumps(merged, indent=2) + "\n",
            f"Dry run: would update {workspace_file}",
            f"After applying, open it with: code {workspace_file}",
            (
                "If a recipe has no matching C/C++ compilation database, "
                "run 'devtool build <recipe>' in the initialized build "
                "environment, then rerun this script."
            ),
            sep="\n",
            file=sys.stderr,
        )
    else:
        write_settings(workspace_file, merged, ["folders"], original_workspace)
        print(f"Updated {workspace_file}")
        print(f"Next: open the workspace with: code {workspace_file}")
        print(
            "If a recipe has no matching C/C++ compilation database, run "
            "'devtool build <recipe>' in the initialized build environment, "
            "then rerun this script."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Configure VS Code for an OpenBMC devtool source, or create a "
            "multi-root workspace for all sources under workspace/sources."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help=(
            "devtool source root (or workspace/sources with --multi-root); "
            "defaults to the current or uniquely discovered source tree"
        ),
    )
    parser.add_argument(
        "--multi-root",
        action="store_true",
        help=(
            "configure each source under workspace/sources and create "
            "devtool-sources.code-workspace"
        ),
    )
    parser.add_argument(
        "--compile-commands",
        type=Path,
        help=(
            "compilation database path; auto-discovered in workspace/oe-workdir "
            "when omitted"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the merged settings without writing a file",
    )
    args = parser.parse_args()

    try:
        selected_workspace = args.workspace or Path.cwd()
        is_sources_directory = (
            selected_workspace.name == "sources"
            and selected_workspace.parent.name == "workspace"
        )
        if args.multi_root or is_sources_directory:
            if args.compile_commands is not None:
                raise SetupError(
                    "--compile-commands cannot be used with --multi-root; "
                    "each recipe discovers its own compilation database."
                )
            configure_multi_root(selected_workspace, args.dry_run)
        else:
            workspace = discover_workspace(args.workspace)
            configure_workspace(workspace, args.compile_commands, args.dry_run)
    except SetupError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
