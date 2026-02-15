"""Utility to convert Markdown formatting to Telegram HTML format.

Telegram supports HTML or MarkdownV2 parsing, but not standard Markdown.
This module converts common Markdown syntax to Telegram-compatible HTML.
"""

import re
from html import escape


def escape_html(text: str) -> str:
    """Escape HTML special characters except in already-converted tags.
    
    Args:
        text: The text to escape.
        
    Returns:
        Text with HTML special characters escaped.
    """
    return escape(text, quote=False)


def markdown_to_telegram_html(text: str) -> str:
    """Convert Markdown formatting to Telegram HTML format.
    
    Converts:
        - **bold** → <b>bold</b>
        - *italic* or _italic_ → <i>italic</i>
        - `code` → <code>code</code>
        - ```code block``` → <pre>code block</pre>
        - [link](url) → <a href="url">link</a>
        - ~~strikethrough~~ → <s>strikethrough</s>
        - ||spoiler|| → <tg-spoiler>spoiler</tg-spoiler>
    
    Also handles nested formatting and escapes HTML special characters.
    
    Args:
        text: Text with Markdown formatting.
        
    Returns:
        Text with HTML formatting compatible with Telegram.
    """
    if not text:
        return text
    
    result = []
    pos = 0
    length = len(text)
    
    while pos < length:
        # Check for code blocks first (```...```) - they take precedence and don't allow nested formatting
        if text[pos:pos+3] == '```':
            end = text.find('```', pos + 3)
            if end != -1:
                code_content = text[pos+3:end]
                code_content = escape_html(code_content)
                result.append(f'<pre>{code_content}</pre>')
                pos = end + 3
                continue
        
        # Check for inline code (`...`) - no nested formatting
        if text[pos] == '`':
            end = text.find('`', pos + 1)
            if end != -1:
                code_content = text[pos+1:end]
                code_content = escape_html(code_content)
                result.append(f'<code>{code_content}</code>')
                pos = end + 1
                continue
        
        # Check for links [text](url)
        if text[pos] == '[':
            link_end = text.find(']', pos + 1)
            if link_end != -1 and link_end + 1 < length and text[link_end+1] == '(':
                url_end = text.find(')', link_end + 2)
                if url_end != -1:
                    link_text = text[pos+1:link_end]
                    url = text[link_end+2:url_end]
                    link_text = markdown_to_telegram_html(link_text)
                    url = escape_html(url)
                    result.append(f'<a href="{url}">{link_text}</a>')
                    pos = url_end + 1
                    continue
        
        # Check for bold (**text**) or bold-italic (***text***)
        if text[pos:pos+2] == '**':
            # Check for *** (bold-italic)
            if pos + 2 < length and text[pos+2] == '*':
                # Find closing *** - search for *** that's not part of longer sequence
                end = pos + 3
                while end < length:
                    end = text.find('***', end)
                    if end == -1:
                        break
                    # Make sure it's not **** or more
                    if end + 3 >= length or text[end+3] != '*':
                        # Found valid closing ***
                        content = text[pos+3:end]
                        content = markdown_to_telegram_html(content)
                        result.append(f'<b><i>{content}</i></b>')
                        pos = end + 3
                        break
                    end += 3
                else:
                    # No closing *** found, treat as ** + *
                    result.append(escape_html(text[pos:pos+2]))
                    pos += 2
                continue
            
            # Regular bold **text**
            end = text.find('**', pos + 2)
            if end != -1:
                # Check if the content has unclosed italic that ends with ***
                # This handles: **bold and *nested italic***
                bold_content = text[pos+2:end]
                
                # Check if there's a single * in content and ** is followed by *
                if '*' in bold_content and '**' not in bold_content and end + 2 < length and text[end+2] == '*':
                    # This might be **...*...*** pattern (bold containing italic ending with ***)
                    # Find the opening * in content
                    italic_start = bold_content.find('*')
                    if italic_start != -1:
                        # Check it's not part of **
                        if italic_start + 1 >= len(bold_content) or bold_content[italic_start+1] != '*':
                            # Yes! This is **text *italic*** pattern
                            before_italic = bold_content[:italic_start]
                            italic_content = bold_content[italic_start+1:]
                            before_italic = markdown_to_telegram_html(before_italic)
                            italic_content = markdown_to_telegram_html(italic_content)
                            result.append(f'<b>{before_italic}<i>{italic_content}</i></b>')
                            pos = end + 3  # Skip ***
                            continue
                
                bold_content = markdown_to_telegram_html(bold_content)
                result.append(f'<b>{bold_content}</b>')
                pos = end + 2
                continue
        
        # Check for spoiler (||text||)
        if text[pos:pos+2] == '||':
            end = text.find('||', pos + 2)
            if end != -1:
                spoiler_content = text[pos+2:end]
                spoiler_content = markdown_to_telegram_html(spoiler_content)
                result.append(f'<tg-spoiler>{spoiler_content}</tg-spoiler>')
                pos = end + 2
                continue
        
        # Check for strikethrough (~~text~~)
        if text[pos:pos+2] == '~~':
            end = text.find('~~', pos + 2)
            if end != -1:
                strike_content = text[pos+2:end]
                strike_content = markdown_to_telegram_html(strike_content)
                result.append(f'<s>{strike_content}</s>')
                pos = end + 2
                continue
        
        # Check for italic (*text* or _text_)
        if text[pos] in ('*', '_'):
            delimiter = text[pos]
            # Make sure it's not part of **, __, ***, etc.
            if pos + 1 < length and text[pos+1] == delimiter:
                # It's ** or __ - output one char and let next iteration handle the pair
                result.append(escape_html(text[pos]))
                pos += 1
                continue
            
            end = text.find(delimiter, pos + 1)
            if end != -1:
                # Check that the closing delimiter is not part of a pair
                if end + 1 < length and text[end+1] == delimiter:
                    # Closing is part of ** - skip this single delimiter
                    result.append(escape_html(text[pos]))
                    pos += 1
                    continue
                
                italic_content = text[pos+1:end]
                italic_content = markdown_to_telegram_html(italic_content)
                result.append(f'<i>{italic_content}</i>')
                pos = end + 1
                continue
        
        # Regular character - escape and add
        result.append(escape_html(text[pos]))
        pos += 1
    
    return ''.join(result)


def split_message_for_telegram(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limits.
    
    Telegram has a 4096 character limit for messages with HTML formatting.
    This function splits at paragraph or sentence boundaries when possible.
    
    Args:
        text: The text to split.
        max_length: Maximum length per chunk (default 4096).
        
    Returns:
        List of text chunks, each within the length limit.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        
        # Try to find a good split point
        split_point = max_length
        
        # Look for paragraph break first
        para_break = remaining.rfind('\n\n', 0, max_length)
        if para_break > max_length // 2:
            split_point = para_break + 2
        else:
            # Look for single newline
            line_break = remaining.rfind('\n', 0, max_length)
            if line_break > max_length // 2:
                split_point = line_break + 1
            else:
                # Look for sentence end
                for end_char in ('. ', '! ', '? ', '。', '！', '？'):
                    sentence_end = remaining.rfind(end_char, 0, max_length)
                    if sentence_end > max_length // 2:
                        split_point = sentence_end + len(end_char)
                        break
                else:
                    # Look for space
                    space = remaining.rfind(' ', 0, max_length)
                    if space > max_length // 2:
                        split_point = space + 1
        
        chunks.append(remaining[:split_point])
        remaining = remaining[split_point:]
    
    return chunks
