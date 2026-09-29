# Erweiterung: Admin-Oberfläche für manuelle Eingriffe

Ergänzung zur bestehenden SPEC.md. Alles Beschriebene kommt zum laufenden
Projekt hinzu, ohne dessen Grundaufbau zu ändern. Beispiele beziehen sich auf
die Konfiguration dieses Repositorys: eigenes Team 1. Herren (`m1`),
Fremdteams 1. Damen und 2. Herren.

## 1. Zweck

Das Skript baut die Feeds bei jedem Lauf vollständig aus den Quellen neu.
Manuelle Eingriffe müssen deshalb als eigene Datenschicht existieren, die bei
jedem Lauf mitgelesen wird. Ein im Kalender gelöschter Termin wäre sonst beim
nächsten Lauf wieder da.

Vier Eingriffe sollen möglich sein:

- einzelne Termine aus den eigenen Feeds ausblenden
- eigene Termine anlegen, die in keiner Quelle stehen
- einzelne Spiele fremder Mannschaften (1. Damen, 2. Herren)
  freischalten
- einzelne Spiele beliebiger Vereine merken, auch solche ohne TBW-Beteiligung

Dazu eine Übersicht, die zeigt, was nach allen Eingriffen tatsächlich in den
Kalendern steht. Das ist die Frage, mit der die App meistens geöffnet wird, und
deshalb ihre Startansicht.

Bedient wird das über eine Weboberfläche, die neben den Feeds auf GitHub Pages
liegt. Kein Server, keine Datenbank.

## 2. Neue Dateien

| Datei | Zweck | Wer schreibt |
| --- | --- | --- |
| `overrides.json` | Sperrliste, eigene Termine, freigeschaltete Fremdspiele, gemerkte Spiele | die App |
| `docs/pool.json` | alle bekannten Termine als Auswahlgrundlage | der Workflow |
| `docs/admin/index.html` | die Oberfläche | einmalig beim Bau |
| `darstellung.json` | Aussehen der Oberfläche (Abschnitt 6, Darstellung) | die App |

### overrides.json

```json
{
  "version": 1,
  "hidden": ["tbw-m1-spiel-380455"],
  "custom": [
    {
      "uid": "tbw-custom-a1b2c3",
      "summary": "Mannschaftsabend",
      "dtstart": "2026-11-14T19:00:00",
      "dtend": "2026-11-14T23:00:00",
      "all_day": false,
      "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
      "description": "",
      "created": "2026-09-24T18:00:00Z"
    }
  ],
  "included": ["tbw-1-damen-spiel-661234"],
  "watch": ["563599"]
}
```

- `hidden`: UIDs, die in keinen Feed geschrieben werden -- auch nicht in den
  Extra-Feed
- `custom`: eigene Termine, landen im Extra-Feed
- `included`: UIDs aus dem Pool fremder Teams, landen im Extra-Feed
- `watch`: Spielnummern von handball.net, landen im Extra-Feed

Die UIDs eigener Termine bekommen das Präfix `tbw-custom-` und eine zufällige
Kennung. Sie bleiben stabil, damit der Kalender bearbeitet statt dupliziert.

`watch` enthält bewusst nur die Spielnummern, nicht die Spieldaten. Titel, Ort
und Liga entstehen bei jedem Lauf neu aus der Quelle -- nur so verschiebt sich
ein verlegtes Spiel mit. Die UID wird daraus gebildet:
`tbw-watch-spiel-563599`.

Ein gemerktes Spiel wird nie aus `watch` entfernt. Abgeschaltet wird es, indem
seine UID in `hidden` landet -- derselbe Weg wie beim Ausblenden eigener
Termine, und damit umkehrbar.

### docs/pool.json

Wird bei jedem Workflow-Lauf neu geschrieben und enthält alle Termine, die das
Skript gesehen hat, auch die der Fremdteams:

```json
{
  "generated": "2026-09-24T06:00:00Z",
  "teams": [
    {
      "key": "m1",
      "name": "1. Herren",
      "own_team": true,
      "color": "#30b0c7",
      "color_dark": "#40c8e0"
    }
  ],
  "feeds": [
    {
      "key": "m1-training",
      "team_key": "m1",
      "name": "1. Herren Training",
      "short_name": "M1 Training"
    },
    {
      "key": "extra",
      "team_key": null,
      "name": "Extra",
      "short_name": "Extra",
      "color": "#5a6270",
      "color_dark": "#9aa3b0"
    }
  ],
  "halls": [
    {
      "name": "Sporthalle Fliethe",
      "address": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland"
    }
  ],
  "events": [
    {
      "uid": "tbw-1-damen-spiel-661234",
      "team": "1. Damen",
      "team_key": "1-damen",
      "own_team": false,
      "type": "spiele",
      "summary": "1. Damen Heim TV Ratingen",
      "dtstart": "2026-10-05T16:00:00+02:00",
      "dtend": "2026-10-05T17:30:00+02:00",
      "all_day": false,
      "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
      "cancelled": false
    }
  ]
}
```

Gemerkte Spiele stehen als eigener Pseudo-Feed im Pool, mit
`team_key: "watch"`, `type: "spiele"` und `own_team: false`. So kann die
Oberfläche sie mit ihrem endgültigen Titel anzeigen, ohne die
Umwandlungsregeln ein zweites Mal in JavaScript nachzubauen.

`team_key` und `type` stehen dort, weil die Oberfläche die Teamfarbe und die
Unterscheidung Spiel/Training an der linken Kante der Zeile zeigt (Abschnitt 6)
und beides nicht aus dem Titel geraten soll. `dtend` und `all_day` braucht sie,
um Ganztagestermine ohne Uhrzeitspalte darzustellen.

Der Pool entsteht aus den Archiven, nicht aus den Quellen. Er enthält deshalb
auch ausgeblendete Termine -- sonst ließe sich ein Ausblenden nicht wieder
zurücknehmen.

`teams` und `feeds` tragen alles mit, was die Oberfläche über die Teams
wissen muss, damit sie nichts davon fest eingebaut hat und in jeder Kopie des
Repositorys unverändert läuft. Beides kommt aus `config.yaml`, in derselben
Reihenfolge:

- `teams`: alle Teams mit Anzeigename, `own_team` und Teamfarbe (`farbe` und
  `farbe_dunkel` in `config.yaml`). Die Reihenfolge ordnet die Filterzeile
  unter „Andere Teams“.
- `feeds`: die abonnierbaren Kalender, also ohne die Pool-Quellen, mit dem
  Extra-Feed zuletzt. `name` steht in der Filterzeile der Übersicht
  (`<Anzeigename> Training|Spiele`), `short_name` in ihrer Kopfzeile
  (`<kurzname> Training|Spiele`, ohne `kurzname` der Anzeigename). Der
  Extra-Feed gehört zu keinem Team und bringt Name und Farbe selbst mit
  (`extra_anzeigename`, `extra_farbe`, `extra_farbe_dunkel`).

`halls` trägt die Hallenliste für die Ortsauswahl im Formular mit. `halls.yaml`
liegt im Wurzelverzeichnis und ist über GitHub Pages nicht erreichbar -- also
dieselbe Begründung, aus der der Pool überhaupt existiert.

Der Pool ist nötig, weil die Oberfläche die fertig umgewandelten Termine
braucht: Titel nach Wunschformat, Adressen aus der Hallentabelle, bereinigte
Gegnernamen. Das alles entsteht im Skript. Dazu reichen die Quellen nicht --
sie liefern nur ein rollierendes Fenster, während der Pool aus den Archiven
kommt und damit auch ältere und ausgeblendete Termine enthält.

Nicht der Grund ist Cross-Origin: handball.net liefert seine Kalender-Endpunkte
mit `access-control-allow-origin: *` aus, ein Browser darf sie also direkt
abrufen. Davon macht nur die Vorschau der gemerkten Spiele Gebrauch
(Abschnitt 3).

## 3. Neue Quellen

In `config.yaml` kommen zwei Teams hinzu, die nur für den Pool gelesen und nie
automatisch in einen Feed geschrieben werden:

| Team | Kürzel | Quelle | Rolle |
| --- | --- | --- | --- |
| 1. Damen | `1-damen` | https://www.handball.net/kalender/team/76182.ics | nur Pool |
| 2. Herren | `2-herren` | https://www.handball.net/kalender/team/74503.ics | nur Pool |

Das Kürzel steckt in der UID (`tbw-1-damen-spiel-661234`) und ändert sich
deshalb nie. Auch diese beiden Teams führen ein Archiv unter `data/`, wie die
eigenen Feeds. Nur so bleibt ein freigeschaltetes Fremdspiel im Extra-Feed
stehen, wenn es aus dem rollierenden Quellfenster fällt, und nur so greift die
Verschwinden-Logik aus SPEC.md Abschnitt 7 auch für sie.

Für diese Teams gilt die Treffpunkt-Logik nicht, sie sind reine
Zuschauertermine. Die Heim-Auswärts-Erkennung und die Adressbereinigung greifen
dagegen wie bei den eigenen Teams, damit Titel und Navigation stimmen.

Eigenname für die Gegnererkennung: aus dem `X-WR-CALNAME` des jeweiligen Feeds
lesen, wie bei den eigenen Teams auch.

### Gemerkte Spiele

Ein paar Mal pro Saison soll ein einzelnes Spiel beliebiger Vereine in den
Kalender, etwa wenn zwei Nachbarvereine gegeneinander spielen. Diese Spiele
haben mit den eigenen Teams nichts zu tun, deshalb gibt es dafür keine
Team-Quelle, sondern einen Abruf pro Spiel:

```
https://www.handball.net/kalender/spiel/<spielnummer>.ics
```

Der Endpunkt liefert genau ein `VEVENT` mit allem Nötigen und antwortet mit
`access-control-allow-origin: *` und `cache-control: public, max-age=900`. Eine
unbekannte Spielnummer ergibt `404` mit `text/plain`, eine nicht-numerische
Eingabe die HTML-Fehlerseite. Validierung ist damit ein Abruf, keine Heuristik.

Beispiel `563599`, ein Spiel ohne TBW-Beteiligung:

```
SUMMARY:TV ALDEKERK II - SG LANGENFELD (41:31)
DTSTART:20260913T150000
DESCRIPTION:Oberliga männliche Jugend A\nSpieltag 1\nSpielnummer …\nFinalizado\n…
LOCATION:SPORTZENTRUM ALDEKERK\, RAHMER KIRCHWEG 19A\, 47647 KERKEN\, 47647 KERKEN
```

Weil der Endpunkt Cross-Origin offen ist, holt die Oberfläche die Vorschau
selbst. Geschrieben wird nur die Spielnummer; die maßgebliche Umwandlung macht
der Workflow. Sonst müssten Hallentabelle, Adressbereinigung und Namensregeln
ein zweites Mal in JavaScript entstehen, mit sicherer Abweichung.

#### Transformation

Abweichend von Abschnitt 6 der SPEC.md, weil hier kein eigenes Team beteiligt
ist und es deshalb kein Heim und kein Auswärts gibt:

| | |
| --- | --- |
| Titel | `<Heim> - <Gast>`, also `TV Aldekerk II - SG Langenfeld` |
| Vorsatz | keiner. Keine Altersklasse, kein Anzeigename, kein Heim/Auswärts |
| Vereinsnamen | nach den Regeln aus SPEC.md Abschnitt 6, **aber** römische Ziffern **und** Mannschaftskennungen bleiben stehen |
| Dauer | 1:30 h ab Anwurf. Die Endzeit der Quelle wird verworfen |
| Notiz | ausschließlich die Liga, also die erste Zeile der `DESCRIPTION`. Kein Treffpunkt |
| Ort | nach den bestehenden Regeln: Hallentabelle, sonst generische Bereinigung |
| UID | `tbw-watch-spiel-<spielnummer>` |
| Ziel | `docs/extra.ics` |

Die Mannschaftskennungen müssen hier bleiben, weil sie die einzige
Unterscheidung sind. `HBD Löwen Oberberg - Solinger TB mA` wäre ohne sie nicht
mehr von einem Spiel der ersten Mannschaft zu unterscheiden -- bei den eigenen
Teams verrät der Feed die Altersklasse, hier gibt es keinen.

Spiele ohne Anwurfzeit werden Ganztagestermine und bekommen statt der Liga
allein die Zeile `Uhrzeit noch offen`, gefolgt von der Liga.

#### Verhalten

- eigenes Archiv unter `data/watch-spiele.json`, wie bei den anderen Feeds
- Verlegung verschiebt den Termin, die UID bleibt stabil
- Rückzug (`Retirado`) erzeugt das `ABGESAGT`-Präfix
- Termine bleiben nach dem Spiel dauerhaft erhalten
- fällt ein Spiel aus der Quelle, greift die Verschwinden-Logik aus SPEC.md
  Abschnitt 7
- schlägt der Abruf einer einzelnen Spielnummer fehl, bleibt ihr Archiveintrag
  unverändert und die übrigen laufen weiter

## 4. Neuer Feed

`docs/extra.ics`, Kalendername `TBW Extra`.

Inhalt, drei Sorten:

- alle Einträge aus `custom`
- alle über `included` freigeschalteten Fremdspiele
- alle über `watch` gemerkten Spiele

Wird wie die anderen Feeds abonniert.

Es bleibt bei einem einzelnen Feed für alles. Getrennte Feeds wären nur dann im
Vorteil, wenn eine der Sorten regelmäßig am Stück ausgeblendet werden soll; das
ist nicht der Fall, und der Preis wäre ein weiteres Abonnement auf jedem Gerät.

Freigeschaltete Fremdspiele bleiben an ihre Quelle gekoppelt. Verlegt der
Verband ein Spiel, verschiebt sich der Termin mit. Wird es zurückgezogen,
greift die normale Absage-Logik inklusive ABGESAGT-Präfix.

## 5. Ablauf im Skript

Nach der bisherigen Transformation und dem Archiv-Abgleich, vor dem Schreiben
der Feeds:

1. `overrides.json` laden. Fehlt die Datei oder ist sie fehlerhaft, mit leeren
   Listen weiterarbeiten und eine Warnung loggen. Die Feeds müssen auch dann
   entstehen.
2. Jede Spielnummer aus `watch` einzeln abrufen, umwandeln und gegen
   `data/watch-spiele.json` mergen.
3. Pool aus allen bekannten Terminen bilden, die gemerkten Spiele als eigenen
   Pseudo-Feed, und nach `docs/pool.json` schreiben.
4. Extra-Feed bauen aus `custom`, den über `included` ausgewählten
   Pool-Einträgen und den gemerkten Spielen.
5. Alle Termine aus `hidden` aus **allen** Feeds entfernen, den Extra-Feed
   eingeschlossen.
6. Alle Feeds schreiben.

Das Archiv bleibt unberührt. Ein ausgeblendeter Termin wird nicht gelöscht,
nur nicht ausgegeben. Deshalb ist jedes Ausblenden umkehrbar.

`hidden` gilt für jeden Feed, nicht nur für die Team-Feeds. Nur so lässt sich
ein gemerktes Spiel abschalten, ohne es zu löschen -- und es ist die
verständlichere Regel: was in `hidden` steht, steht in keinem Kalender.

## 6. Die Oberfläche

Eine einzelne HTML-Datei unter `docs/admin/index.html`, ohne Framework und ohne
Abhängigkeiten von fremden Servern. Schrift ist die Systemschrift, auf
Apple-Geräten also SF Pro.

Die Oberfläche wird meistens auf dem iPhone benutzt, oft kurz vor oder nach
dem Training, und daneben am Mac im Browser. Sie wird für den Daumen entworfen
und muss am Mac genauso gut funktionieren.

### Gestaltungsrichtung

Vorbild ist Software von Apple: auf dem iPhone soll sich die Seite wie eine
iOS-App anfühlen, am Mac wie eine macOS-App. Das Gegenmodell ist die typische
Verwaltungsoberfläche: graue Tabelle, kleine Schaltflächen, alles gleich
wichtig. Die App hat genau eine Aufgabe, nämlich Termine an- und abzuschalten.
Das soll sie so selbstverständlich können wie die Einstellungen-App.

Leitgedanken:

- Die Bausteine von iOS und macOS statt eigener Erfindungen: großer Titel,
  durchscheinende Leisten, Reiterleiste mit Symbolen, gruppierte Listen mit
  abgerundeten Ecken, Häkchen, Chips, Formulare aus beschrifteten Zeilen.
- Farben und Maße nach den Human Interface Guidelines: Systemfarben für
  Hintergrund, Flächen, Text und Trennlinien.
- Bedienelemente standardmäßig in Schwarz, im Dunkelmodus in Weiß; in der
  Darstellung umstellbar auf Blau. Rot nur für Absagen, Fehler und Löschen.
- Ein Blick soll reichen, um Spiel von Training und eigenes Team von fremdem
  Team zu unterscheiden. Dafür ist die farbige Leiste links in der Zeile
  zuständig, wie im Kalender von Apple, nicht ein Etikett im Text.
- Der Zustand ist das Wichtigste auf dem Bildschirm. Ein ausgeblendeter Termin
  muss durchgestrichen und deutlich zurückgenommen wirken, ein
  freigeschalteter Fremdtermin sichtbar aktiv.
- Die Anzeige am Zeilenende (standardmäßig ein Häkchen) bedeutet in jedem
  Bereich dasselbe: das liegt in meinem Kalender. Ein Denkmodell für alle
  vier Listen, egal ob technisch `hidden`, `included` oder `watch`
  dahintersteht.
- Farbig sind nur die Teamfarben. `config.yaml` enthält die vollen
  Grundfarben; wie kräftig sie erscheinen, regelt die Farbstärke in der
  Darstellung (Standard 55 Prozent). Alles andere ist Schwarz, Weiß und Grau.

Bewusst nicht erwünscht: Verlaufsflächen als Dekoration, Schatten auf jeder
Fläche, Einblendanimationen bei jedem Abschnitt, eigene Bedienelemente, wo
das System schon eines hat.

### Aufbau

**iPhone:**

- oben eine schmale Leiste mit dem Zahnrad für die Darstellung links und dem
  Zeitraum rechts. Darunter steht der große Titel des Bereichs. Beim Scrollen wird die Leiste durchscheinend und zeigt
  den Titel klein in der Mitte.
- unten die Reiterleiste mit Symbol und kurzer Beschriftung: `Übersicht`,
  `Meine`, `Andere`, `Gemerkt`, `Neu`
- der Speichern-Knopf erscheint nur, wenn es etwas zu speichern gibt, und
  schwebt dann über der Reiterleiste, wo der Daumen ist. Nichts in der Leiste
  darf breiter werden als der Bildschirm.

**Mac (ab 768 Punkt Breite):**

- links eine Seitenleiste mit den fünf Bereichen und ihren vollen Namen,
  ganz unten die Darstellung
- oben eine Werkzeugleiste mit Titel, Zeitraum und Speichern-Knopf
- Schrift und Zeilen in den etwas kleineren macOS-Größen

Die Übersicht ist die Startansicht.

Die Liste ist nach Datum gruppiert, standardmäßig jeder Tag eine abgerundete
Gruppe. Das Datum steht als Überschrift darüber, grau, der heutige Tag
hervorgehoben. Eine Terminzeile enthält:

```
▌ 19:00   Training 1. Herren                        ✓
▌ 20:30   Sporthalle Fliethe
```

Die farbige Leiste links trägt die Teamfarbe und ist bei Spielen kräftiger
als bei Trainings. Beginn und darunter Ende stehen in einer eigenen Spalte,
damit die Zeiten untereinander eine lesbare Kante bilden. Rechts steht die
Anzeige für an und aus, standardmäßig ein Häkchen, wenn der Termin im
Kalender liegt, sonst nichts. Getroffen wird die ganze Zeile.

Ausgeblendete Termine: Text durchgestrichen und grau, Leiste grau. Sie
bleiben an ihrer Stelle in der Liste stehen. Nicht freigeschaltete Spiele
fremder Teams haben eine hohle Leiste.

### Zustände

Leere Liste: ein kurzer Absatz in ganzen Sätzen, der sagt, was zu tun ist.
Also bei den Fremdteams nicht "Keine Daten", sondern der Hinweis, dass hier
Spiele der anderen Mannschaften des Vereins stehen und jedes einzeln in den
Kalender geholt werden kann. Die Texte nennen keine Teams beim Namen --
welche Teams es gibt, steht allein in `config.yaml`.

Ladezustand: Die Struktur der Liste ist bereits sichtbar, während die Daten
kommen. Kein Ladekreisel über der ganzen Seite.

Fehler: benennen, was nicht geklappt hat, und was zu tun ist. Keine
Entschuldigungen, keine Fehlercodes ohne Erklärung.

### Bewegung

Nur als Antwort auf eine Handlung: das Häkchen blendet ein, ein Termin wird
durchgestrichen, die Leiste wird beim Scrollen durchscheinend. Sonst nichts.
`prefers-reduced-motion` wird respektiert.

### Qualitätsanforderungen

- bedienbar mit einer Hand auf dem iPhone, Schaltflächen mindestens 44 Punkt
- Hell- und Dunkelmodus über `prefers-color-scheme`, mit Farbtokens auf
  `:root`
- Tastaturbedienung mit sichtbarem Fokus
- auf dem iPhone kein Text unter 15 Punkt, ausgenommen die Beschriftungen der
  Reiterleiste; am Mac gelten die macOS-Größen
- unter den Systemleisten des iPhones nichts abgeschnitten, also
  `viewport-fit=cover` und `env(safe-area-inset-*)` verwenden
- die Seite wird nie breiter als der Bildschirm

### Anmeldung

Beim ersten Aufruf fragt die Seite nach einem Zugangsschlüssel. Dieser wird im
lokalen Speicher des Browsers abgelegt, gebunden an die Adresse der App. Er
wird niemals in eine Datei geschrieben oder an Dritte übertragen, sondern nur
im Kopf der Anfragen an die GitHub-Schnittstelle mitgeschickt.

Ein Knopf "Schlüssel entfernen" löscht ihn aus dem Browser.

Antwortet GitHub mit 401 oder 403, erklärt die App, dass der Schlüssel
abgelaufen oder ungültig ist, und fragt erneut danach.

### Darstellung

Alles zum Aussehen lässt sich in der Oberfläche selbst einstellen, über das
Zahnrad oben links (iPhone) oder „Darstellung“ unten in der Seitenleiste
(Mac). Jede Änderung gilt sofort, eine Vorschau mit echten Terminen zeigt sie
an Ort und Stelle.

| Einstellung | Werte | Standard |
| --- | --- | --- |
| Farbstärke | 0 bis 100 Prozent: wie viel der Grundfarbe gegen Grau | 55 |
| Teamfarben | eigene Farbe je Team und für den Extra-Feed, sonst die aus `config.yaml` | keine eigenen |
| Knöpfe | Schwarz/Weiß oder Blau | Schwarz/Weiß |
| An und aus | Häkchen, Kreis, Schalter, Auge | Häkchen |
| Aufbau der Liste | Gruppen, Liste (ohne Karten), Agenda (Datum als Spalte), Kompakt (eine Zeile) | Gruppen |
| Erscheinungsbild | Automatisch, Hell, Dunkel | Automatisch |

Gespeichert wird in `darstellung.json` im Repository, damit iPhone und Mac
gleich aussehen. In diesem Repository steht dort anfangs die Optik, mit der
es gestartet ist: Knöpfe Blau, Schalter, Farbstärke 100:

```json
{
  "version": 1,
  "farbstaerke": 55,
  "akzent": "schwarzweiss",
  "anzeige": "haken",
  "aufbau": "gruppen",
  "modus": "auto",
  "teamfarben": {"m2": "#5856d6"}
}
```

- geschrieben wird kurz nach der letzten Änderung und beim Verlassen des
  Bereichs, ohne Workflow-Lauf -- die Feeds hängen nicht davon ab
- zusätzlich liegt eine Kopie im Browser, damit schon Anmeldung und
  Ladezustand richtig aussehen
- hat ein anderes Gerät inzwischen gespeichert, gewinnt die letzte Änderung
- unbekannte oder kaputte Werte fallen auf den Standard zurück, keiner geht
  ungeprüft in Stile oder Attribute
- eine eigene Teamfarbe ist eine Farbe; für den Dunkelmodus wird sie etwas
  aufgehellt

### Die fünf Bereiche

**Übersicht**

Startansicht. Zeigt alle Termine, die nach Anwendung aller Sperren und
Freischaltungen tatsächlich in den Kalendern stehen -- also genau das, was ein
Blick in die Kalender-App zeigen würde. Chronologisch, nach Datum gruppiert,
gleiche Zeilendarstellung wie überall.

Die Farblinie links trägt hier die Feed-Zugehörigkeit, nicht das Team. Für die
Team-Feeds ist das dasselbe, weil Farbton und Gewicht bereits Team und Typ
unterscheiden. Alles, was im Extra-Feed landet, bekommt einen eigenen
Farbton -- unabhängig davon, aus welchem Team es stammt, denn die Frage
in diesem Bereich ist, in welchem Kalender es steht.

Oben eine Reihe Chips, einer je Feed mit Farbpunkt und Anzahl, davor „Alle“
mit der Summe. Jeder Chip zählt und filtert zugleich. Der Zeitraumfilter aus
der Leiste gilt hier ebenfalls.

Termine lassen sich auch von hier aus ausblenden, mit einem Tipp auf die
Zeile wie überall. Ein ausgeblendeter Termin verschwindet aus diesem Bereich
nicht, sondern bleibt durchgestrichen an seiner Stelle -- sonst wäre das
Ausblenden nicht umkehrbar.

**Meine Termine**

Alle Termine der eigenen Teams aus `pool.json`, chronologisch, nach Datum
gruppiert. Ein Tipp auf die Zeile blendet sie aus oder wieder ein.

**Andere Teams**

Dieselbe Darstellung für die 1. Damen und die 2. Herren. Standardmäßig alles
aus. Einschalten übernimmt den Termin in den Extra-Feed. Oben Chips zum
Eingrenzen auf ein Team.

**Gemerkte Spiele**

Bewusst nicht mit „Andere Teams" vermischt: dort geht es um die anderen
Vereinsmannschaften, hier um beliebige Spiele beliebiger Vereine.

Oben das Eingabefeld. Es nimmt drei Formen an und erkennt selbst, welche
gemeint ist:

| Eingabe | Beispiel |
| --- | --- |
| Spiel-Adresse | `https://www.handball.net/match/563599` |
| ICS-Link des Spiels | `https://www.handball.net/kalender/spiel/563599.ics` |
| nackte Spielnummer | `563599` |

Aus allen drei wird dieselbe Spielnummer gezogen. Gemeint ist die Zahl aus der
Adresse, nicht die Spielnummer des Verbands (`2627NROLAJMA0102`) -- die steht
nur in der Beschreibung und lässt sich über diesen Endpunkt nicht auflösen.

Eine unbrauchbare Eingabe wird abgelehnt, mit dem Hinweis, welche drei Formen
funktionieren. Eine Spielnummer, die handball.net nicht kennt, wird ebenso
abgelehnt, aber mit der Auskunft, dass die Nummer selbst unbekannt ist -- das
sind zwei verschiedene Fehler und sie werden verschieden benannt.

Nach der Eingabe erscheint eine Vorschau mit Datum, Uhrzeit, Begegnung, Halle
und Liga. Sie wird bestätigt oder verworfen. Erst das Bestätigen trägt die
Spielnummer in `watch` ein.

Die Vorschau zeigt die Begegnung so, wie handball.net sie liefert, also in
Großbuchstaben. Ein Hinweis erklärt, dass der Kalendertitel die bereinigte
Schreibweise bekommt. Die Vorschau dient dem Erkennen des richtigen Spiels,
nicht der Typografie -- und die Namensregeln in JavaScript nachzubauen hieße,
sie zweimal zu pflegen.

Darunter die Liste der gemerkten Spiele mit Häkchen. Ausgeschaltete bleiben
durchgestrichen an ihrer Stelle stehen. Ganz entfernen ist nicht vorgesehen.

Ein gerade bestätigtes Spiel steht noch in keinem Archiv. Bis zum nächsten
Workflow-Lauf erscheint es als Zeile mit dem Hinweis, dass es beim nächsten Lauf
geholt wird.

**Eigener Termin**

Formular mit Titel, Datum, Startzeit, Endzeit, Ganztags-Schalter, Ort und
Notiz. Beim Ort eine Auswahlliste der bekannten Hallen aus `halls.yaml` plus
freie Eingabe.

Darunter die bereits angelegten eigenen Termine, jeweils mit Bearbeiten und
Löschen.

### Zeitraum

Standardmäßig nur Termine ab heute. Im Auswahlfeld zusätzlich: Letzte 30 Tage,
Letzte 12 Monate, Alle. Die Auswahl gilt für alle Listenbereiche, also
Übersicht, Meine Termine, Andere Teams und Gemerkte Spiele.

### Speichern

Ein Knopf, beschriftet mit "Speichern und aktualisieren", der zwei Dinge tut:

1. `overrides.json` über die GitHub-Schnittstelle schreiben
2. den Workflow "Feeds aktualisieren" auslösen

Danach zeigt die App den Status des Laufs und meldet, wenn er fertig ist. Ein
Hinweis erklärt, dass die Feeds nach etwa einer Minute stehen und die
Kalender-Apps je nach Einstellung etwas später nachziehen.

Ungespeicherte Änderungen werden sichtbar markiert. Beim Verlassen der Seite
mit ungespeicherten Änderungen kommt eine Rückfrage.

### Konflikte

Vor dem Schreiben prüft die App, ob sich `overrides.json` seit dem Laden
geändert hat. Falls ja, wird gefragt, ob neu geladen oder überschrieben werden
soll. Das kann passieren, wenn die App auf zwei Geräten offen ist.

## 7. Workflow-Anpassungen

- `workflow_dispatch` muss aktiv sein, damit die App den Lauf auslösen kann
- der Lauf schreibt zusätzlich `docs/pool.json` und `docs/extra.ics`
- der Lauf schreibt zusätzlich `data/watch-spiele.json`
- `overrides.json` wird gelesen, aber vom Workflow nie verändert
- `darstellung.json` braucht der Workflow gar nicht, sie gehört allein der
  Oberfläche
- schlägt das Lesen von `overrides.json` fehl, läuft der Rest trotzdem durch
- `fetch-depth: 0` beim Checkout, weil der Commit-Schritt ein `git pull
  --rebase` macht: die App schreibt `overrides.json`, während der Lauf läuft,
  und auf einem flachen Klon schlüge das fehl

## 8. Zugangsschlüssel

Ein eigener Fine-grained Token, getrennt vom Token für die Kommandozeile:

- Repository access: Only select repositories, dort `handball-kalender-HB`
- Permissions: Contents auf Read and write, Actions auf Read and write
- Expiration: 90 Tage

Mehr Rechte braucht die App nicht. Bei Verlust oder Verdacht wird der Token auf
github.com gelöscht und ein neuer erstellt.

Erstellt wird der Token vom Konto `alekspaunovic`, dem das Repository gehört.
Ein Fine-grained Token reicht nur an Repositorys des eigenen Kontos heran, ein
Token eines anderen Kontos kann `handball-kalender-HB` deshalb nicht
auswählen.

Die Adresse der Oberfläche ist
`https://alekspaunovic.github.io/handball-kalender-HB/admin/`. Damit sie erreichbar
ist, muss GitHub Pages auf den Ordner `docs/` des Branches `main` zeigen.

Die Oberfläche liest ihr Repository aus dieser Adresse: der Name vor
`.github.io` ist der Besitzer, der erste Pfadteil das Repository. Fest
eingebaut ist es nicht, damit dieselbe Datei in jeder Kopie läuft. Unter einer
anderen Adresse (etwa lokal geöffnet) kann sie deshalb nichts laden und sagt
das.

Die Seite selbst ist öffentlich erreichbar, das lässt sich bei GitHub Pages
nicht verhindern. Ohne Schlüssel zeigt sie nur eine leere Liste und die
Aufforderung zur Anmeldung. Schreiben kann ohne ihn niemand.

## 9. Tests

- `overrides.json` fehlt: Feeds entstehen trotzdem, Warnung im Log
- `overrides.json` fehlerhaft: gleiches Verhalten
- UID in `hidden`: Termin fehlt im Feed, bleibt aber im Archiv
- UID aus `hidden` entfernt: Termin erscheint wieder
- Eintrag in `custom`: landet im Extra-Feed mit stabiler UID
- UID in `included`: Fremdspiel landet im Extra-Feed
- Freigeschaltetes Fremdspiel wird verlegt: Termin im Extra-Feed verschiebt
  sich, UID bleibt gleich
- Freigeschaltetes Fremdspiel wird zurückgezogen: ABGESAGT-Präfix
- `pool.json` enthält eigene und fremde Termine, korrekt über `own_team`
  unterschieden
- `pool.json` enthält Teams, Feed-Namen und Farben aus `config.yaml` in deren
  Reihenfolge, die Feeds ohne Pool-Quellen und mit dem Extra-Feed zuletzt

Für die gemerkten Spiele:

- Spielnummer in `watch`: Spiel landet im Extra-Feed, UID
  `tbw-watch-spiel-<nummer>`
- Titel ist genau `<Heim> - <Gast>`, ohne Vorsatz und ohne Altersklasse
- römische Ziffern und Mannschaftskennungen bleiben im Titel stehen
  (`TV Aldekerk II - SG Langenfeld`, `HBD Löwen Oberberg - Solinger TB mA`)
- Endzeit ist Anwurf plus 1:30 h, nicht die der Quelle
- Notiz enthält nur die Liga, keinen Treffpunkt
- Ort kommt aus der Hallentabelle, sonst generisch bereinigt
- gemerktes Spiel wird verlegt: Termin verschiebt sich, UID bleibt gleich
- gemerktes Spiel wird zurückgezogen: ABGESAGT-Präfix
- UID eines gemerkten Spiels in `hidden`: fehlt im Extra-Feed, bleibt im Archiv
  und im Pool
- Abruf einer Spielnummer schlägt fehl: die übrigen gemerkten Spiele entstehen
  trotzdem, der Archiveintrag der fehlgeschlagenen bleibt unverändert
- Spiel ohne Anwurfzeit wird Ganztagestermin mit `Uhrzeit noch offen`
- gemerkte Spiele stehen im Pool mit `team_key: "watch"` und `own_team: false`
- steht die UID eines gemerkten Spiels zusätzlich in `included`, kommt es
  trotzdem nur einmal in den Extra-Feed; unter „Andere Teams“ erscheinen
  gemerkte Spiele gar nicht

Für die Eingabe in der Oberfläche:

- alle drei Eingabeformen ergeben dieselbe Spielnummer
- unbrauchbare Eingabe und unbekannte Spielnummer erzeugen verschiedene
  Meldungen

## 10. Offene Punkte

Keine.
