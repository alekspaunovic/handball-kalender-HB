# Projektregeln

## Geheime SpielerPlus-URL

Die SpielerPlus-URL der 1. Herren (M1) ist geheim. Sie steht ausschließlich
in `.env` und im GitHub Secret `SPIELERPLUS_M1`. Sie darf niemals in einer
anderen Datei auftauchen – auch nicht als Beispiel, Kommentar, Testdaten oder
in Log-Ausgaben. In Dokumentation und Code wird sie nur als Platzhalter wie
`aus GitHub Secret SPIELERPLUS_M1` referenziert.

## Herkunft

Dieses Repository ist eine Kopie von `alekspaunovic/handball-kalender`,
eingestellt auf die 1. Herren. Code, Admin-Oberfläche und Tests sind dieselben;
was dieses Repository ausmacht, steht allein in `config.yaml`. Die Tests laufen
gegen `tests/config.yaml`, die Testkonfiguration des Ursprungs, weil die
Fixtures unter `fixtures/` von dort stammen (M2, M3, MC). Änderungen am Code
möglichst im Ursprung machen und hierher übernehmen.
