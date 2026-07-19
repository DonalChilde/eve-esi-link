"""Write text files while creating parent directories and enforcing overwrite policy."""

from pathlib import Path


def save_text_file(
    *,
    text: str,
    directory: Path,
    filename: str,
    overwrite: bool = False,
    encoding: str = "utf-8",
    add_newline: bool = True,
) -> Path:
    """Write text to a file in the target output directory.

    Args:
        text: Text content to write.
        directory: Directory that should contain the output file.
        filename: Name of the output file to create.
        overwrite: If true, replace an existing file. If false, raise an error
            when the target file already exists.
        encoding: Text encoding to use when writing the file.
        add_newline: If true, append a newline character to the end of the text after writing.

    Returns:
        Path object for the written file.

    Raises:
        FileExistsError: If the target file exists and overwrite is false.
        OSError: If the parent directory cannot be created or the file cannot
            be written.

    Notes:
        Parent directories are created automatically when missing.
    """
    output_file = directory / filename
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if overwrite:
        mode = "w"
    else:
        mode = "x"
    with output_file.open(mode, encoding=encoding) as f:
        f.write(text)
        if add_newline:
            f.write("\n")
    return output_file
