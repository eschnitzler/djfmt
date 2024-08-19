from tree_sitter import Language, Parser

# Load the compiled htmldjango and html languages
HTMLDJANGO_LANGUAGE = Language("lib/htmldjango.so", "htmldjango")
HTML_LANGUAGE = Language("lib/html.so", "html")

# Initialize the parsers
html_parser = Parser()
html_parser.set_language(HTML_LANGUAGE)

django_parser = Parser()
django_parser.set_language(HTMLDJANGO_LANGUAGE)


def extract_html_start_tags(content):
    """
    Extract HTML start tags and their boundaries from the content using Tree-sitter.
    """
    html_tree = html_parser.parse(content)
    html_root_node = html_tree.root_node

    tags = []

    def extract_tags(node):
        if node.type == "start_tag":
            tag_start = node.start_byte
            tag_end = node.end_byte
            tags.append((tag_start, tag_end))
        for child in node.children:
            extract_tags(child)

    extract_tags(html_root_node)
    return tags


def insert_dtl_marker(node, content, replacements, html_start_tags):
    """
    DFS to insert DTL markers around DTL nodes or as attributes on HTML tags.
    """
    if node.type in ["paired_statement", "unpaired_statement"]:
        if is_within_html_start_tag(node, html_start_tags):
            # Insert the DTL content as an attribute
            content = (
                content[: node.start_byte]
                + b'dtl="'
                + content[node.start_byte : node.end_byte].replace(b'"', b"&quot;")
                + b'"'
                + content[node.end_byte :]
            )
        else:
            # Fallback to inserting markers
            start_tag = b"<dtl>"
            end_tag = b"</dtl>"
            replacements.append((node.start_byte, node.start_byte, start_tag))
            replacements.append((node.end_byte, node.end_byte, end_tag))

    for child in node.children:
        content = insert_dtl_marker(child, content, replacements, html_start_tags)

    return content


def is_within_html_start_tag(node, html_start_tags):
    """
    Determine if a node is within an opening HTML tag using start tag boundaries.
    """
    for tag_start, tag_end in html_start_tags:
        if tag_start <= node.start_byte <= tag_end:
            return True
    return False


def apply_replacements(content, replacements):
    """
    Apply the replacements to the content and return the modified content.
    """
    replacements.sort(
        reverse=True
    )  # Sort in reverse order to apply from the end of the content
    for start, end, replacement in replacements:
        content = content[:start] + replacement + content[end:]
    return content


# Read the HTML file as bytes
with open("test.html", "rb") as file:
    file_content = file.read()

# Extract HTML start tag boundaries
html_start_tags = extract_html_start_tags(file_content)

# Parse the content to create a syntax tree for Django template
django_tree = django_parser.parse(file_content)
django_root_node = django_tree.root_node

# Collect replacements for DTL nodes
replacements = []
file_content = insert_dtl_marker(
    django_root_node, file_content, replacements, html_start_tags
)

# Apply replacements to the file content
modified_content = apply_replacements(file_content, replacements)

# Write the modified content to a new file called test_output.html
with open("test/test_output.html", "wb") as output_file:
    output_file.write(modified_content)

print("Formatted content has been written to 'test_output.html'")
