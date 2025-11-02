"""
Reusable helper functions with cross module application.
"""

import time
import warnings
from pathlib import Path
from typing import Any, Callable, List
from zipfile import ZipFile


def run_with_timer(func: Callable, *args, **kwargs) -> Any:
    """
    Runs a function with provided arguments and prints the time taken. Used to test run time of
    functions when developing to ensure performance is satisfactory.

    Args:
        func (Callable): The function to execute.
        *args: Positional arguments to pass to func.
        **kwargs: Keyword arguments to pass to func.

    Returns:
        Any: The return value of the function `func`.
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    print(f"Function '{func.__name__}' executed in {end - start:.4f} seconds.")
    return result


def unzip_files(
    zip_path: Path, target_dir: Path, file_types: List[str] | str | None = None
) -> List[Path]:
    """
    Extract files from a .zip to a target directory with option to extract only specific file types.

    Args:
        zip_path (Path): Path to the .zip to extract from.
        target_dir (Path): Path to the directory where extracted files will be written.
        file_types (list[str] | str | None): Optional list of file types to extract
            (e.g., ['.tif', '.png']). If None, all files will be extracted.

    Returns:
        list[Path]: List of Paths to the extracted files.
    """
    # TODO: add ability to extract specific filenames in addition to specific filepaths
    # if necessary, convert string like path to Path object
    if not isinstance(target_dir, Path):
        target_dir = Path(target_dir)

    # ensure file path is valid and exists - if it doesn't then make it
    if not target_dir.parent.exists():
        target_dir.parent.mkdir(parents=True, exist_ok=True)

    # force convert file_type to lowercase
    if file_types:
        if isinstance(file_types, list):
            file_types = [i.lower() for i in file_types]
        elif isinstance(file_types, str):
            file_types = [file_types.lower()]

    extracted_files = []
    with ZipFile(zip_path, "r") as zip_r:
        target_files = []
        for file in zip_r.namelist():
            # only extract files with specified types
            if file_types:
                if Path(file).suffix.lower() in file_types:
                    target_files.append(file)
            # if no types specified then extract all files
            else:
                target_files.append(file)

        for file in target_files:
            zip_r.extract(file, target_dir)
            extracted_files.append(target_dir / file)

    if not extracted_files:
        # warn user that no files were found
        warnings.warn(
            f"No files with the specified types {file_types} were found in {zip_path.name}.",
            UserWarning,
        )
    return extracted_files
