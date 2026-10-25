# Maschinensteuerung und G-Code

Ab **v0.5.0** erscheint nach dem HACS-Update und einem Neustart von Home Assistant
die Seite **Bambu Control** in der Seitenleiste. Sie steht HA-Administratoren zur Verfügung.
Keine zusätzliche Dashboard-Karte und kein YAML sind für die Oberfläche nötig.

1. **Bambu Control** öffnen und den Drucker anhand seines vorhandenen Namens auswählen.
2. Auf **Cloud · IDLE** oder **LAN · IDLE** warten. Bei fehlender Signierung oder
   veraltetem Druckerstatus bleiben die Bedienelemente gesperrt.
3. Ab **v0.5.1** erscheint die Cloud-Kamera des ausgewählten Druckers direkt bei den Bedienelementen. **Kamera öffnen** zeigt sie zusätzlich vergrößert an. Bei Problemen **Neu verbinden** wählen.
4. Schrittweite und Vorschub wählen und X/Y/Z bewegen. **Home** führt G28 für alle Achsen aus.
5. Düse, Bett und Bauteillüfter einstellen. Extrudieren/Zurückziehen betrifft die aktive
   Düse und erfordert eine gemeldete Düsentemperatur von mindestens 170 °C.
6. Eigene Befehle zeilenweise in die **G-Code-Konsole** eingeben und **G-Code senden** drücken.

Die Steuerung nutzt dieselbe vorhandene Open-Bamboo-Verbindung und Signierung wie
ha-bambulab. Cloud-Betrieb benötigt weiterhin keinen LAN Access Code.

## Grenzen der Bedienelemente

- Achsbewegung, Homing und Extrusion sind nur bei IDLE, FINISH oder FAILED möglich.
  Auch ein pausierter Druck sperrt diese Tasten.
- X/Y: maximal 100 mm pro Befehl und 6000 mm/min. Z: maximal 10 mm pro Befehl;
  die Oberfläche verwendet 600 mm/min.
- Extrusion: maximal 20 mm pro Befehl, 300 mm/min. Die aktive Düse wird verwendet;
  es erfolgt kein automatischer Werkzeugwechsel.
- Temperaturfelder: 0–300 °C für die Düse und 0–120 °C für das Bett.
  Die jeweiligen Firmware-/Modellgrenzen gelten zusätzlich.
- Der Bauteillüfter lässt sich von 0 bis 100 % setzen.
- Pause, Fortsetzen und Druckabbruch sind abhängig vom gemeldeten Druckzustand.
  Druckabbruch ist kein hardwareseitiger Not-Aus.

Vor manuellen Bewegungen den Druckraum freihalten und bei Bedarf homen.
Die Achsvorzeichen entsprechen den G-Code-Koordinaten; die sichtbare Bettbewegung
hängt vom Druckermodell ab. Die Seite erfindet keine Positionswerte.

## G-Code-Konsole

Die Konsole nimmt mehrere Zeilen bis insgesamt **16 KiB** an. Zeilenenden werden
normalisiert; eine abschließende neue Zeile wird automatisch ergänzt.

Beispiel für die Heizungssteuerung:

~~~gcode
M104 S200
M140 S60
~~~

Eigener G-Code kann Achsen und Heizungen direkt ansprechen und umgeht die Grenzen
der Achstasten. Während eines Drucks ist er standardmäßig gesperrt. Die Option
**G-Code auch während eines Drucks erlauben** hebt diese Sperre ausdrücklich auf
und wird beim Wechsel des Druckers zurückgesetzt.

**Übermittelt** bedeutet: Die native Open-Bamboo-Bibliothek hat den Befehl angenommen.
Das ist keine Bestätigung, dass die Firmware jede Zeile ausgeführt hat.
Bambu MQTT bietet hier kein serielles ok-Protokoll wie Pronterface.
M105/M114 liefern deshalb keine klassischen Terminal-Antworten in diesem Verlauf;
Temperaturen und Druckstatus werden separat aus der Druckertelemetrie angezeigt.

Es erfolgt kein automatisches Wiederholen. Bei unbekanntem Übertragungsstatus erst
am Drucker prüfen, bevor ein Befehl erneut gesendet wird. Manuelle Befehle, die vor
der Übertragung länger als zwei Sekunden in der Transportwarteschlange liegen,
verfallen. Nach einem Verbindungsabbruch werden gepufferte Befehle verworfen.
Der begrenzte Verlauf bleibt nur im aktuell geöffneten Panel; es gibt kein dauerhaftes
G-Code-Protokoll oder erneutes Senden beim Öffnen der Seite.

Die Konsole ist für direkte Befehle gedacht. Sie ersetzt keinen G-Code-Dateiupload
oder einen zeilenweise quittierten seriellen Druckjob.

## G-Code aus Automationen senden

Unter **Entwicklerwerkzeuge → Aktionen** gibt es **Bambu Open Network: Send G-code**.
Als Gerät den bestehenden Bambu-Lab-Drucker auswählen.

~~~yaml
action: bambu_open_network.send_gcode
data:
  device_id: DEINE_HOME_ASSISTANT_GERAETE_ID
  gcode: |
    M104 S200
    M140 S60
  allow_during_print: false
~~~

Die Geräte-ID lässt sich über die Geräteauswahl im Aktionseditor einsetzen.
Die Aktion benötigt Administratorrechte bei Benutzeraufrufen; HA-interne
Automationen können sie ebenfalls verwenden. Die gleichen Verbindungs-, Status-
und Drucksperren gelten auch hier. Ein erfolgreicher Aktionsaufruf bestätigt die
Annahme durch Open Bamboo, nicht die mechanische Ausführung.

## Kamera direkt beim Steuern

Die Kamera folgt automatisch der Druckerauswahl. Du brauchst keine Kamerakarte
anzulegen oder eine Kamera-URL einzutragen. Auf breiten Bildschirmen stehen
Kamera, Achsen und Temperatursteuerung nebeneinander; auf schmalen Bildschirmen
werden sie untereinander angeordnet.

Beim Wechsel wird das vorherige Druckerbild sofort entfernt. Verbindungsfehler,
fehlende Kamera-Entitäten und veraltete Bilder werden als Status angezeigt.
Der Bildabruf wird automatisch erneut versucht oder über **Neu verbinden**
manuell gestartet. Beim Verlassen/Verbergen der Seite endet ihr Bildabruf;
die vorhandene gemeinsame Cloud-Sitzung läuft nach ihrem normalen Timeout aus.
Bei der Rückkehr startet die Ansicht wieder für den ausgewählten Drucker.
