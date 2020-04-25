import re
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
import osmnx as ox


class OverpassQLHighlighter(QSyntaxHighlighter):

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        self.formats = []

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(144, 83, 138))
        keywordPattern = "(?<!\\w)(node|way|rel|nwr|nw|nr|wr|w|n|r|derived|area|timeout|out|maxsize|bbox|date|diff|if" \
                         "|foreach|for|complete|retro|compare|delta|ids|skel|body|tags|meta|geom|bb|center|asc|qt" \
                         "|is_in|local|timeline|convert|make|id|around|poly|newer|changed|user|uid|pivot|type|t" \
                         "|is_tag|keys|version|timestamp|changeset|count_tags|count_members|count_distinct_members" \
                         "|count_by_role|count_distinct_by_role|per_member|per_vertex|pos|mtype|ref|role|is_closed" \
                         "|geom|length|lat|lon|lstr|min|max|sum|count|gcat|number|is_number|suffix|is_date|trace|hull" \
                         "|lrs_in|lrs_isect|lrs_union|lrs_min|lrs_max)(?!\\w)"

        self.formats.append((keywordPattern, keywordFormat, 0))

        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(104, 151, 187))
        numberPattern = "-?\\d+(\\.\\d+)?"

        self.formats.append((numberPattern, numberFormat, 0))

        setNameFormat = QTextCharFormat()
        setNameFormat.setForeground(QColor(197, 116, 50))
        setNamePattern = "\\.[a-zA-Z_]\\w*"

        self.formats.append((setNamePattern, setNameFormat, 0))

        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(105, 133, 88))
        stringPattern = r"([\"'])((?:[^\1\\]|\\.)*?)\1"

        self.formats.append((stringPattern, stringFormat, 0))

    def highlightBlock(self, text):
        for pattern, format, group in self.formats:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(group), match.end(group) - match.start(group), format)

        self.setCurrentBlockState(0)


def getIdFromLocationName(name):
    if name == "":
        return None
    item = next((x for x in ox.nominatim_request({"q": name, 'format': 'json'})
                 if x['osm_type'] != 'node'), None)
    if item is None:
        return item
    id = item['osm_id']
    if item['osm_type'] == 'relation':
        id += 3600000000
    elif item['osm_type'] == 'node':
        id += 2400000000
    return id
