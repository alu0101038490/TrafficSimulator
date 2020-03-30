/*
 * Parser Rules
 */
query    : settings statement+ (union|diff|intersect)* outputset output;
statement: ELEMENT (tag|area|around|polygon)+ '->' SET ';' ;
union    : '(' (SET ';')+ ')' ';';
diff     : '(' SET ';- ' (SET ';- ')* SET ';' ')' ';' ;
intersect: ELEMENT SET SET+ ';';
tag      : '[' STRING ':' STRING ']' ;
area     : '(' 'area' ':' INT ')';
around   : '(' 'around' ':' INT ')';
polygon  : '(' 'poly' ':' coors ')';
coors    : '"' (NUMBER NUMBER)+ '"' ;
outputset: '(' SET ';' '>' ';' ')' ';' ;
output   : 'out' 'meta' ';' ;

setting  : '[' SETTINGNAME ':' STRING ']' ;
settings : setting+ ';' ;

/*
 * Lexer Rules
 */
WHITESPACE : ('\r'|'\n'|'\t'|'\f'|'\v'|' ') ;
ELEMENT    : 'node' | 'way' | 'rel' | 'area' | 'nw' | 'nr' | 'wr' | 'nwr'
SETTINGNAME: 'date' ;
INT        : \d+;
NUMBER     : -?\\d+(\\.\\d+)? ;
STRING : ([\"'])((?:[^\1\\]|\\.)*?)\1 ;
SET        : \\.[a-zA-Z_]\\w* ;