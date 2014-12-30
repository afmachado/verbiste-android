#!/bin/env python3
from xml.dom import minidom
import sqlite3
conn = sqlite3.connect('../assets/conjugation.db')

def get_text(node):
    if node.firstChild == None:
        return None
    return node.firstChild.nodeValue

def get_first(node, childClass):
    return node.getElementsByTagName(childClass)[0]




xmldoc = minidom.parse('../data/verbs-fr.xml')
verbs = xmldoc.getElementsByTagName('v');


verbTypes = {}
verbTypesCounter = 1

# we build the list of verbs
conn.execute(
    '''
    CREATE TABLE verb (
        id INTEGER PRIMARY KEY,
        verb_type_id INTEGER,
        infinitive TEXT,
        radical TEXT,
        h_aspired BOOL
    )
    '''
)
for oneVerb in verbs:
    infinitive = get_text(get_first(oneVerb, 'i'))
    verbType = get_text(get_first(oneVerb, 't'))
    isInitialHPronounced = len(oneVerb.getElementsByTagName('aspirate-h')) == 1


    if verbType not in verbTypes:
        verbTypes[verbType] = verbTypesCounter
        verbTypesCounter += 1

    verbTypeId = verbTypes[verbType]
    conn.execute(
        '''
        INSERT INTO verb
        VALUES(
            NULL,
            ?,
            ?,
            ?,
            ?
        )
        ''',
        [
            verbTypeId,
            infinitive,
            #to get the radical we remove the suffix part that we
            #got from the verb type
            infinitive[:-len(verbType.split(':')[1])],
            isInitialHPronounced
        ]
    )
conn.commit()

# we build the list of verb types
conn.execute(
    '''
    CREATE TABLE verb_type (
        id INTEGER PRIMARY KEY,
        base TEXT,
        part_to_replace TEXT
    )
    '''
)

for verbType, verbTypeId in verbTypes.items():
    conn.execute(
        'INSERT INTO verb_type VALUES(?, ?, ?)',
        [verbTypeId, verbType.replace(':', ''), verbType.split(':')[1]]
    )
conn.commit()


xmldoc = minidom.parse('../data/conjugation-fr.xml')


# we build the list of type of conjugation
MODES = {
    'infinitive' : 1,
    'indicative' : 2,
    'conditional' : 3,
    'subjunctive' : 4,
    'imperative' : 5,
    'participle' : 6
}

TENSES = {
    'infinitive-present' : 1,
    'present' : 2,
    'imperfect' : 3,
    'future' : 4,
    'simple-past' : 5,
    'imperative-present' : 6,
    'present-participle' : 7,
    'past-participle' : 8
}

NOBODY = 1 #for infinitive and participle
FIRST_SINGULAR = 2
SECOND_SINGULAR = 3
THIRD_SINGULAR = 4
FIRST_PLURAL = 5
SECOND_PLURAL = 6
THIRD_PLURAL = 7

PERSONS_NORMAL_TENSE = frozenset([
    FIRST_SINGULAR,
    SECOND_SINGULAR,
    THIRD_SINGULAR,
    FIRST_PLURAL,
    SECOND_PLURAL,
    THIRD_PLURAL
])

conn.execute(
    '''
    CREATE TABLE conjugation (
        id INTEGER PRIMARY KEY,
        verb_type_id INTEGER NOT NULL,
        mode INTEGER NOT NULL,
        tense INTEGER NOT NULL,
        person INTEGER NOT NULL,
        suffix TEXT DEFAULT NULL
    )
    '''
)

def parse_tense(
    verbe_type_id,
    mode,
    tense_name,
    persons_id_for_that_tense=PERSONS_NORMAL_TENSE
):

    tense = get_first(mode, tense_name)

    persons = tense.getElementsByTagName('p')

    for person_id, person in zip(persons_id_for_that_tense, persons):
        for inflection_node in person.getElementsByTagName('i'):
            inflection = get_text(inflection_node)
            conn.execute(
                '''
                INSERT INTO conjugation VALUES (
                    NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                ''',
                [
                    verbe_type_id,
                    MODES[mode.tagName],
                    TENSES[tense_name],
                    person_id,
                    inflection
                ]
            )



templates = xmldoc.getElementsByTagName('template')
for oneTemplate in templates:
    verbType = (oneTemplate.attributes['name'].value)
    verbTypeId = verbTypes[verbType]
    radical = verbType.split(':')[0]

    # Infinitive
    mode = get_first(oneTemplate, 'infinitive')

    parse_tense(
        radical,
        mode,
        'infinitive-present',
        persons_id_for_that_tense=[NOBODY]
    )

    # Indicative
    mode = get_first(oneTemplate, 'indicative')

    parse_tense(verbTypeId, mode, 'present')
    parse_tense(verbTypeId, mode, 'imperfect')
    parse_tense(verbTypeId, mode, 'future')
    parse_tense(verbTypeId, mode, 'simple-past')

    #Conditional
    mode = get_first(oneTemplate, 'conditional')

    parse_tense(verbTypeId, mode, 'present')
#Subjunctive
    mode = get_first(oneTemplate, 'subjunctive')

    parse_tense(verbTypeId, mode, 'present')
    parse_tense(verbTypeId, mode, 'imperfect')

    #imperative
    mode = get_first(oneTemplate, 'imperative')

    parse_tense(
        verbTypeId,
        mode,
        'imperative-present',
        persons_id_for_that_tense=[SECOND_SINGULAR, FIRST_PLURAL, SECOND_PLURAL]
    )

    #participle
    mode = get_first(oneTemplate, 'participle')

    parse_tense(
        verbTypeId,
        mode,
        'present-participle',
        persons_id_for_that_tense=[NOBODY]
    )

    parse_tense(
        verbTypeId,
        mode,
        'past-participle',
        #Note: actually it's supposed to a special case as we store
        # masculine singular
        # feminine singular
        # masculine plural
        # feminine plural
        persons_id_for_that_tense=[
            FIRST_SINGULAR,
            THIRD_SINGULAR,
            FIRST_PLURAL,
            THIRD_PLURAL
        ]
    )

conn.commit()


# create reverse look up tables
conn.execute(
    '''
    CREATE TABLE conjugated_form (
        id INTEGER PRIMARY KEY,
        conjugation_id INTEGER NOT NULL,
        verb_id INTEGER NOT NULL,
        conjugated TEXT
    )
    '''
)

conn.execute(
    '''
    INSERT INTO conjugated_form
    SELECT
        NULL,
        c.id,
        v.id,
        radical || suffix
    FROM verb v
    JOIN verb_type t ON t.id = v.verb_type_id
    JOIN conjugation c ON t.id = c.verb_type_id
    '''
)

# Insert person
conn.execute(
    '''
    CREATE TABLE person (
        id INT PRIMARY KEY,
        base text,
        with_h_aspired text
    )
    '''
)
conn.execute(
    '''
    INSERT INTO person
    VALUES
        (1,    "",      ""),
        (2,   "je",   "j'"),
        (3,   "tu",   "tu"),
        (4,   "il",   "il"),
        (5, "nous", "nous"),
        (6, "vous", "vous"),
        (7,  "ils",  "ils")
    '''
)
conn.commit()

# Android metadata
conn.execute('CREATE TABLE android_metadata (locale TEXT);')
conn.execute('INSERT INTO android_metadata VALUES ("en_US");')
conn.commit()
