"""Unit tests for FileReadTool.

Tests follow TDD Red-Green-Refactor pattern.
"""

import os
import tempfile
from pathlib import Path

import pytest

from nergal.tools.files.read import FileReadTool


class TestFileReadTool:
    """Tests for FileReadTool functionality."""

    @pytest.mark.asyncio
    async def test_read_file_success(self) -> None:
        """Test successfully reading a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello, World!")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "test.txt"})

            assert result.success is True
            assert result.output == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_file_with_absolute_path(self) -> None:
        """Test reading file with absolute path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Content")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": str(test_file)})

            assert result.success is True
            assert result.output == "Content"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self) -> None:
        """Test reading non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "nonexistent.txt"})

            assert result.success is False
            assert result.error is not None
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_file_path_traversal(self) -> None:
        """Test that path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "../outside.txt"})

            assert result.success is False
            assert "outside workspace" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_file_binary(self) -> None:
        """Test reading binary file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "binary.bin"
            test_file.write_bytes(b"\x00\x01\x02\x03")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "binary.bin"})

            assert result.success is True
            assert len(result.output) == 4

    @pytest.mark.asyncio
    async def test_read_empty_file(self) -> None:
        """Test reading empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.txt"
            test_file.write_text("")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "empty.txt"})

            assert result.success is True
            assert result.output == ""

    @pytest.mark.asyncio
    async def test_read_file_with_subdirectory(self) -> None:
        """Test reading file from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("Subdir content")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "subdir/test.txt"})

            assert result.success is True
            assert result.output == "Subdir content"

    @pytest.mark.asyncio
    async def test_tool_properties(self) -> None:
        """Test tool properties."""
        tool = FileReadTool(workspace_dir="/tmp")

        assert tool.name == "file_read"
        assert tool.description is not None
        assert "read" in tool.description.lower()
        assert "file" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_read_file_multiline(self) -> None:
        """Test reading file with multiple lines."""
        content = "Line 1\nLine 2\nLine 3"
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "multiline.txt"
            test_file.write_text(content)

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "multiline.txt"})

            assert result.success is True
            assert result.output == content

    @pytest.mark.asyncio
    async def test_read_file_unicode(self) -> None:
        """Test reading file with unicode content."""
        content = "Привет мир! Hello World! 你好世界"
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "unicode.txt"
            test_file.write_text(content)

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "unicode.txt"})

            assert result.success is True
            assert result.output == content


class TestFileReadToolEdgeCases:
    """Edge case tests for FileReadTool."""

    @pytest.mark.asyncio
    async def test_read_file_special_chars_in_filename(self) -> None:
        """Test reading file with special characters in name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "file with spaces.txt"
            test_file.write_text("Content")

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "file with spaces.txt"})

            assert result.success is True
            assert result.output == "Content"

    @pytest.mark.asyncio
    async def test_read_large_file(self) -> None:
        """Test reading a large file."""
        large_content = "A" * 10000
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "large.txt"
            test_file.write_text(large_content)

            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "large.txt"})

            assert result.success is True
            assert len(result.output) == 10000

    @pytest.mark.asyncio
    async def test_read_file_missing_path_arg(self) -> None:
        """Test reading file without path argument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileReadTool(workspace_dir=tmpdir)
            result = await tool.execute({})

            assert result.success is False
            assert result.error is not None
            assert "path" in result.error.lower()
