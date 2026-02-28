"""Unit tests for FileWriteTool.

Tests follow TDD Red-Green-Refactor pattern.
"""

import os
import tempfile
from pathlib import Path

import pytest

from nergal.tools.files.write import FileWriteTool


class TestFileWriteTool:
    """Tests for FileWriteTool functionality."""

    @pytest.mark.asyncio
    async def test_write_file_success(self) -> None:
        """Test successfully writing a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "test.txt",
                "content": "Hello, World!"
            })

            assert result.success is True
            assert result.output is not None

    @pytest.mark.asyncio
    async def test_write_file_create_subdirectory(self) -> None:
        """Test writing file that requires creating subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "subdir/new_file.txt",
                "content": "Content"
            })

            assert result.success is True
            assert "written" in result.output.lower()
            file_path = Path(tmpdir) / "subdir" / "new_file.txt"
            assert file_path.exists()
            assert file_path.read_text() == "Content"

    @pytest.mark.asyncio
    async def test_write_file_overwrite(self) -> None:
        """Test overwriting an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Original content")

            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "test.txt",
                "content": "New content"
            })

            assert result.success is True
            assert test_file.read_text() == "New content"


    @pytest.mark.asyncio
    async def test_write_file_empty_content(self) -> None:
        """Test writing empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "empty.txt",
                "content": ""
            })

            assert result.success is True
            file_path = Path(tmpdir) / "empty.txt"
            assert file_path.exists()
            assert file_path.read_text() == ""

    @pytest.mark.asyncio
    async def test_write_file_unicode(self) -> None:
        """Test writing unicode content."""
        content = "Привет мир! 你好世界"
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "unicode.txt",
                "content": content
            })

            assert result.success is True
            file_path = Path(tmpdir) / "unicode.txt"
            assert file_path.read_text() == content

    @pytest.mark.asyncio
    async def test_write_file_missing_path(self) -> None:
        """Test writing file without path argument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({"content": "Test content"})

            assert result.success is False
            assert result.error is not None
            assert "path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_file_binary(self) -> None:
        """Test writing binary content (bytes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            binary_content = b"\x00\x01\x02\x03"
            result = await tool.execute({
                "path": "binary.bin",
                "content": binary_content,
            })

            assert result.success is True
            # Binary content should be written correctly
            file_path = Path(tmpdir) / "binary.bin"
            assert file_path.read_bytes() == binary_content

    @pytest.mark.asyncio
    async def test_write_file_missing_content(self) -> None:
        """Test writing file without content argument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({"path": "test.txt"})

            assert result.success is False
            assert result.error is not None
            assert "content" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_file_path_traversal(self) -> None:
        """Test that path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "../../../outside.txt",
                "content": "Dangerous"
            })

            assert result.success is False
            assert "outside workspace" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_file_with_create_flag(self) -> None:
        """Test write with create flag set to True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)

            # First write to create file
            result1 = await tool.execute({
                "path": "test.txt",
                "content": "First write",
            })
            assert result1.success is True

            # Second write with create=True should fail
            result2 = await tool.execute({
                "path": "test.txt",
                "content": "Second write",
                "create": True,
            })
            assert result2.success is False
            assert "already exists" in result2.error.lower()

    @pytest.mark.asyncio
    async def test_tool_properties(self) -> None:
        """Test tool properties."""
        tool = FileWriteTool(workspace_dir="/tmp")

        assert tool.name == "file_write"
        assert tool.description is not None
        assert "write" in tool.description.lower()
        assert "file" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_write_file_large_content(self) -> None:
        """Test writing file with large content."""
        large_content = "A" * 100000
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "large.txt",
                "content": large_content
            })

            assert result.success is True
            file_path = Path(tmpdir) / "large.txt"
            assert file_path.read_text() == large_content


class TestFileWriteToolEdgeCases:
    """Edge case tests for FileWriteTool."""

    @pytest.mark.asyncio
    async def test_write_file_special_chars_in_filename(self) -> None:
        """Test writing file with special characters in name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "file with spaces.txt",
                "content": "Content"
            })

            assert result.success is True
            file_path = Path(tmpdir) / "file with spaces.txt"
            assert file_path.exists()
            assert file_path.read_text() == "Content"

    @pytest.mark.asyncio
    async def test_write_file_with_newlines(self) -> None:
        """Test writing file with newlines."""
        content = "Line 1\nLine 2\nLine 3"
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool(workspace_dir=tmpdir)
            result = await tool.execute({
                "path": "newlines.txt",
                "content": content
            })

            assert result.success is True
            file_path = Path(tmpdir) / "newlines.txt"
            assert file_path.read_text() == content
