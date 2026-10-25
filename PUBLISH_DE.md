# Bambu Open Network v0.5.1

## ⚠️ Voraussetzung: ha-bambulab muss installiert sein

> [!IMPORTANT]
> **Zuerst [Bambu Lab (ha-bambulab)](https://github.com/greghesp/ha-bambulab) über HACS installieren. Diese Erweiterung benötigt ha-bambulab v2.2.26.**
>
> Lass deine vorhandene Bambu-Lab-Installation und deine Drucker bestehen. Bambu Open Network ergänzt sie um die folgenden Funktionen.

[English README](README.md)

## Das bekommst du

Steuere und überwache deine Bambu-Drucker über die Bambu Cloud direkt in Home Assistant:

- **Kamera direkt bei der Steuerung:** Den ausgewählten Drucker in Bambu Control sehen, während du Achsen bewegst oder G-Code sendest. Der Cloud-Zugriff benötigt keine Drucker-IP und keinen LAN-Access-Code.
- **Maschinensteuerung:** X/Y/Z bewegen, homen, Düsen- und Betttemperatur sowie Bauteillüfter einstellen.
- **Extrudersteuerung:** An der aktiven, aufgeheizten Düse extrudieren und Filament zurückziehen.
- **Drucksteuerung:** Druck pausieren, fortsetzen oder abbrechen.
- **G-Code-Konsole:** Eigene Befehle mehrzeilig senden, mit Verlauf für die aktuelle Sitzung. Auch als Aktion für Automationen verfügbar.
- **Eine Bedienseite:** In der HA-Seitenleiste **Bambu Control** öffnen. Das Kamerabild wechselt automatisch mit der Druckerauswahl.
- **Deine Druckernamen:** Namen aus Bambu werden übernommen; eigene HA-Namen und vorhandene Entitäts-IDs bleiben erhalten.
- **Automatische Einrichtung:** Mit deinem Bambu-Konto anmelden und Drucker auswählen. Die nötigen Signatur-Zertifikate werden automatisch eingerichtet.

## Installation

**Es sind zwei Schritte nötig: erst die Dateien über HACS herunterladen, danach Bambu Open Network als Integration in Home Assistant hinzufügen.**

### 1. Das brauchst du vorher

- Home Assistant mit eingerichtetem **HACS** und einen HA-Administratorzugang.
- **[ha-bambulab v2.2.26](https://github.com/greghesp/ha-bambulab)** muss bereits über HACS heruntergeladen sein.
- Für den Cloud-Zugriff: einen eingeschalteten, mit dem Internet verbundenen Drucker, der in deinem Bambu-Konto bereits angezeigt wird, beispielsweise in Bambu Handy.

Wenn deine Drucker bereits über Bambu Lab eingerichtet sind, **lass diese Einträge bestehen**.
Du musst sie weder löschen noch neu anlegen.

### 2. Bambu Open Network in HACS herunterladen

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

1. Oben auf **In HACS öffnen** klicken. Falls gefragt, die Adresse deines Home Assistant eingeben.
2. Das Repository öffnen beziehungsweise hinzufügen und **Herunterladen** wählen.
3. Die vorgeschlagene aktuelle reguläre Version ausgewählt lassen. Eine Beta-Auswahl ist nicht nötig.
4. Warten, bis der Download abgeschlossen ist.

**Falls der Button nicht funktioniert:**

1. In Home Assistant **HACS** öffnen.
2. Oben rechts auf **⋮ → Benutzerdefinierte Repositories** gehen.
3. Als Repository **https://github.com/odggg/ha-openbamboo** eintragen.
4. Als Typ **Integration** auswählen und **Hinzufügen** drücken.
5. In HACS nach **Bambu Open Network** suchen, öffnen und **Herunterladen** wählen.

### 3. Home Assistant neu starten

**Home Assistant selbst neu starten** und warten, bis es wieder erreichbar ist.
Nur die Browserseite neu zu laden reicht nicht aus.

### 4. Jetzt die Integration hinzufügen

**Nach dem HACS-Download bist du noch nicht fertig. Dieser Schritt aktiviert die Erweiterung:**

1. In Home Assistant **Einstellungen → Geräte & Dienste** öffnen.
2. Unten rechts auf **Integration hinzufügen** klicken.
3. Nach **Bambu Open Network** suchen und den Treffer auswählen.
4. **Mit Bambu Cloud anmelden** wählen.
5. Deine **Kontoregion** auswählen und die **E-Mail-Adresse sowie das Passwort deines Bambu-Kontos** eingeben.
6. Falls abgefragt, den **Bestätigungscode** aus E-Mail/SMS oder deiner Authenticator-App eingeben.
7. Die gewünschten **Drucker auswählen**.
8. Das Feld für den **Ordner mit Slicer-Signatur-Zertifikaten** auf dem vorgeschlagenen Standardwert lassen.
9. Das Formular absenden und die Einrichtung abschließen.

**Du meldest dich bei Bambu bisher über Google an?**
Richte zuerst einen E-Mail-/Passwort-Login für dein **bestehendes Bambu-Konto** ein:
[Anleitung für Google-Login-Nutzer](docs/GOOGLE_LOGIN_DE.md).

Die ausgewählten Drucker werden übernommen beziehungsweise vorhandene Bambu-Lab-Einträge aktualisiert.
Die erste Verbindung und die automatische Einrichtung der Zertifikate können etwas dauern.

### 5. Steuerung und Kamera öffnen

1. Als HA-Administrator in der Seitenleiste **Bambu Control** öffnen.
2. Den gewünschten Drucker anhand seines Namens auswählen.
3. Auf einen verbundenen Status warten und die Bedienelemente nutzen.
4. Die **Cloud camera** des Druckers wird direkt bei den Bedienelementen angezeigt. Mit **Kamera öffnen** kannst du sie zusätzlich vergrößert aufrufen.
5. Eigene Befehle in der **G-Code-Konsole** eingeben und senden.

Für dein Dashboard die Entität **Cloud camera** des jeweiligen Druckers in einer Kamerakarte verwenden.
Die bisherige Entität **Camera** gehört zur lokalen Kamera von ha-bambulab.
Für den Cloud-Zugriff dieser Erweiterung **Cloud camera** auswählen.

[Ausführliche Anleitung zur Maschinensteuerung und G-Code-Aktion](docs/MACHINE_CONTROL_DE.md)

### Wenn du bereits eine ältere Version nutzt

In HACS **Bambu Open Network aktualisieren**, danach Home Assistant neu starten.
Eine bereits eingerichtete Integration muss nicht erneut hinzugefügt werden.
Bestehende Druckereinträge bleiben bestehen. **Bambu Control** erscheint nach dem Neustart in der Seitenleiste.

### Wenn etwas nicht auftaucht

| Problem | Das kannst du prüfen |
| --- | --- |
| Bambu Open Network fehlt bei „Integration hinzufügen“ | HACS-Download abschließen, Home Assistant vollständig neu starten und danach die Browserseite neu laden. |
| Bambu Control fehlt | Schritt 4 abschließen und mit einem HA-Administratorkonto anmelden. |
| Keine Drucker zur Auswahl | Bambu-Konto und Kontoregion prüfen. Die Drucker müssen diesem Konto bereits zugeordnet sein. |
| Kamera nicht verfügbar | **Cloud camera** auswählen. Den ersten Verbindungsaufbau abwarten und nach einem anfänglichen Vorschaubild-Timeout erneut öffnen. |
| Bisher nur Google-Login | Vorher die verlinkte Anleitung für den E-Mail-/Passwort-Login durchgehen. |

## Technische Details

Ab hier stehen Kompatibilität, Funktionsgrenzen und Hintergrund zur Implementierung.

### Kompatibilität und Installationsdateien

- Home Assistant **2025.1 oder neuer** auf **Linux amd64 oder aarch64**.
- Benötigte Basisintegration: **ha-bambulab v2.2.26**.
- Für eine manuelle Installation das gebaute Release-Paket **bambu_open_network.zip** verwenden. GitHubs automatische Quellcode-Archive enthalten die nativen Laufzeitdateien nicht.
- Es handelt sich um eine benutzerdefinierte Integration. Die Einrichtung erfolgt über HACS und **Geräte & Dienste**, nicht über den Add-on-Store.

### Automatische Zertifikate

Im Cloud-Modus werden Zertifikatskette, Sperrliste und passender Slicer-Schlüssel
automatisch über den [persano Open-Bamboo-Fork](https://github.com/persano/open-bamboo-networking)
beschafft. Dieser wird auch vom verlinkten
[Orca-Plugin](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5d35283e-0378-474d-8d3a-6d8f718fddeb)
verwendet.

Standardpfad:

    /config/bambu_open_network/credentials/slicer_key.pem
    /config/bambu_open_network/credentials/slicer_cert.pem
    /config/bambu_open_network/credentials/slicer_crl.pem

Diese Dateien müssen nicht manuell kopiert werden. Gültige Dateien werden weiterverwendet;
der Ordner bleibt über HACS-Updates erhalten. Die Gültigkeit wird alle 15 Minuten lokal
geprüft und sieben Tage vor Ablauf erneuert. Fehler beim Abruf stellen vorherige Dateien
wieder her. Nach erfolgreicher Erneuerung werden Druckerverbindungen neu geladen.

Der Abruf benötigt eine Internetverbindung. In den Diagnosedaten steht der Zustand unter
**credential_provisioning**. Reine LAN-Verbindungen lösen keinen automatischen Cloud-Abruf aus.
Tatsächliche Signatur-Schlüssel werden nicht im öffentlichen Repository oder Release mitgeliefert.
Der Fork enthält einen Hersteller-Bootstrap-Wert; Herkunft und Lizenzen stehen in [NOTICE.md](NOTICE.md).

### Kamera und Übertragung

Ab v0.5.1 zeigt Bambu Control die Kamera des ausgewählten Druckers direkt an.
Beim Druckerwechsel wird das vorherige Bild sofort entfernt. Nicht verfügbare,
unterbrochene oder veraltete Bilder werden durch eine Statusanzeige ersetzt.
Fehlgeschlagene Abrufe werden mit wachsendem Zeitabstand erneut versucht;
**Neu verbinden** startet den Abruf manuell. Ist die Seite nicht sichtbar,
wird ihr Bildabruf angehalten und bei der Rückkehr wieder aufgenommen.


Die **Cloud camera** verwendet TUTK und liefert JPEG/MJPEG mit bis zu vier decodierten
Bildern pro Sekunde. H.264 wird in Home Assistant decodiert. Audio, Agora und ein
vollständiger Slicer-Player sind nicht implementiert. Eine Kamerasitzung pro Drucker wird
von den Betrachtern geteilt und nach 60 Sekunden ohne Bildabruf beendet.

Lokale Kameras, FTP und Datei-Uploads bleiben Funktionen der Basisintegration und benötigen
deren lokale Einstellungen.

### Maschinensteuerung und G-Code

Die Befehle laufen über die vorhandene Open-Bamboo-Verbindung und deren Signierung.
Der Drucker muss den App-Zertifikatsaustausch bestätigen, bevor erforderliche signierte
Befehle freigegeben werden.

Achsbewegung, Homing und Extrusion sind während laufender und pausierter Drucke gesperrt.
Extrusion erfordert mindestens 170 °C an der aktiven Düse. Eigener G-Code während eines Drucks
muss ausdrücklich freigegeben werden. Statusprüfung, serverseitige Grenzen, verfallende
wartende manuelle Befehle und der Verzicht auf automatische Wiederholungen gelten auch
außerhalb der Oberfläche.

**Übermittelt** bestätigt die Annahme durch Open Bamboo, nicht die Ausführung jeder Zeile
durch die Firmware. Es gibt kein serielles ok-/Antwortprotokoll wie bei Pronterface.
Die Konsole ersetzt keinen gestreamten G-Code-Dateidruck.
Die HA-Aktion für Automationen heißt **bambu_open_network.send_gcode**.

[Grenzwerte, Bedienung und Automationsbeispiel](docs/MACHINE_CONTROL_DE.md)

### Konto und bestehende Drucker

Passwort und Bestätigungscode werden nur für die Anmeldung verwendet; das Kontotoken wird
in Home Assistant gespeichert. Bei abgelaufener Sitzung über die Konfiguration von
**Bambu Open Network → Mit Bambu Cloud anmelden** erneut anmelden.
Eine automatische Erneuerung des Kontotokens ist nicht implementiert.

Beim Import werden Bambu-Druckernamen übernommen. Eigene HA-Namen und vorhandene
Entitäts-IDs bleiben erhalten. Beim Deaktivieren der Erweiterung werden die ursprünglichen
MQTT-Methoden der Basisintegration wiederhergestellt.

### Diagnose

Die Kameraattribute **camera_status** und **last_error** zeigen unter anderem:

| Status | Bedeutung |
| --- | --- |
| **missing_signing_credentials** | Automatische Zertifikatseinrichtung noch nicht fertig oder fehlgeschlagen. Internetverbindung prüfen und Integration neu laden. |
| **cloud_camera_rejected** | Die Cloud verweigert die TUTK-Sitzung. |
| **camera_timeout** | Es ist kein verwertbarer Stream angekommen. |

### Entwicklung, Tests und Quellen

v0.5.0 wurde mit 101 Python-Tests, Browserprüfungen und nativen Builds für amd64/aarch64
geprüft. Die neuen Bewegungs- und Heizungsfunktionen wurden dabei nicht an einem echten
Drucker ausgelöst. Modell- und Firmware-Abdeckung bleiben begrenzt.

[Validierung](docs/VALIDATION.md) · [Architektur](docs/ARCHITECTURE.md) ·
[Quellcode und Entwicklungsanleitung](README.md#development-and-source) · [Lizenzen und Herkunft](NOTICE.md)
