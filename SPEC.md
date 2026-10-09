# Handball-Kalender-Feeds TB Wülfrath

Spezifikation für ein Skript, das aus SpielerPlus- und handball.net-Feeds
zwei eigene ICS-Kalender für die 1. Herren erzeugt und per GitHub Pages
veröffentlicht.

Dieses Repository ist eine Kopie von `alekspaunovic/handball-kalender`. Code
und Regeln sind dieselben, was sich unterscheidet, steht in `config.yaml`.

## 1. Ziel

Ein Nutzer spielt in der 1. Herren des TB Wülfrath. Trainings kommen aus
SpielerPlus, Spiele aus handball.net.
Beide Quellformate gefallen ihm nicht. Das Skript liest die Quell-Feeds,
schreibt die Termine in ein festes Wunschformat um und veröffentlicht sie als
statische ICS-Dateien, die im Apple-Kalender abonniert werden.

Wichtig: Es werden keine Termine in einen Kalender geschrieben. Das Skript
erzeugt ausschließlich Dateien. Der Nutzer abonniert die URLs.

## 2. Quellen

### SpielerPlus (Trainings und sonstige Termine)

| Team | URL |
| --- | --- |
| M1 | aus GitHub Secret SPIELERPLUS_M1 |

Diese URL ist ein personalisierter Geheim-Link. Sie gehört in GitHub Secrets,
nicht ins Repository.

### handball.net (Spiele)

| Team | URL |
| --- | --- |
| M1 | https://www.handball.net/kalender/team/75787.ics |

Diese URL ist öffentlich und kann in der Konfiguration stehen.

### Abgrenzung der Quellen

Die SpielerPlus-Feeds enthalten auch Spiele und weitere Termine, die nicht in
den Kalender gehören. Die Unterscheidung erfolgt über das UID-Präfix, das
SpielerPlus vergibt. Die echten Feeds enthalten vier Präfixe: `training.`,
`event.`, `game.` und `absence.`

Es gilt eine Positivliste, konfigurierbar über `spielerplus_uid_prefixes` in
`config.yaml`:

- `training.<id>` wird übernommen
- `event.<id>` wird übernommen
- `game.<id>` wird verworfen (die Spieldaten kommen aus handball.net, sonst
  landen Spiele doppelt im Kalender)
- `absence.<id>` wird verworfen (Abwesenheiten sind für den Kalender
  irrelevant)
- alle anderen, unbekannten Präfixe werden ebenfalls verworfen und im Log als
  Warnung ausgegeben, damit nichts stillschweigend verlorengeht

## 3. Ausgabe

Zwei Feeds, getrennt nach Typ:

| Datei | Inhalt | Quelle |
| --- | --- | --- |
| `m1-training.ics` | Trainings und sonstige Termine 1. Herren | SpielerPlus M1 |
| `m1-spiele.ics` | Spiele 1. Herren | handball.net 75787 |

Fehlt die SpielerPlus-URL, wird der Training-Feed nicht erzeugt. Das Skript
darf deswegen nicht abbrechen.

Kalender-Header je Datei:

```
X-WR-CALNAME:TBW 1. Herren Training      (bzw. TBW 1. Herren Spiele)
X-WR-TIMEZONE:Europe/Berlin
X-PUBLISHED-TTL:PT6H
REFRESH-INTERVAL;VALUE=DURATION:PT6H
```

Es werden keine VALARM-Komponenten erzeugt. Keine Wegzeit, keine Erinnerungen.
Der Nutzer setzt sich das bei Bedarf selbst.

## 4. Team-Konfiguration

| Kürzel | Anzeigename | Eigenname bei handball.net | Treffpunkt Spiel | Treffpunkt Training | Spieldauer |
| --- | --- | --- | --- | --- | --- |
| M1 | 1. Herren | TB Wülfrath | 1:15 h vorher | 5 min vorher | 1:30 h |

Als Eigenname zählen der Name aus der Tabelle (`handballnet_name` in
`config.yaml`) und der `X-WR-CALNAME` des jeweiligen handball.net-Feeds,
beide gleichberechtigt. Der `X-WR-CALNAME` zieht mit, wenn handball.net ein
Team umbenennt -- im Herbst 2026 wurde etwa aus `TB Wülfrath`
`TB Wülfrath M1` --, `config.yaml` nicht. Fremdteams haben gar keinen
`handballnet_name`, bei ihnen zählt nur der `X-WR-CALNAME`. Vergleich immer
case-insensitiv und ohne Mehrfach-Leerzeichen, weil die Schreibweise zwischen
den Feeds schwankt (`TB WÜLFRATH III` vs. `TB Wülfrath II`).

## 5. Transformation Trainings (SpielerPlus)

### Titel

Grundform: `Training <Anzeigename>`

Beispiel: `Training 1. Herren`

Der SpielerPlus-Titel hat das Muster `Training - <Ortszusatz>` oder nur
`Training`. Ist ein Ortszusatz vorhanden, wird er angehängt:

`Training - Erbacher Berg` wird zu `Training 1. Herren - Erbacher Berg`

Termine, deren Titel nicht mit `Training` beginnt (Beispiele aus den Rohdaten:
`Teamevent`, `Auftakt zur Vorbereitung`), bekommen die Form
`<Anzeigename>: <Originaltitel>`, also `1. Herren: Teamevent`.

### Zeiten

Start und Ende werden unverändert aus der Quelle übernommen, inklusive
`TZID=Europe/Berlin`. Auch dann, wenn die Quelle einen längeren Hallenblock
liefert als die tatsächliche Trainingszeit. Das ist so gewollt.

### Ort

Manche SpielerPlus-Feeds haben kein LOCATION-Feld, der Ort steckt nur im
Titelzusatz (im Ursprung die M3). Andere haben teils LOCATION plus GEO plus
`X-APPLE-STRUCTURED-LOCATION` -- SpielerPlus liefert dort aber teils nur
eine unvollständige Rohadresse (z.B. `42 Wülfrath, Deutschland`), die keine
verlässliche Information ist. Ein Ortszusatz im Titel, der in der
Hallentabelle bekannt ist, geht deshalb vor. Regel in dieser Reihenfolge:

1. Ortszusatz im Titel, der in der Hallentabelle (Abschnitt 8) bekannt ist:
   Adresse aus der Tabelle, unabhängig davon, ob zusätzlich eine LOCATION
   vorliegt.
2. Kein bekannter Ortszusatz, aber Quelle liefert LOCATION: diese
   verwenden, zusammen mit GEO und `X-APPLE-STRUCTURED-LOCATION`, falls
   vorhanden. Entspricht die Adresse einer Halle aus der Hallentabelle,
   stattdessen den Eintrag aus der Hallentabelle nehmen, damit die
   Schreibweise einheitlich bleibt.
3. Kein bekannter Ortszusatz und keine LOCATION: Standardhalle Fliethe

SpielerPlus gibt den Trainingsort teils explizit als Ortszusatz `Halle` an,
gemeint ist die Standardhalle Fliethe. Das wird wie gar kein Ortszusatz
behandelt: Ort ist Fliethe (Fall 3) und `Halle` taucht nicht im Titel auf,
also `Training 1. Herren` statt `Training 1. Herren - Halle`.
4. Unbekannter Ortszusatz im Titel und keine LOCATION: Ortszusatz als
   reinen Text setzen und im Log warnen

In den Fällen, in denen die Adresse aus der Hallentabelle kommt (Fall 1,
Fall 2 bei Treffer, Fall 3), wird sie als vollständiger String geschrieben:

```
LOCATION:Sporthalle Fliethe\, Fortunastraße 30\, 42489 Wülfrath\, Deutschland
```

Zusätzlich `GEO` und `X-APPLE-STRUCTURED-LOCATION` aus der Hallentabelle
setzen, damit Apple die Navigation direkt anbietet.

### Notizen

- Training: `Treffpunkt: HH:MM` mit Beginn minus 5 Minuten
- sonstige Termine (Teamevent etc.): keine Notiz

Die Quell-DESCRIPTION enthält nur den SpielerPlus-Link und wird verworfen.

## 6. Transformation Spiele (handball.net)

### Heim oder Auswärts

Bestimmt über die Halle, nicht über die Spielplanseite. Liegt das Spiel in der
Heimhalle (Fliethe, bei handball.net `MTC ARENA WÜLFRATH`, Fortunastraße 30),
gilt es als Heimspiel, sonst als Auswärtsspiel.

Grund (Beispiel aus dem Ursprung): Am 19.09. hat die C-Jugend vier Spiele in
der Voss-Arena Wippperfürth, bei zweien steht TB Wülfrath auf der Heimseite.
Das ist ein Turnier, faktisch also auswärts. Nach Halle bestimmt liefert das
richtige Ergebnis.

Hat ein Spiel gar kein LOCATION-Feld, wird `Auswärts` angenommen und geloggt.

### Gegner

Die SUMMARY hat die Form `<Heim> - <Gast>`, teilweise mit angehängtem Ergebnis
in Klammern. Vorgehen:

1. Ergebnis in Klammern am Ende abtrennen und merken
2. An ` - ` splitten
3. Die Seite, die einem der Eigennamen des Teams (Abschnitt 4) entspricht,
   ist man selbst
4. Die andere Seite ist der Gegner. Passt keine Seite, gilt die Heimseite als
   Gegner und das Skript loggt eine Warnung -- meist hat handball.net das
   Team umbenannt.

Achtung: Bei `TB WÜLFRATH III - TB WÜLFRATH IV` stehen auf beiden Seiten
TB Wülfrath. Der Vergleich muss deshalb auf den vollständigen Seitenstring
gehen, nicht auf ein Teilstring-Enthaltensein.

### Gegnername normalisieren

handball.net liefert Namen in Großbuchstaben und mit Zusätzen. Ziel ist die
Schreibweise aus dem Wunschformat, also `Lüttringhauser TV`.

Regeln:

1. Mojibake reparieren, siehe Abschnitt 9
2. Ist der Name bereits gemischt geschrieben, unverändert lassen
3. Ist er komplett groß, in Title Case wandeln, dabei bekannte Abkürzungen
   groß lassen: TV, TB, TSV, TuS, TUS, HV, HC, EV, SV, SG, JSG, HSV, SSG, DJK,
   MTG, MTV, VfL, VfB, HG, HSG, SC, FC, TG.
   Die Wandlung greift auch hinter Bindestrich und Punkt innerhalb eines
   Wortes: `WALD-MERSCHEIDER` wird `Wald-Merscheider`,
   `INTERAKTIV.HANDBALL` wird `Interaktiv.Handball`.
4. Angehängte Mannschaftskennungen entfernen. handball.net hängt sie je
   Spielklasse unterschiedlich an, und weil die Feeds schon nach Team getrennt
   sind, ist die Kennung des Gegners darin redundant:
   - Herren und Damen: `1M`, `2.M`, `2.Herren`, `1F`, `1D`, `2.Damen`
   - Jugend mit Ziffer: `C1J`, `B2`, `A1J`
   - Jugend kurz: `mA`, `mC`, `wB`
   - Jugend ausgeschrieben: `männl. C-Jugend`, `weibl. B-Jugend`
5. Römische Zahlen am Ende (II, III, IV) beibehalten -- sie unterscheiden
   echte Mannschaften und sind keine Spielklassenkennung
6. Die Rechtsform `e.V.` entfernen, egal wo im Namen sie steht. Der Punkt
   hinter dem `e` ist dafür Pflicht, damit das Vereinskürzel `EV` (etwa
   `EV Duisburg`) unangetastet bleibt.
7. Mehrfache Leerzeichen zusammenfassen

Beispiele:

| Quelle | Ergebnis |
| --- | --- |
| `Lüttringhauser TV` | `Lüttringhauser TV` |
| `NEUSSER HV 1M` | `Neusser HV` |
| `DJK GRÜN WEISS WERDEN 2.M` | `DJK Grün Weiss Werden` |
| `SSG WUPPERTAL/HSV WUPPERTAL` | `SSG Wuppertal/HSV Wuppertal` |
| `TB WÜLFRATH IV` | `TB Wülfrath IV` |
| `TUS LINTFORT` | `TuS Lintfort` |
| `MTG Horst Essen` | `MTG Horst Essen` |
| `WALD-MERSCHEIDER TV` | `Wald-Merscheider TV` |
| `JSG ELLER-GERRESHEIM C1J` | `JSG Eller-Gerresheim` |
| `INTERAKTIV.HANDBALL DÜSSELDORF/RATINGEN 2M` | `Interaktiv.Handball Düsseldorf/Ratingen` |
| `DJK UNITAS HAAN E.V. II` | `DJK Unitas Haan II` |
| `FORTUNA DÜSSELDORF 1895 E.V. 1F` | `Fortuna Düsseldorf 1895` |
| `Solinger TB mC` | `Solinger TB` |
| `Kettwiger SV 70/86 männl. C-Jugend` | `Kettwiger SV 70/86` |

Eine Override-Tabelle in der Konfiguration erlaubt es, Einzelfälle von Hand zu
korrigieren. Sie wird vor allen Regeln geprüft.

### Titel

`<Anzeigename> <Heim|Auswärts> <Gegner>`

Beispiel: `1. Herren Heim Lüttringhauser TV`

Bei Absage wird `ABGESAGT ` vorangestellt:
`ABGESAGT 1. Herren Heim Lüttringhauser TV`

### Zeiten

Startzeit ist die Anwurfzeit aus der Quelle. Die Endzeit von handball.net ist
immer Start plus zwei Stunden und damit nicht brauchbar. Sie wird durch die
Spieldauer aus der Team-Konfiguration ersetzt, also Herren 1:30 h und Jugend
1:15 h.

Spiele ohne Anwurfzeit kommen als Ganztagestermin
(`DTSTART;VALUE=DATE`). Diese bleiben Ganztagestermine, bekommen keine
Treffpunkt-Notiz, sondern die Notiz `Uhrzeit noch offen`.

### Ort

Adresse aus der Hallentabelle, falls die Halle bekannt ist. Sonst generische
Bereinigung nach Abschnitt 9. Immer als vollständiger String mit
`, Deutschland` am Ende.

Für Heimspiele wird die Halle immer als `Sporthalle Fliethe` ausgegeben, nie
als `MTC Arena Wülfrath`.

### Notizen

Zeile 1: `Treffpunkt: HH:MM` (Anwurf minus Vorlauf laut Team-Konfiguration).
Bei Auswärtsspielen ist der Treffpunkt an der Gasthalle, es braucht deshalb
keinen Zusatztext.

Zeile 2, nur wenn ein Ergebnis in der SUMMARY stand: `Ergebnis: 34:25
(Gewonnen)`. Das Ergebnis bleibt in der Reihenfolge der Quelle (Heim:Gast).
Die Wertung in Klammern -- `Gewonnen`, `Verloren` oder `Unentschieden` --
gilt aus Sicht des Teams und richtet sich nach seiner Seite in der SUMMARY,
nicht nach Heim/Auswärts im Titel: Beim Turnier steht TB Wülfrath auf der
Heimseite, obwohl auswärts gespielt wird. Entspricht keine Seite einem
Eigennamen (Abschnitt 4), entfällt die Wertung, ebenso bei `0:0` -- das ist
im Handball kein Ergebnis, sondern ein Platzhalter der Quelle.

Ganztagestermine bekommen statt Zeile 1 die Zeile `Uhrzeit noch offen`.

Die restliche Quell-DESCRIPTION (Liga, Spieltag, Spielnummer, Status, Link)
wird verworfen. Der Link wandert in das URL-Feld.

## 7. Absagen und Verlegungen

handball.net führt in der DESCRIPTION ein Statuswort:

| Wort | Bedeutung | Verhalten |
| --- | --- | --- |
| `Pendiente` | ausstehend | normal |
| `Finalizado` | gespielt | normal, Ergebnis in die Notiz |
| `Retirado` | zurückgezogen | sofort als abgesagt markieren |

Weitere unbekannte Statuswörter: als normal behandeln und loggen.

Zusätzlich die Verschwinden-Logik, für Spiele und Trainings: Ist ein Termin
im Archiv, taucht aber nicht mehr in der Quelle auf, bleibt er zunächst
unverändert stehen. Erst wenn er vorbei ist und weiterhin fehlt, bekommt er
das ABGESAGT-Präfix. So werden Verlegungen nicht fälschlich als Absage
markiert.

Ausgenommen ist ein Termin, den die Quelle nach seinem Beginn noch geführt hat
(`last_seen` nach `dtstart`, bei ganztägigen Terminen ab dem Folgetag): Er hat
stattgefunden und ist nur aus dem Zeitfenster der Quelle gefallen. SpielerPlus
behält vergangene Termine rund drei Monate, handball.net nahm die
Turnierspiele der C-Jugend vom 19.09.2026 neun Tage später aus dem
Team-Kalender. Beides wurde vorher als Absage markiert.

Taucht ein verschwundener Termin wieder in der Quelle auf, gilt wieder die
Quelle -- die Absage ist aufgehoben.

Ändern sich Zeit oder Ort eines bekannten Spiels, wird der Archiveintrag
aktualisiert. Die UID bleibt dabei stabil, damit der Apple-Kalender den Termin
verschiebt statt einen zweiten anzulegen.

## 8. Hallentabelle

Konfigurationsdatei `halls.yaml`. Schlüssel sind normalisierte Suchbegriffe
(kleingeschrieben, ohne Sonderzeichen), Werte enthalten Anzeigename, Adresse
und Koordinaten.

Bekannt:

| Suchbegriff | Anzeigename | Adresse | Koordinaten |
| --- | --- | --- | --- |
| fliethe, mtc arena wülfrath (Teilstring); Halle (nur exakt) | Sporthalle Fliethe | Fortunastraße 30, 42489 Wülfrath | 51.2759225, 7.0168646 |
| flehenberg | Sporthalle Flehenberg | Flehenberg 91, 42489 Wülfrath | 51.2810503, 7.0508109 |
| frankys gym, franky's gym | Franky's Gym | Glockenstahlstraße 1, 42855 Remscheid | 51.1910388, 7.1741024 |
| erbacher berg | Sportplatz Erbacher Berg (1. FC) | Silberberger Weg 3, Innenstadt, 42489 Wülfrath | 51.2883843, 7.0312878 |

Alle Adressen enden im ICS mit `, Deutschland`.

Unbekannte Hallen werden nicht geraten, sondern generisch bereinigt und
geloggt, damit die Tabelle nach und nach wachsen kann.

## 9. Bereinigung von handball.net-Adressen

Die Quelle liefert kaputte Strings:

```
MTC ARENA WüLFRATH\, FORTUNA STR. 30\, 42489 WüLFRATH\, 42489 WüLFRATH
BOCKMüHLE\, MERCATORSTR.\, 45143 ESSEN\, 45143 ESSEN
MATARé-GYMNASIUM\, NIEDERDONKER STR. 34\, 40667 MEERBUSCH\, 40667 MEERBUSCH
```

Probleme und Behandlung:

1. Halb-großgeschriebene Umlaute (`WüLFRATH`, `MATARé`). Das Skript muss
   sowohl diese Variante als auch korrekt kodierte Umlaute verarbeiten. Nach
   der Title-Case-Wandlung ist das Problem gelöst.
2. Doppelte PLZ und Stadt am Ende. Das letzte Komma-Segment entfernen, wenn es
   im vorletzten Segment bereits enthalten ist.
3. Alles in Title Case wandeln, Straßenabkürzungen normalisieren
   (`STR.` zu `Str.`).
4. `, Deutschland` anhängen.

Ergebnis für die Beispiele:

```
Bockmühle, Mercatorstr., 45143 Essen, Deutschland
Mataré-Gymnasium, Niederdonker Str. 34, 40667 Meerbusch, Deutschland
```

## 10. Archiv

Termine sollen dauerhaft im Kalender bleiben. Die Quellen liefern nur ein
rollierendes Fenster. Deshalb führt das Skript pro Feed eine JSON-Datei unter
`data/<feed>.json`, die bei jedem Lauf ergänzt und ins Repository
zurückcommittet wird.

Struktur je Eintrag:

```json
{
  "uid": "tbw-m1-spiel-380455",
  "source_uid": "spiel-380455@mmcc-news",
  "summary": "1. Herren Heim Lüttringhauser TV",
  "dtstart": "2026-09-19T15:50:00+02:00",
  "dtend": "2026-09-19T17:20:00+02:00",
  "all_day": false,
  "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
  "geo": [51.282, 7.0398],
  "description": "Treffpunkt: 14:35",
  "url": "https://www.handball.net/match/380455",
  "cancelled": false,
  "first_seen": "2026-09-02T09:00:00Z",
  "last_seen": "2026-09-02T09:00:00Z"
}
```

Abgesagte Einträge tragen zusätzlich `abgesagt_weil`: `quelle`, wenn die
Quelle die Absage meldet (`Retirado`), `verschwunden`, wenn sie aus der
Verschwinden-Logik stammt (Abschnitt 7). Nur eine Absage `verschwunden` darf
das Skript selbst zurücknehmen. Abgesagte Einträge ohne das Feld stammen aus
der Zeit davor. Fehlen sie in der Quelle, sind es Absagen der
Verschwinden-Logik: Stand der Termin nach seinem Beginn noch in der Quelle,
wird die Absage zurückgenommen, sonst bekommt er `verschwunden`.

Der Feed wird immer vollständig aus dem Archiv erzeugt, nicht aus der Quelle.
Die Quelle aktualisiert nur das Archiv.

UIDs werden aus einem festen Präfix und der Quell-ID gebildet und ändern sich
nie. Beispiel: `tbw-m1-spiel-380455`, `tbw-m1-training-77001458`.

## 11. Technik

- Python 3.12, Abhängigkeiten `icalendar` und `requests`
- Konfiguration in `config.yaml`, Hallen in `halls.yaml`
- SpielerPlus-URLs aus GitHub Secrets, per Umgebungsvariable ins Skript
- GitHub Actions, Cron alle 6 Stunden plus manueller Trigger
- Ausgabe nach `docs/`, Veröffentlichung über GitHub Pages
- Der Workflow committet `docs/*.ics` und `data/*.json` zurück
- Bei Fehlern einer einzelnen Quelle laufen die übrigen Feeds weiter; das
  Archiv des fehlgeschlagenen Feeds bleibt unverändert und der bestehende
  Feed wird unverändert neu geschrieben
- Zeitzone durchgehend Europe/Berlin, VTIMEZONE korrekt einbetten

## 12. Tests

Die Fixtures unter `fixtures/` stammen aus dem Ursprungsrepository (M2, M3,
MC, dazu die Spielpläne der 1. Herren und 1. Damen). Die Tests laufen deshalb
gegen `tests/config.yaml`, die Konfiguration des Ursprungs; die Beispiele in
diesem Abschnitt beziehen sich auf deren Teams. Die eigene `config.yaml`
prüft `tests/test_config.py` mit einem vollständigen Lauf gegen dieselben
Fixtures: Feeds und Kalendernamen, Treffpunkt 1:15 h vor dem Anwurf,
Spieldauer 1:30 h, Treffpunkt 5 min vor dem Training, nur das Secret
`SPIELERPLUS_M1` im Workflow.

Mindestens abzudecken:

- M3-Training ohne Ortszusatz wird Fliethe
- M3-Training mit Ortszusatz Erbacher Berg wird korrekt aufgelöst
- M2-Training erzeugt Treffpunkt-Notiz mit Beginn minus 10 Minuten
- M2-Spiel gegen Lüttringhauser TV ergibt exakt den Titel aus dem Wunschformat
- MC-Turnierspiel am 19.09. mit TB Wülfrath auf der Heimseite wird `Auswärts`
- `TB WÜLFRATH III - TB WÜLFRATH IV` erkennt den richtigen Gegner
- Nach einer Umbenennung bei handball.net erkennt der `X-WR-CALNAME` das
  eigene Team, auch wenn `config.yaml` noch den alten Namen führt
- `Retirado` erzeugt das ABGESAGT-Präfix
- Ganztagesspiel bekommt keine Treffpunkt-Notiz
- Spiel mit Ergebnis in der SUMMARY: Ergebnis wandert in die Notiz, mit
  Wertung aus Sicht des Teams (Heim und Gast, gewonnen, verloren,
  unentschieden; Turnierspiel mit Heimseite in fremder Halle)
- Verschwundenes Spiel vor dem Termin bleibt unverändert, nach dem Termin wird
  es als abgesagt markiert
- Termin, der nach seinem Beginn noch in der Quelle stand und dann
  verschwindet, bleibt unverändert; eine alte Absage dieser Art wird
  zurückgenommen, eine Absage der Quelle nie
- Adressbereinigung für alle drei Beispielstrings aus Abschnitt 9

## 13. Offene Punkte

Keine.
