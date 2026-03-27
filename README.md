# RLM - Recursive Language Model

A Python-based CLI tool that implements a recursive language model using LuaJIT as a sandboxed execution environment.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
rlm --help
```

## Configuration

Check `.env.example`, it uses litellm for the ai integration.

## Structure

- `rlm/` - Core package
- `cli/` - Command-line interface
- `styles/` - UI assets for TUI
