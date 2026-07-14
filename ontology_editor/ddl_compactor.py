from __future__ import annotations

import json
import math
import re
from typing import Any

DDL_SINGLE_CALL_TOKEN_BUDGET = 60_000


def analyze_ddl_documents(
    documents: list[dict[str, Any]],
    *,
    single_call_token_budget: int = DDL_SINGLE_CALL_TOKEN_BUDGET,
) -> dict[str, Any]:
    tables: dict[str, dict[str, Any]] = {}
    foreign_keys: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    table_comments: dict[str, str] = {}
    column_comments: dict[tuple[str, str], str] = {}
    raw_bytes = 0

    for index, document in enumerate(documents):
        file_name = str(document.get("name") or f"ddl_{index + 1}.sql")
        content = str(document.get("content") or "")
        raw_bytes += len(content.encode("utf-8"))
        if not content.strip():
            continue
        statements, parse_error = parse_ddl_script(content)
        if parse_error:
            diagnostics.append({"severity": "warning", "file": file_name, "message": parse_error})
        create_count = 0
        for statement in statements:
            if statement["kind"] == "create_table":
                parsed = parse_create_table(statement, file_name)
                if parsed is None:
                    continue
                create_count += 1
                table, statement_foreign_keys = parsed
                merge_table(tables, table)
                foreign_keys.extend(statement_foreign_keys)
            elif statement["kind"] == "alter_table":
                foreign_keys.extend(parse_alter_foreign_keys(statement, file_name))
            elif statement["kind"] == "comment":
                parse_comment_statement(statement, table_comments, column_comments)
        if create_count == 0:
            diagnostics.append(
                {
                    "severity": "warning",
                    "file": file_name,
                    "message": "未发现可用于本体建模的 CREATE TABLE 语句",
                }
            )

    apply_comments(tables, table_comments, column_comments)
    foreign_keys = normalize_foreign_keys(tables, foreign_keys)
    schema = compact_schema(tables, foreign_keys)
    compact_text = schema_to_compact_text(schema)
    estimated_tokens = estimate_tokens(compact_text)
    column_count = sum(len(table.get("columns") or []) for table in schema["tables"])
    chunks = [schema]
    summary = {
        "file_count": len(documents),
        "raw_bytes": raw_bytes,
        "compact_bytes": len(compact_text.encode("utf-8")),
        "compression_ratio": round(len(compact_text.encode("utf-8")) / raw_bytes, 4) if raw_bytes else 0,
        "table_count": len(schema["tables"]),
        "column_count": column_count,
        "foreign_key_count": len(foreign_keys),
        "estimated_tokens": estimated_tokens,
        "single_call_token_budget": single_call_token_budget,
        "over_single_call_token_budget": estimated_tokens > single_call_token_budget,
        "execution_mode": "single",
        "chunk_count": 1,
        "diagnostic_count": len(diagnostics),
    }
    return {
        "schema": schema,
        "compact_text": compact_text,
        "summary": summary,
        "diagnostics": diagnostics,
        "chunks": chunks,
    }


def parse_ddl_script(content: str) -> tuple[list[dict[str, str]], str]:
    raw_statements, errors = split_sql_statements(content)
    statements: list[dict[str, str]] = []
    for raw in raw_statements:
        normalized = raw.strip()
        if not normalized or normalized.upper() == "GO":
            continue
        parsed = parse_create_statement(normalized)
        if parsed:
            statements.append(parsed)
            continue
        parsed = parse_alter_statement(normalized)
        if parsed:
            statements.append(parsed)
            continue
        if re.match(r"(?is)^\s*COMMENT\s+ON\s+", normalized):
            statements.append({"kind": "comment", "raw": normalized})
        else:
            statements.append({"kind": "other", "raw": normalized})
    message = f"DDL 部分解析：{'；'.join(errors[:3])}" if errors else ""
    return statements, message


def split_sql_statements(content: str) -> tuple[list[str], list[str]]:
    statements: list[str] = []
    current: list[str] = []
    errors: list[str] = []
    quote = ""
    dollar_quote = ""
    line_comment = False
    block_comment = False
    depth = 0
    index = 0
    while index < len(content):
        char = content[index]
        following = content[index + 1] if index + 1 < len(content) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
                current.append("\n")
            index += 1
            continue
        if block_comment:
            if char == "*" and following == "/":
                block_comment = False
                current.append(" ")
                index += 2
            else:
                index += 1
            continue
        if dollar_quote:
            if content.startswith(dollar_quote, index):
                current.append(dollar_quote)
                index += len(dollar_quote)
                dollar_quote = ""
            else:
                current.append(char)
                index += 1
            continue
        if quote:
            current.append(char)
            if quote == "]":
                if char == "]" and following == "]":
                    current.append(following)
                    index += 2
                    continue
                if char == "]":
                    quote = ""
            elif char == quote:
                if following == quote:
                    current.append(following)
                    index += 2
                    continue
                quote = ""
            elif char == "\\" and following:
                current.append(following)
                index += 2
                continue
            index += 1
            continue
        if char == "-" and following == "-":
            line_comment = True
            index += 2
            continue
        if char == "#":
            line_comment = True
            index += 1
            continue
        if char == "/" and following == "*":
            block_comment = True
            index += 2
            continue
        if char in "'\"`[":
            quote = "]" if char == "[" else char
            current.append(char)
            index += 1
            continue
        if char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", content[index:])
            if match:
                dollar_quote = match.group(0)
                current.append(dollar_quote)
                index += len(dollar_quote)
                continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                errors.append("存在未匹配的右括号")
                depth = 0
        if char == ";" and depth == 0:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    if quote or dollar_quote:
        errors.append("存在未闭合的引号")
    if block_comment:
        errors.append("存在未闭合的块注释")
    if depth:
        errors.append("存在未闭合的括号")
    return statements, unique_strings(errors)


def parse_create_statement(raw: str) -> dict[str, str] | None:
    match = re.match(
        r"(?is)^\s*CREATE\s+(?:(?:OR\s+REPLACE|GLOBAL\s+TEMPORARY|LOCAL\s+TEMPORARY|TEMPORARY|TEMP|UNLOGGED)\s+)*(?:EXTERNAL\s*)?TABLE\s+",
        raw,
    )
    if not match:
        return None
    position = match.end()
    exists_match = re.match(r"(?is)IF\s+NOT\s+EXISTS\s+", raw[position:])
    if exists_match:
        position += exists_match.end()
    table_name, position = read_qualified_identifier(raw, position)
    position = consume_clickhouse_on_cluster(raw, position)
    position = skip_space(raw, position)
    if not table_name or position >= len(raw) or raw[position] != "(":
        return None
    closing = find_matching_paren(raw, position)
    if closing < 0:
        return None
    return {
        "kind": "create_table",
        "name": table_name,
        "body": raw[position + 1 : closing],
        "tail": raw[closing + 1 :].strip(),
        "raw": raw,
    }


def parse_alter_statement(raw: str) -> dict[str, str] | None:
    match = re.match(r"(?is)^\s*ALTER\s+TABLE\s+", raw)
    if not match:
        return None
    position = match.end()
    only_match = re.match(r"(?is)ONLY\s+", raw[position:])
    if only_match:
        position += only_match.end()
    table_name, position = read_qualified_identifier(raw, position)
    if not table_name:
        return None
    return {"kind": "alter_table", "name": table_name, "body": raw[position:].strip(), "raw": raw}


def parse_create_table(
    statement: dict[str, str],
    file_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    table_name = statement.get("name") or ""
    columns: list[dict[str, Any]] = []
    primary_key: list[str] = []
    unique_keys: list[list[str]] = []
    foreign_keys: list[dict[str, Any]] = []

    for item in split_top_level(statement.get("body") or "", ","):
        definition = strip_constraint_name(item.strip())
        if not definition:
            continue
        keyword = first_word(definition)
        if keyword not in {"PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "KEY", "INDEX", "FULLTEXT", "SPATIAL", "EXCLUDE", "PERIOD", "LIKE"}:
            parsed_column = parse_column(definition, table_name, file_name)
            if parsed_column is None:
                continue
            column, inline_foreign_key = parsed_column
            columns.append(column)
            if column.pop("primary_key", False):
                primary_key.append(column["name"])
            if column.pop("unique", False):
                unique_keys.append([column["name"]])
            if inline_foreign_key:
                foreign_keys.append(inline_foreign_key)
            continue
        if keyword == "PRIMARY":
            primary_key.extend(parse_parenthesized_identifiers(definition))
        elif keyword == "UNIQUE":
            unique_columns = parse_parenthesized_identifiers(definition)
            if unique_columns:
                unique_keys.append(unique_columns)
        elif keyword == "FOREIGN":
            parsed = parse_foreign_key(definition, table_name, file_name)
            if parsed:
                foreign_keys.append(parsed)

    table: dict[str, Any] = {"name": table_name, "columns": columns, "source_file": file_name}
    if primary_key:
        table["primary_key"] = unique_strings(primary_key)
    elif tail_primary_key := extract_clickhouse_primary_key(statement.get("tail") or ""):
        table["primary_key"] = tail_primary_key
    if unique_keys:
        table["unique_keys"] = dedupe_nested(unique_keys)
    comment = extract_comment_clause(statement.get("tail") or "")
    if comment:
        table["comment"] = comment
    return table, foreign_keys


def parse_column(
    definition: str,
    table_name: str,
    file_name: str,
) -> tuple[dict[str, Any], dict[str, Any] | None] | None:
    column_name, position = read_identifier_segment(definition, 0)
    if not column_name:
        return None
    remainder = definition[position:].strip()
    markers = constraint_markers(remainder)
    type_end = markers[0][0] if markers else len(remainder)
    sql_type = remainder[:type_end].strip() or "UNKNOWN"
    column: dict[str, Any] = {
        "name": column_name,
        "type": normalize_value_type(sql_type),
        "sql_type": sql_type,
    }
    upper = remainder.upper()
    is_primary = bool(re.search(r"\bPRIMARY\s+KEY\b", upper))
    if is_primary:
        column["primary_key"] = True
    if re.search(r"\bUNIQUE\b", upper):
        column["unique"] = True
    if is_primary or re.search(r"\bNOT\s+NULL\b", upper):
        column["nullable"] = False
    comment = extract_comment_clause(remainder)
    if comment:
        column["comment"] = comment
    default = extract_default_clause(remainder, markers)
    if default and len(default) <= 120:
        column["default"] = default
    inline_foreign_key = None
    reference_position = keyword_position(remainder, "REFERENCES")
    if reference_position >= 0:
        inline_foreign_key = parse_reference(
            remainder[reference_position:], table_name, [column_name], file_name
        )
    return column, inline_foreign_key


def parse_alter_foreign_keys(statement: dict[str, str], file_name: str) -> list[dict[str, Any]]:
    source = statement.get("name") or ""
    result: list[dict[str, Any]] = []
    body = statement.get("body") or ""
    for match in re.finditer(r"(?is)\bFOREIGN\s+KEY\b", body):
        parsed = parse_foreign_key(body[match.start():], source, file_name)
        if parsed:
            result.append(parsed)
    return result


def parse_foreign_key(
    definition: str,
    source_table: str,
    file_name: str,
) -> dict[str, Any] | None:
    foreign_position = keyword_position(definition, "FOREIGN")
    if foreign_position < 0:
        return None
    opening = definition.find("(", foreign_position)
    closing = find_matching_paren(definition, opening)
    if opening < 0 or closing < 0:
        return None
    source_columns = parse_identifier_list(definition[opening + 1 : closing])
    reference_position = keyword_position(definition, "REFERENCES", closing)
    if reference_position < 0:
        return None
    return parse_reference(definition[reference_position:], source_table, source_columns, file_name)


def parse_reference(
    reference: str,
    source_table: str,
    source_columns: list[str],
    file_name: str,
) -> dict[str, Any] | None:
    match = re.match(r"(?is)\s*REFERENCES\s+", reference)
    if not match:
        return None
    target_table, position = read_qualified_identifier(reference, match.end())
    position = skip_space(reference, position)
    if position >= len(reference) or reference[position] != "(":
        return None
    closing = find_matching_paren(reference, position)
    if closing < 0:
        return None
    target_columns = parse_identifier_list(reference[position + 1 : closing])
    if not source_columns or not target_table:
        return None
    row: dict[str, Any] = {
        "from_table": source_table,
        "from_columns": source_columns,
        "to_table": target_table,
        "to_columns": target_columns,
        "source_file": file_name,
    }
    options_text = re.sub(r"\s+", " ", reference[closing + 1 :]).strip().rstrip(",")
    options = [options_text] if options_text else []
    if options:
        row["options"] = options
    return row


def parse_comment_statement(
    statement: dict[str, str],
    table_comments: dict[str, str],
    column_comments: dict[tuple[str, str], str],
) -> None:
    raw = statement.get("raw") or ""
    match = re.match(r"(?is)^\s*COMMENT\s+ON\s+(TABLE|COLUMN)\s+", raw)
    if not match:
        return
    target, position = read_qualified_identifier(raw, match.end())
    is_position = keyword_position(raw, "IS", position)
    if not target or is_position < 0:
        return
    comment = parse_sql_string(raw[is_position + 2:].strip())
    if not comment:
        return
    if match.group(1).upper() == "TABLE":
        table_comments[target] = comment
    elif "." in target:
        table_name, column_name = target.rsplit(".", 1)
        column_comments[(table_name, column_name)] = comment


def skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def consume_clickhouse_on_cluster(text: str, position: int) -> int:
    position = skip_space(text, position)
    match = re.match(r"(?is)ON\s+CLUSTER\s+", text[position:])
    if not match:
        return position
    cluster_position = skip_space(text, position + match.end())
    if cluster_position >= len(text):
        return position
    if text[cluster_position] == "'":
        closing = cluster_position + 1
        while closing < len(text):
            if text[closing] == "'":
                if closing + 1 < len(text) and text[closing + 1] == "'":
                    closing += 2
                    continue
                return closing + 1
            closing += 1
        return position
    if text[cluster_position] == "{":
        closing = text.find("}", cluster_position + 1)
        return closing + 1 if closing >= 0 else position
    _cluster_name, end = read_identifier_segment(text, cluster_position)
    return end if end > cluster_position else position


def read_identifier_segment(text: str, position: int) -> tuple[str, int]:
    position = skip_space(text, position)
    if position >= len(text):
        return "", position
    opening = text[position]
    if opening in {'"', "`", "["}:
        closing = "]" if opening == "[" else opening
        position += 1
        value: list[str] = []
        while position < len(text):
            char = text[position]
            if char == closing:
                if position + 1 < len(text) and text[position + 1] == closing:
                    value.append(closing)
                    position += 2
                    continue
                return "".join(value), position + 1
            value.append(char)
            position += 1
        return "".join(value), position
    start = position
    while position < len(text) and not text[position].isspace() and text[position] not in ".(),;=":
        position += 1
    return text[start:position], position


def read_qualified_identifier(text: str, position: int) -> tuple[str, int]:
    parts: list[str] = []
    part, position = read_identifier_segment(text, position)
    if not part:
        return "", position
    parts.append(part)
    while True:
        dot_position = skip_space(text, position)
        if dot_position >= len(text) or text[dot_position] != ".":
            return ".".join(parts), position
        part, position = read_identifier_segment(text, dot_position + 1)
        if not part:
            return ".".join(parts), dot_position
        parts.append(part)


def find_matching_paren(text: str, opening: int) -> int:
    if opening < 0 or opening >= len(text) or text[opening] != "(":
        return -1
    depth = 0
    quote = ""
    index = opening
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            if quote == "]":
                if char == "]" and following == "]":
                    index += 2
                    continue
                if char == "]":
                    quote = ""
            elif char == quote:
                if following == quote:
                    index += 2
                    continue
                quote = ""
            elif char == "\\" and following:
                index += 2
                continue
            index += 1
            continue
        if char in "'\"`[":
            quote = "]" if char == "[" else char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def split_top_level(text: str, separator: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            if quote == "]":
                if char == "]" and following == "]":
                    index += 2
                    continue
                if char == "]":
                    quote = ""
            elif char == quote:
                if following == quote:
                    index += 2
                    continue
                quote = ""
            elif char == "\\" and following:
                index += 2
                continue
            index += 1
            continue
        if char in "'\"`[":
            quote = "]" if char == "[" else char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == separator and depth == 0:
            result.append(text[start:index])
            start = index + 1
        index += 1
    result.append(text[start:])
    return result


def top_level_words(text: str) -> list[tuple[str, int, int]]:
    words: list[tuple[str, int, int]] = []
    depth = 0
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            if quote == "]":
                if char == "]" and following == "]":
                    index += 2
                    continue
                if char == "]":
                    quote = ""
            elif char == quote:
                if following == quote:
                    index += 2
                    continue
                quote = ""
            elif char == "\\" and following:
                index += 2
                continue
            index += 1
            continue
        if char in "'\"`[":
            quote = "]" if char == "[" else char
            index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and (char.isalpha() or char == "_"):
            start = index
            index += 1
            while index < len(text) and (text[index].isalnum() or text[index] in "_$"):
                index += 1
            words.append((text[start:index].upper(), start, index))
            continue
        index += 1
    return words


def keyword_position(text: str, keyword: str, start: int = 0) -> int:
    expected = keyword.upper()
    for word, word_start, _word_end in top_level_words(text):
        if word_start >= start and word == expected:
            return word_start
    return -1


def constraint_markers(text: str) -> list[tuple[int, str, int]]:
    marker_words = {
        "CONSTRAINT", "NOT", "NULL", "DEFAULT", "PRIMARY", "UNIQUE", "REFERENCES",
        "CHECK", "COLLATE", "COMMENT", "GENERATED", "IDENTITY", "AUTO_INCREMENT",
        "MATERIALIZED", "ALIAS", "EPHEMERAL", "CODEC", "TTL",
    }
    return [(start, word, end) for word, start, end in top_level_words(text) if word in marker_words]


def first_word(text: str) -> str:
    words = top_level_words(text)
    return words[0][0] if words else ""


def strip_constraint_name(definition: str) -> str:
    if first_word(definition) != "CONSTRAINT":
        return definition
    match = re.match(r"(?is)^\s*CONSTRAINT\s+", definition)
    if not match:
        return definition
    _name, position = read_identifier_segment(definition, match.end())
    return definition[position:].strip()


def parse_parenthesized_identifiers(definition: str) -> list[str]:
    opening = definition.find("(")
    closing = find_matching_paren(definition, opening)
    if opening < 0 or closing < 0:
        return []
    return parse_identifier_list(definition[opening + 1 : closing])


def parse_identifier_list(text: str) -> list[str]:
    result: list[str] = []
    for item in split_top_level(text, ","):
        name, _position = read_identifier_segment(item, 0)
        if name:
            result.append(name)
    return unique_strings(result)


def extract_comment_clause(text: str) -> str:
    position = keyword_position(text, "COMMENT")
    if position < 0:
        return ""
    position += len("COMMENT")
    position = skip_space(text, position)
    if position < len(text) and text[position] == "=":
        position = skip_space(text, position + 1)
    return parse_sql_string(text[position:])


def extract_clickhouse_primary_key(text: str) -> list[str]:
    primary_position = keyword_position(text, "PRIMARY")
    if primary_position < 0:
        return []
    key_position = keyword_position(text, "KEY", primary_position + len("PRIMARY"))
    if key_position < 0:
        return []
    value_position = skip_space(text, key_position + len("KEY"))
    if value_position >= len(text):
        return []
    if text[value_position] == "(":
        closing = find_matching_paren(text, value_position)
        return parse_identifier_list(text[value_position + 1 : closing]) if closing >= 0 else []
    name, _end = read_identifier_segment(text, value_position)
    return [name] if name else []


def extract_default_clause(text: str, markers: list[tuple[int, str, int]]) -> str:
    default_marker = next((item for item in markers if item[1] == "DEFAULT"), None)
    if not default_marker:
        return ""
    value_start = skip_space(text, default_marker[2])
    value_end = len(text)
    for marker_start, _marker_word, _marker_end in markers:
        if marker_start <= value_start:
            continue
        value_end = marker_start
        break
    return text[value_start:value_end].strip()


def parse_sql_string(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0].upper() in {"E", "N"} and value[1] == "'":
        value = value[1:]
    if not value.startswith("'"):
        return value.split(None, 1)[0].rstrip(";") if value else ""
    result: list[str] = []
    index = 1
    while index < len(value):
        char = value[index]
        if char == "'":
            if index + 1 < len(value) and value[index + 1] == "'":
                result.append("'")
                index += 2
                continue
            break
        if char == "\\" and index + 1 < len(value):
            result.append(value[index + 1])
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def apply_comments(
    tables: dict[str, dict[str, Any]],
    table_comments: dict[str, str],
    column_comments: dict[tuple[str, str], str],
) -> None:
    for table_name, comment in table_comments.items():
        resolved = resolve_table_name(tables, table_name)
        if resolved:
            tables[resolved]["comment"] = comment
    for (table_name, column_name), comment in column_comments.items():
        resolved = resolve_table_name(tables, table_name)
        if not resolved:
            continue
        for column in tables[resolved].get("columns") or []:
            if column.get("name") == column_name:
                column["comment"] = comment
                break


def merge_table(tables: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    name = incoming["name"]
    existing = tables.get(name)
    if existing is None:
        tables[name] = incoming
        return
    columns = {column["name"]: column for column in existing.get("columns") or []}
    for column in incoming.get("columns") or []:
        columns[column["name"]] = {**columns.get(column["name"], {}), **column}
    existing["columns"] = list(columns.values())
    for key in ("primary_key", "unique_keys"):
        if incoming.get(key):
            existing[key] = incoming[key]
    if incoming.get("comment"):
        existing["comment"] = incoming["comment"]


def normalize_foreign_keys(
    tables: dict[str, dict[str, Any]],
    foreign_keys: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for row in foreign_keys:
        normalized = dict(row)
        normalized["from_table"] = resolve_table_name(tables, str(row.get("from_table") or "")) or row.get("from_table")
        normalized["to_table"] = resolve_table_name(tables, str(row.get("to_table") or "")) or row.get("to_table")
        key = (
            normalized.get("from_table"),
            tuple(normalized.get("from_columns") or []),
            normalized.get("to_table"),
            tuple(normalized.get("to_columns") or []),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return sorted(
        result,
        key=lambda item: (
            str(item.get("from_table")),
            ",".join(item.get("from_columns") or []),
            str(item.get("to_table")),
        ),
    )


def build_schema_chunks(schema: dict[str, Any], token_budget: int) -> list[dict[str, Any]]:
    tables = schema.get("tables") or []
    if not tables:
        return [schema]
    table_names = {table["name"] for table in tables}
    adjacency: dict[str, set[str]] = {name: set() for name in table_names}
    for foreign_key in schema.get("foreign_keys") or []:
        source = foreign_key[0] if len(foreign_key) > 0 else ""
        target = foreign_key[2] if len(foreign_key) > 2 else ""
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
    components = connected_components(adjacency)
    packed: list[set[str]] = []
    current: set[str] = set()
    for component in components:
        candidate = current | component
        if current and schema_token_count(schema_subset(schema, candidate)) > token_budget:
            packed.append(current)
            current = set()
        if schema_token_count(schema_subset(schema, component)) > token_budget:
            if current:
                packed.append(current)
                current = set()
            packed.extend(split_large_component(schema, component, token_budget))
        else:
            current |= component
    if current:
        packed.append(current)
    return [schema_subset(schema, names) for names in packed] or [schema]


def split_schema_by_column_budget(schema: dict[str, Any], column_budget: int) -> list[dict[str, Any]]:
    budget = max(1, int(column_budget))
    foreign_keys = schema.get("foreign_keys") or []
    table_pieces: list[dict[str, Any]] = []
    for table in schema.get("tables") or []:
        columns = table.get("columns") or []
        if len(columns) <= budget:
            table_pieces.append(table)
            continue
        required_names = set(table.get("primary_key") or [])
        for foreign_key in foreign_keys:
            if len(foreign_key) < 4:
                continue
            if foreign_key[0] == table.get("name"):
                required_names.update(foreign_key[1] or [])
            if foreign_key[2] == table.get("name"):
                required_names.update(foreign_key[3] or [])
        required_columns = [column for column in columns if column and column[0] in required_names]
        optional_columns = [column for column in columns if not column or column[0] not in required_names]
        optional_budget = max(1, budget - len(required_columns))
        for start in range(0, len(optional_columns), optional_budget):
            selected = [*required_columns, *optional_columns[start : start + optional_budget]]
            selected_names = {column[0] for column in selected if column}
            piece = {**table, "columns": selected}
            if table.get("unique_keys"):
                piece["unique_keys"] = [
                    key for key in table["unique_keys"] if set(key).issubset(selected_names)
                ]
            table_pieces.append(piece)

    packed_tables: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_columns = 0
    current_names: set[str] = set()
    for table in table_pieces:
        table_columns = len(table.get("columns") or [])
        table_name = str(table.get("name") or "")
        if current and (current_columns + table_columns > budget or table_name in current_names):
            packed_tables.append(current)
            current = []
            current_columns = 0
            current_names = set()
        current.append(table)
        current_columns += table_columns
        current_names.add(table_name)
    if current:
        packed_tables.append(current)

    result = []
    for tables in packed_tables:
        names = {str(table.get("name") or "") for table in tables}
        result.append(
            {
                "format": schema.get("format") or "oag_compact_ddl_v1",
                "tables": tables,
                "foreign_keys": [
                    item
                    for item in foreign_keys
                    if (len(item) > 0 and item[0] in names) or (len(item) > 2 and item[2] in names)
                ],
            }
        )
    return result or [schema]


def connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    remaining = set(adjacency)
    components = []
    while remaining:
        start = min(remaining)
        queue = deque([start])
        component = set()
        while queue:
            current = queue.popleft()
            if current in component:
                continue
            component.add(current)
            remaining.discard(current)
            queue.extend(sorted(adjacency[current] - component))
        components.append(component)
    return sorted(components, key=lambda item: min(item))


def split_large_component(schema: dict[str, Any], names: set[str], token_budget: int) -> list[set[str]]:
    result: list[set[str]] = []
    current: set[str] = set()
    table_by_name = {table["name"]: table for table in schema.get("tables") or []}
    ordered = sorted(names, key=lambda name: (-len(compact_json(table_by_name[name])), name))
    for name in ordered:
        candidate = current | {name}
        if current and schema_token_count(schema_subset(schema, candidate)) > token_budget:
            result.append(current)
            current = {name}
        else:
            current = candidate
    if current:
        result.append(current)
    return result


def schema_subset(schema: dict[str, Any], names: set[str]) -> dict[str, Any]:
    return {
        "format": schema.get("format") or "oag_compact_ddl_v1",
        "tables": [table for table in schema.get("tables") or [] if table.get("name") in names],
        "foreign_keys": [
            item
            for item in schema.get("foreign_keys") or []
            if (len(item) > 0 and item[0] in names) or (len(item) > 2 and item[2] in names)
        ],
    }


def compact_schema(
    tables: dict[str, dict[str, Any]],
    foreign_keys: list[dict[str, Any]],
) -> dict[str, Any]:
    compact_tables = []
    for table in sorted(tables.values(), key=lambda item: item["name"]):
        compact_table: dict[str, Any] = {
            "name": table["name"],
            "columns": [compact_column(column) for column in table.get("columns") or []],
        }
        if table.get("primary_key"):
            compact_table["primary_key"] = table["primary_key"]
        if table.get("unique_keys"):
            compact_table["unique_keys"] = table["unique_keys"]
        if table.get("comment"):
            compact_table["comment"] = table["comment"]
        compact_tables.append(compact_table)
    compact_foreign_keys = []
    for foreign_key in foreign_keys:
        row: list[Any] = [
            foreign_key.get("from_table"),
            foreign_key.get("from_columns") or [],
            foreign_key.get("to_table"),
            foreign_key.get("to_columns") or [],
        ]
        if foreign_key.get("options"):
            row.append(foreign_key["options"])
        compact_foreign_keys.append(row)
    return {
        "format": "oag_compact_ddl_v1",
        "tables": compact_tables,
        "foreign_keys": compact_foreign_keys,
    }


def compact_column(column: dict[str, Any]) -> list[Any]:
    flags = []
    if column.get("nullable") is False:
        flags.append("not_null")
    if column.get("default") not in (None, ""):
        flags.append(f"default={column['default']}")
    row: list[Any] = [column.get("name"), column.get("type") or "string"]
    if flags or column.get("comment"):
        row.append(flags)
    if column.get("comment"):
        row.append(column["comment"])
    return row


def schema_token_count(schema: dict[str, Any]) -> int:
    return estimate_tokens(schema_to_compact_text(schema))


def schema_to_compact_text(schema: dict[str, Any]) -> str:
    lines = ["# oag-ddl-v1"]
    for table in schema.get("tables") or []:
        table_line = f"T|{escape_compact_value(table.get('name'))}"
        if table.get("comment"):
            table_line += f"|{escape_compact_value(table.get('comment'))}"
        lines.append(table_line)
        column_rows = []
        for column in table.get("columns") or []:
            name = escape_compact_value(column[0] if len(column) > 0 else "")
            value_type = escape_compact_value(column[1] if len(column) > 1 else "string")
            flags = ",".join(escape_compact_value(item) for item in (column[2] if len(column) > 2 else []))
            comment = escape_compact_value(column[3] if len(column) > 3 else "")
            parts = [name, value_type]
            if flags or comment:
                parts.append(flags)
            if comment:
                parts.append(comment)
            column_rows.append(":".join(parts))
        lines.append(f"C|{';'.join(column_rows)}")
        if table.get("primary_key"):
            lines.append("P|" + ",".join(escape_compact_value(item) for item in table["primary_key"]))
        for unique_key in table.get("unique_keys") or []:
            lines.append("U|" + ",".join(escape_compact_value(item) for item in unique_key))
    for foreign_key in schema.get("foreign_keys") or []:
        if len(foreign_key) < 4:
            continue
        source_columns = ",".join(escape_compact_value(item) for item in foreign_key[1])
        target_columns = ",".join(escape_compact_value(item) for item in foreign_key[3])
        line = (
            f"F|{escape_compact_value(foreign_key[0])}({source_columns})>"
            f"{escape_compact_value(foreign_key[2])}({target_columns})"
        )
        if len(foreign_key) > 4 and foreign_key[4]:
            line += "|" + ",".join(escape_compact_value(item) for item in foreign_key[4])
        lines.append(line)
    return "\n".join(lines)


def schema_to_outline_text(schema: dict[str, Any]) -> str:
    lines = ["# oag-ddl-outline-v1"]
    lines.extend(f"T|{escape_compact_value(table.get('name'))}" for table in schema.get("tables") or [])
    for foreign_key in schema.get("foreign_keys") or []:
        if len(foreign_key) < 4:
            continue
        source_columns = ",".join(escape_compact_value(item) for item in foreign_key[1])
        target_columns = ",".join(escape_compact_value(item) for item in foreign_key[3])
        lines.append(
            f"F|{escape_compact_value(foreign_key[0])}({source_columns})>"
            f"{escape_compact_value(foreign_key[2])}({target_columns})"
        )
    return "\n".join(lines)


def escape_compact_value(value: Any) -> str:
    text = str(value or "")
    return (
        text.replace("\\", "\\\\")
        .replace("\r", "")
        .replace("\n", "\\n")
        .replace("|", "\\|")
        .replace(";", "\\;")
        .replace(":", "\\:")
    )


def estimate_tokens(text: str) -> int:
    cjk = sum(1 for char in text if "\u3400" <= char <= "\u9fff")
    non_cjk = max(0, len(text) - cjk)
    return cjk + math.ceil(non_cjk / 3.5)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def normalize_value_type(sql_type: str) -> str:
    normalized = re.sub(r"^[\s\[\]`\"]+|[\s\[\]`\"]+$", "", str(sql_type or ""))
    upper = normalized.upper()
    wrapper = re.match(r"^(?:NULLABLE|LOWCARDINALITY)\s*\((.*)\)$", upper, re.DOTALL)
    if wrapper:
        return normalize_value_type(wrapper.group(1))
    if upper.endswith("[]") or upper.startswith("ARRAY") or upper.startswith("LIST"):
        return "array"
    match = re.match(r"[A-Z][A-Z0-9_]*", upper)
    type_name = match.group(0) if match else ""
    if type_name in {"BOOLEAN", "BOOL", "BIT"}:
        return "boolean"
    if type_name in {"DATE", "DATE32"}:
        return "date"
    if type_name in {"TIME", "TIMETZ", "TIMESTAMP", "TIMESTAMPTZ", "DATETIME", "DATETIME64"}:
        return "datetime"
    if type_name in {"TINYINT", "SMALLINT", "INT", "INTEGER", "BIGINT", "SERIAL", "BIGSERIAL", "MEDIUMINT"} or re.fullmatch(r"U?INT(?:8|16|32|64|128|256)?", type_name):
        return "integer"
    if type_name in {"DECIMAL", "DEC", "NUMERIC", "NUMBER", "FLOAT", "DOUBLE", "REAL", "MONEY", "SMALLMONEY"} or re.fullmatch(r"(?:DECIMAL|FLOAT)(?:32|64|128|256)", type_name):
        return "number"
    if type_name in {"JSON", "JSONB", "STRUCT", "MAP", "OBJECT", "TUPLE"}:
        return "object"
    if type_name == "NESTED":
        return "array"
    return "string"


def resolve_table_name(tables: dict[str, Any], name: str) -> str:
    if name in tables:
        return name
    exact_matches = [table_name for table_name in tables if table_name.casefold() == name.casefold()]
    if len(exact_matches) == 1:
        return exact_matches[0]
    base_name = name.rsplit(".", 1)[-1].casefold()
    matches = [table_name for table_name in tables if table_name.rsplit(".", 1)[-1].casefold() == base_name]
    return matches[0] if len(matches) == 1 else ""


def unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def dedupe_nested(values: list[list[str]]) -> list[list[str]]:
    seen = set()
    result = []
    for value in values:
        normalized = tuple(unique_strings(value))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(list(normalized))
    return result
