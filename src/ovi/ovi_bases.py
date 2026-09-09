"""Harvest Obsidian Bases for the Bases tab.

A base is a saved database view over the vault: a YAML document naming a set
of filters, the properties it shows and one or more *views* (table, cards, ...)
of the notes that match. Obsidian keeps one in a ``.base`` file, and a note can
also embed one in a ```` ```base ```` code fence.

A base is a tree and a worksheet is a table, so the tab shows one row per
view. What belongs to the base as a whole -- its filters, its formulas and the
number of properties it configures -- is repeated on each of its rows, so any
one row is self-contained once the sheet is filtered or re-sorted. Filters are
rendered as a single boolean expression rather than as nested YAML.

Row layout, which ``DefBase`` and the ``export_tab`` 'base' branch both depend
on, is given by the ``ROW_ID`` .. ``PROPS`` indexes below. Slot ``BASE_PATH``
holds the path of the ``.base`` file, or of the note that embeds the base; the
exporter turns it into an Obsidian link.
"""

from pathlib import Path
from typing import Any

import yaml

from ovi.ovi_logger import logger

#: Column order of one row, in the sheet's order.
(ROW_ID, BASE_PATH, FOLDER, KIND, VIEW, VIEW_TYPE, FILTERS, VIEW_FILTERS,
 COLUMNS, SORT, GROUP_BY, LIMIT, FORMULAS, PROPS) = range(14)

#: Values of the Kind column.
KIND_FILE = 'File'
KIND_EMBEDDED = 'Embedded'

#: Type markers for rows that are not a view. A base that declares no views
#: still gets one row, or its filters and formulas would never be seen; a base
#: that does not parse gets one so the problem is on the sheet rather than in
#: the log.
NO_VIEWS = '(no views)'
INVALID_YAML = '(invalid YAML)'
NOT_A_MAPPING = '(not a mapping)'

#: Folder column for a base sitting in the vault root -- a blank there would
#: read as "unknown".
VAULT_ROOT = '(vault root)'

#: Joins the items of a list column: columns, sort keys, formula names.
SEP = ' | '

#: The code-fence signature ``VaultScan.extract_codeblock_info`` produces for
#: an embedded base.
EMBEDDED_SIG = 'BASE'

#: Vault folders never scanned for .base files. ``.trash`` holds deleted ones.
_SKIPPED_PARTS = frozenset({'.obsidian', '.trash'})


class BasesData:
    """Collect the vault's bases into rows for ``obs_bases``.

    :param dir_vault: the vault root.
    :param skip_dirs: absolute directories to leave out, as ``sys_cfg``
        carries them in ``skip_abs_lst``.

    ``.base`` files are read on construction. A base embedded in a note is
    added by ``add_embedded()`` as the vault walk meets it, so ``pack_rows()``
    is called once the walk is over.
    """

    def __init__(self, dir_vault, skip_dirs=()):
        self.dir_vault = Path(dir_vault)
        self.skip_dirs = [Path(d) for d in skip_dirs if d]
        self.rows = []

        self.scan_files()

    # ------------------------------------------------------------------ input

    def scan_files(self):
        for path in sorted(self.dir_vault.rglob('*.base')):
            if self.is_skipped(path):
                continue

            try:
                text = path.read_text(encoding='utf-8-sig')
            except OSError as e:
                logger.warning(f"BasesData: could not read {path}: {e}")
                continue

            self.add_base(str(path), KIND_FILE, text)

    def is_skipped(self, path):
        relative = path.relative_to(self.dir_vault)
        if any(part in _SKIPPED_PARTS for part in relative.parts):
            return True
        return any(skip in path.parents for skip in self.skip_dirs)

    def add_embedded(self, note_path, block):
        """Add a base from a ```` ```base ```` fence.

        ``block`` is the fence as ``VaultScan.extract_codeblocks`` returns it,
        opening and closing backtick lines included.
        """
        lines = block.strip().splitlines()
        body = '\n'.join(lines[1:-1]) if len(lines) > 2 else ''
        self.add_base(str(note_path), KIND_EMBEDDED, body)

    # ------------------------------------------------------------------- walk

    def add_base(self, path, kind, text):
        folder = self.folder_of(path)

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            logger.debug(f"BasesData: invalid YAML in {path}: {e}")
            self.add_row(path, folder, kind, '', INVALID_YAML,
                         filters=str(e).splitlines()[0] if str(e) else '')
            return

        if data is None:
            data = {}
        if not isinstance(data, dict):
            self.add_row(path, folder, kind, '', NOT_A_MAPPING)
            return

        filters = self.render_filter(data.get('filters'))
        formulas = data.get('formulas')
        formulas = SEP.join(str(k) for k in formulas) if isinstance(formulas, dict) else ''
        properties = data.get('properties')
        props = len(properties) if isinstance(properties, dict) else 0

        views = data.get('views') or []
        if not isinstance(views, list):
            views = [views]

        if not views:
            self.add_row(path, folder, kind, '', NO_VIEWS,
                         filters=filters, formulas=formulas, props=props)
            return

        for view in views:
            if not isinstance(view, dict):
                view = {'name': str(view)}

            limit = view.get('limit')
            self.add_row(path, folder, kind,
                         str(view.get('name') or ''),
                         str(view.get('type') or ''),
                         filters=filters,
                         view_filters=self.render_filter(view.get('filters')),
                         columns=self.join_list(view.get('order')),
                         sort=self.render_sort(view.get('sort')),
                         group_by=self.render_sort(view.get('groupBy')),
                         limit='' if limit is None else limit,
                         formulas=formulas,
                         props=props)

    def folder_of(self, path):
        """The base's folder, vault-relative with forward slashes."""
        try:
            relative = Path(path).relative_to(self.dir_vault)
        except ValueError:
            return Path(path).parent.as_posix()

        parent = relative.parent.as_posix()
        return VAULT_ROOT if parent == '.' else parent

    # -------------------------------------------------------------- rendering

    @classmethod
    def render_filter(cls, node: Any, top: bool = True) -> str:
        """One boolean expression for a Bases filter tree.

        Obsidian nests ``and`` / ``or`` / ``not`` lists to any depth. Each
        list becomes its items joined by its operator, parenthesised when it
        sits inside another; ``not`` is "none of these", so it reads
        ``NOT (a OR b)``. A bare list is an ``and``. Anything else is shown as
        written.
        """
        if node is None or node == '':
            return ''
        if isinstance(node, list):
            return cls.render_group('AND', node, top)
        if not isinstance(node, dict):
            return str(node)

        parts = []
        for key, sub in node.items():
            op = str(key).upper()
            items = sub if isinstance(sub, list) else [sub]

            if op == 'NOT':
                inner = cls.render_group('OR', items, top=True)
                if inner:
                    parts.append(f'NOT ({inner})')
            elif op in ('AND', 'OR'):
                rendered = cls.render_group(op, items, top and len(node) == 1)
                if rendered:
                    parts.append(rendered)
            else:
                parts.append(f'{key}: {cls.render_filter(sub, top=False)}')

        return ' AND '.join(parts)

    @classmethod
    def render_group(cls, op: str, items: list[Any], top: bool) -> str:
        rendered = [r for r in (cls.render_filter(i, top=False) for i in items) if r]
        if not rendered:
            return ''
        if len(rendered) == 1:
            return rendered[0]

        joined = f' {op} '.join(rendered)
        return joined if top else f'({joined})'

    @staticmethod
    def render_sort(sort):
        """``property DIRECTION`` per entry; also fits a ``groupBy`` mapping."""
        if not sort:
            return ''
        items = sort if isinstance(sort, list) else [sort]

        rendered = []
        for item in items:
            if isinstance(item, dict):
                prop = str(item.get('property') or '')
                direction = str(item.get('direction') or '')
                rendered.append(f'{prop} {direction}'.strip())
            else:
                rendered.append(str(item))

        return SEP.join(rendered)

    @staticmethod
    def join_list(value):
        if not value:
            return ''
        if isinstance(value, list):
            return SEP.join(str(v) for v in value)
        return str(value)

    # ----------------------------------------------------------------- output

    def add_row(self, path: str, folder: str, kind: str, view: str, view_type: str,
                filters: str = '', view_filters: str = '', columns: str = '',
                sort: str = '', group_by: str = '', limit: int | str = '',
                formulas: str = '', props: int | str = '') -> None:
        # Slot 0 is the RowId, which ExcelExporter overwrites with the sheet row
        # number. It is carried here so the list is already in column order.
        self.rows.append([0, path, folder, kind, view, view_type, filters,
                          view_filters, columns, sort, group_by, limit,
                          formulas, props])

    def pack_rows(self):
        """Wrap the rows in the two-level shape ``ExcelExporter.export_tab()`` unpacks.

        Same arrangement as ``QuickAddData.pack_rows``: a zero-padded sequence
        number used as both keys, so the dict, the YAML batch file and the
        sheet all keep the same order.
        """
        return {f"{i:05d}": {f"{i:05d}": row} for i, row in enumerate(self.rows, 1)}


def main() -> None:
    pass


if __name__ == '__main__':
    main()
