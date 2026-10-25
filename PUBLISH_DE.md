# Bambu Open Network v0.4.1

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

## Installation und Update

1. ha-bambulab v2.2.26 installiert lassen.
2. Oben **In HACS öffnen** wählen und das Repository hinzufügen.
3. **Herunterladen** beziehungsweise **Erneut herunterladen** wählen.
   HACS wählt die aktuelle reguläre Version automatisch aus.
4. Home Assistant neu starten.
5. Bei neuer Einrichtung unter **Geräte & Dienste** die Integration
   **Bambu Open Network** hinzufügen, Cloud-Login wählen und Drucker auswählen.

Eine Beta-Auswahl ist nicht erforderlich. Bestehende Drucker nicht löschen.

**Bisher mit Google angemeldet?**
[Hier steht, wie du die Bambu-E-Mail-Adresse prüfst/hinterlegst und ein
Bambu-Passwort für den Login setzt.](docs/GOOGLE_LOGIN_DE.md)

## Druckernamen beim Import

Neue Drucker erhalten ihren in Bambu gespeicherten Namen als Eintrags- und
Gerätenamen. Ein bisheriger Seriennummern-Eintrag wird beim nächsten Import
beziehungsweise Laden der Cloud-Konfiguration berichtigt.

Eigene Namen, die du bereits in Home Assistant vergeben hast, bleiben erhalten.
Vorhandene Einträge und Entitäts-IDs werden weiterverwendet.

## Automatische Zertifikate

Im Cloud-Modus werden Zertifikatskette, Sperrliste und passender Slicer-Schlüssel
automatisch über den Open-Bamboo-Fork aus dem
[Orca-Plugin](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5d35283e-0378-474d-8d3a-6d8f718fddeb)
beschafft. Standardpfad:

    /config/bambu_open_network/credentials/slicer_key.pem
    /config/bambu_open_network/credentials/slicer_cert.pem
    /config/bambu_open_network/credentials/slicer_crl.pem

Du musst diese Dateien nicht selbst kopieren. Gültige Dateien werden
weiterverwendet. Der Ordner bleibt über HACS-Updates erhalten.
Die Gültigkeit wird alle 15 Minuten lokal geprüft; sieben Tage vor Ablauf
wird erneuert. Fehler beim Abruf stellen vorherige Dateien wieder her.
Nach erfolgreicher Erneuerung werden Druckerverbindungen neu geladen.

Der erste Abruf benötigt eine Internetverbindung und kann einige Sekunden dauern.
In den Diagnosedaten steht der Zustand unter **credential_provisioning**.

## Kamera und Steuerung

Für die Cloud-Kamera die Entität **Cloud camera** am Bambu-Lab-Drucker verwenden.
Die bisherige **Camera**-Entität ist weiterhin eine lokale Kamera.
Der Cloud-Zugriff benötigt keine Drucker-IP und keinen manuell eingegebenen
LAN-Access-Code.

Die Kamera liefert JPEG/MJPEG mit bis zu vier decodierten Bildern pro Sekunde.
Nach einem anfänglichen Thumbnail-Timeout erneut öffnen. TUTK wird unterstützt;
Agora ist nicht implementiert.

Pause, Fortsetzen, Stopp, Licht und weitere unterstützte Funktionen stehen auf
der normalen Bambu-Lab-Geräteseite. Der Drucker muss die automatisch beschaffte
App-Zertifizierung bestätigen, bevor signierte Befehle freigegeben werden.

## Fehlerstatus

Die Kameraattribute **camera_status** und **last_error** zeigen den Zustand:

- **missing_signing_credentials**: Automatische Einrichtung noch nicht fertig
  oder fehlgeschlagen; Integration neu laden und Internetverbindung prüfen.
- **cloud_camera_rejected**: Die Cloud verweigert die TUTK-Sitzung.
- **camera_timeout**: Kein verwertbarer Stream angekommen.

Der Betreiber hat den Betrieb von v0.4.0 am 25.10.2026 als funktionierend
bestätigt. Die Abdeckung weiterer Modelle und Firmware-Versionen ist begrenzt.
