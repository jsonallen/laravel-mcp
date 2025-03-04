# Laravel Helpers MCP

⚠️ **ALPHA SOFTWARE WARNING** ⚠️
This package is currently in alpha stage. APIs and functionality may change without notice. Use in production at your own risk.

## Overview
A collection of Laravel helper tools specifically designed for integration with [Cursor IDE](https://cursor.sh), improving development workflow and debugging capabilities directly within your editor.

## Cursor Integration
This package is built to enhance your Laravel development experience in Cursor IDE. All tools are accessible directly through Cursor's command palette and integrate seamlessly with your development workflow.

## Available Tools

- `tail_log_file`: View the most recent entries in your Laravel log file directly in Cursor
- `search_log_errors`: Search through your log files for specific error patterns with integrated results
- `run_artisan_command`: Execute Laravel artisan commands directly from Cursor
- `show_model`: Display model information and relationships in your editor

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/laravel-mcp.git
cd laravel-mcp
```

2. Create a shell script wrapper (e.g., `~/bin/run-laravel-mcp`):
```bash
#!/bin/bash

# Point to your Laravel project path
export LARAVEL_PATH=/path/to/your/laravel/project

# Run the MCP server
mcp run /path/to/laravel-helpers-mcp/server.py
```

3. Make the script executable:
```bash
chmod +x ~/bin/run-laravel-mcp
```

4. Ensure `~/bin` is in your PATH:
```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc  # or ~/.bashrc
source ~/.zshrc  # or source ~/.bashrc
```

## Requirements
- PHP 8.1+
- Laravel 10.0+
- [Cursor IDE](https://cursor.sh)
- [UV](https://github.com/astral-sh/uv) - Modern Python packaging tools

## Contributing
This project is in active development. Issues and pull requests are welcome.

## License
[License Type] - See LICENSE file for details
