from mcp.server.fastmcp import FastMCP, Context
import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Union, List, Dict
import base64
from dataclasses import dataclass
import io
from pathlib import Path
import sys
import logging
import re

# Simple file logging
log_file = os.path.expanduser("~/laravel-helpers-mcp.log")
state_file = os.path.expanduser("~/laravel-helpers-state.json")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_state() -> Dict[str, Union[int, float]]:
    """Load the file tracking state from disk"""
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load state file: {e}")
    return {'size': 0, 'mtime': 0.0, 'position': 0}

def save_state(state: Dict[str, Union[int, float]]) -> None:
    """Save the file tracking state to disk"""
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error(f"Failed to save state file: {e}")

# Store Laravel directory and file tracking info
laravel_dir: Optional[Path] = None
last_file_check = load_state()

def initialize_laravel_dir() -> None:
    """Initialize and validate the Laravel directory from LARAVEL_PATH env var"""
    global laravel_dir, last_file_check
    
    laravel_path = os.getenv('LARAVEL_PATH')
    if not laravel_path:
        error = "LARAVEL_PATH environment variable is not set"
        logging.error(error)
        raise ValueError(error)
    
    laravel_dir = Path(os.path.expanduser(laravel_path))
    logging.info(f"Initializing Laravel directory from LARAVEL_PATH: {laravel_dir}")

    if not laravel_dir.exists():
        error = f"Laravel directory not found: {laravel_dir}"
        logging.error(error)
        raise ValueError(error)

    if not (laravel_dir / 'artisan').exists():
        error = f"Not a valid Laravel directory (no artisan file found): {laravel_dir}"
        logging.error(error)
        raise ValueError(error)

    # Initialize file tracking for the log file
    log_path = laravel_dir / 'storage' / 'logs' / 'laravel.log'
    if log_path.exists():
        stats = log_path.stat()
        last_file_check['size'] = stats.st_size
        last_file_check['mtime'] = stats.st_mtime
        last_file_check['position'] = stats.st_size
        logging.info(f"Initialized file tracking: size={stats.st_size}, mtime={datetime.fromtimestamp(stats.st_mtime)}")

    logging.info(f"Laravel directory validated successfully: {laravel_dir}")

# Initialize when module is loaded
initialize_laravel_dir()

# Initialize FastMCP with a descriptive name
mcp = FastMCP(
    "Laravel Helper Tools",
    description="Tools for working with Laravel applications"
)


@mcp.tool()
async def tail_log_file(ctx: Context, lines: int = 10) -> str:
    """Tail the last N lines of the Laravel log file
    
    Args:
        ctx: MCP context for logging and progress tracking
        lines: Number of lines to tail from the log file
    
    Returns:
        The last N lines from the Laravel log file
    """
    global laravel_dir
    if laravel_dir is None:
        error_msg = "Laravel directory not initialized"
        logging.error(error_msg)
        await ctx.error(error_msg)
        return f"Error: {error_msg}"

    logging.info(f"Tail log file called with lines={lines}")
    log_path = laravel_dir / 'storage' / 'logs' / 'laravel.log'
    
    if not log_path.exists():
        error_msg = f"Log file not found at {log_path}"
        logging.error(error_msg)
        await ctx.error(error_msg)
        return f"Error: {error_msg}"
    
    try:
        logging.debug(f"Reading last {lines} lines from {log_path}")
        await ctx.info(f"Reading last {lines} lines from {log_path}")
        result = subprocess.run(
            ["tail", f"-n{lines}", str(log_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logging.debug(f"Successfully read {lines} lines from log file")
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Error executing tail command: {str(e)}"
        logging.error(f"Tail command failed: {str(e)}")
        await ctx.error(error_msg)
        return error_msg

@mcp.tool()
async def search_log_errors(
    ctx: Context, 
    minutes_back: int = 1,
    show_all: bool = False
) -> str:
    """Search the Laravel log file for errors within a specified time window
    
    Args:
        ctx: MCP context for logging and progress tracking
        minutes_back: Number of minutes to look back for errors (default: 1, max: 60)
        show_all: If True, show all errors in time window. If False, only show new errors since last check.
    
    Returns:
        Found error messages with timestamps
    """
    global laravel_dir, last_file_check
    
    # Validate minutes_back range
    if minutes_back < 1 or minutes_back > 60:
        error_msg = "minutes_back must be between 1 and 60"
        logging.error(error_msg)
        await ctx.error(error_msg)
        return f"Error: {error_msg}"
    
    if laravel_dir is None:
        error_msg = "Laravel directory not initialized"
        logging.error(error_msg)
        await ctx.error(error_msg)
        return f"Error: {error_msg}"

    log_path = laravel_dir / 'storage' / 'logs' / 'laravel.log'
    if not log_path.exists():
        error_msg = f"Log file not found at {log_path}"
        logging.error(error_msg)
        await ctx.error(error_msg)
        return f"Error: {error_msg}"
    
    try:
        # Check if file has been modified
        stats = log_path.stat()
        file_modified = (
            stats.st_size != last_file_check['size'] or 
            stats.st_mtime > last_file_check['mtime']
        )
        
        if not file_modified and not show_all:
            return "No new errors found (file unchanged)"
            
        # Calculate the time window
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=minutes_back)
        logging.debug(f"Current time: {now}, Searching for errors between {cutoff_time} and {now}")
        await ctx.info(f"Searching for errors in the last {minutes_back} minute(s)")

        # If showing all errors, read from start of time window
        # If showing only new, read from last position
        if show_all:
            # Use tail first to get recent content, then grep for errors
            result = subprocess.run(
                ["tail", "-n", "1000", str(log_path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Now search this content for errors in our time window
            content = result.stdout
        else:
            # Use tail to read only new content
            bytes_to_read = stats.st_size - last_file_check['position']
            if bytes_to_read > 0:
                result = subprocess.run(
                    ["tail", "-c", str(bytes_to_read), str(log_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                content = result.stdout
            else:
                return "No new errors found (no new content)"
        
        # Process the output to filter by timestamp and format nicely
        errors = []
        timestamp_pattern = r'\[([\d-]+ [\d:]+)\]'
        
        for line in content.splitlines():
            if 'ERROR:' not in line:
                continue
                
            # Extract timestamp
            match = re.search(timestamp_pattern, line)
            if not match:
                continue
                
            try:
                # Parse the timestamp in the local timezone
                timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                
                # Only include errors that are:
                # 1. Not from the future
                # 2. Within our time window
                if timestamp <= now and timestamp >= cutoff_time:
                    # Format the error message nicely
                    errors.append(f"Time: {timestamp}\nError: {line.split('ERROR:', 1)[1].strip()}\n")
            except ValueError:
                # Skip lines with invalid timestamps
                continue
        
        # Update tracking info
        if not show_all:
            last_file_check['size'] = stats.st_size
            last_file_check['mtime'] = stats.st_mtime
            last_file_check['position'] = stats.st_size
            logging.debug(f"Updated file tracking: size={stats.st_size}, mtime={datetime.fromtimestamp(stats.st_mtime)}")
        
        if not errors:
            return f"No {'new ' if not show_all else ''}errors found in the last {minutes_back} minute(s)"
            
        # Sort errors by timestamp to show most recent first
        errors.sort(reverse=True)
        logging.debug(f"Found {len(errors)} errors")
        return "\n".join(errors)
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Error reading log file: {str(e)}"
        logging.error(f"Command failed: {str(e)}")
        await ctx.error(error_msg)
        return error_msg

@mcp.tool()
async def run_artisan_command(ctx: Context, command: str) -> str:
    """Run an artisan command in the Laravel directory"""
    try:
        result = subprocess.run(
            ["php", "artisan"] + command.split(),
            cwd=laravel_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Error running artisan command: {e.stderr}"
        logging.error(f"Artisan command failed: {error_msg}")
        await ctx.error(error_msg)
        return f"Error: {error_msg}"

@mcp.tool()
async def show_model(ctx: Context, model_name: str) -> str:
    """Show details about a Laravel model, focusing on relationships
    
    Args:
        ctx: MCP context for logging
        model_name: Name of the model to inspect (e.g., 'User', 'Post')
    
    Returns:
        Model details with relationships highlighted
    """
    logging.info(f"Showing model details for: {model_name}")
    await ctx.info(f"Getting information about model: {model_name}")
    
    # Run the model:show command
    output = await run_artisan_command(ctx, f"model:show {model_name}")
    
    # If there was an error, return it directly
    if output.startswith("Error:"):
        return output
    
    # Process the output to highlight relationships
    lines = output.splitlines()
    formatted_lines = []
    in_relations_section = False
    
    for line in lines:
        # Check for relationship methods
        if any(rel in line.lower() for rel in ['hasone', 'hasmany', 'belongsto', 'belongstomany', 'hasmanythrough']):
            # Add a blank line before relationships section if we just entered it
            if not in_relations_section:
                formatted_lines.append("\nRelationships:")
                in_relations_section = True
            
            # Clean up and format the relationship line
            line = line.strip()
            if line:
                # Extract relationship type and related model
                rel_match = re.search(r'(hasOne|hasMany|belongsTo|belongsToMany|hasManyThrough)\(([^)]+)\)', line)
                if rel_match:
                    rel_type, rel_args = rel_match.groups()
                    formatted_lines.append(f"- {rel_type}: {rel_args}")
                else:
                    formatted_lines.append(f"- {line}")
        else:
            # For non-relationship lines, just add them as-is
            if line.strip():
                formatted_lines.append(line)
    
    # If we found no relationships, add a note
    if not in_relations_section:
        formatted_lines.append("\nNo relationships found in this model.")
    
    return "\n".join(formatted_lines)

if __name__ == "__main__":
    logging.info("Starting Laravel Helper Tools server")
    mcp.run()

