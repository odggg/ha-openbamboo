# Bambu Open Network v0.4.0

## Update / Installation

1. ha-bambulab v2.2.26 installiert lassen.
2. HACS > Bambu Open Network > Erneut herunterladen.
3. „Need a different version?“ > Release > **v0.4.0** auswählen.
4. Installieren und Home Assistant neu starten.
5. Bei neuer Einrichtung: Geräte & Dienste > Bambu Open Network hinzufügen,
   Cloud-Login wählen und Drucker auswählen.

Vorhandene Drucker nicht löschen. Bestehende Einträge und Entitäts-IDs bleiben erhalten.

## Zertifikate werden automatisch eingerichtet

Ab v0.4.0 wird derselbe native Open-Bamboo-Fork wie im verlinkten
[Orca-Plugin](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5d35283e-0378-474d-8d3a-6d8f718fddeb)
verwendet: [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking).

Die Erweiterung holt Zertifikatskette, Sperrliste und passenden Slicer-Schlüssel
von Bambus Zertifikatsdienst und speichert sie standardmäßig hier:

    /config/bambu_open_network/credentials/slicer_key.pem
    /config/bambu_open_network/credentials/slicer_cert.pem
    /config/bambu_open_network/credentials/slicer_crl.pem

**Kein manuelles Beschaffen oder Kopieren erforderlich.**
Vorhandene gültige Dateien werden weiterverwendet. Der konfigurierte Ordner
bleibt über HACS-Updates erhalten. Die Dateien erhalten Zugriffsrechte 0600.

Alle 15 Minuten wird lokal die Gültigkeit geprüft. Sieben Tage vor Ablauf
wird erneuert. Bei Fehlern werden die vorherigen Dateien wiederhergestellt.
Eine erfolgreiche Erneuerung lädt die Druckerverbindungen neu.

Der erste Abruf kann einige Sekunden dauern. In den Diagnosedaten steht
unter credential_provisioning der Zustand ready oder provision_failed.
Für den Abruf muss Bambus Zertifikatsdienst erreichbar sein.

Die tatsächlichen PEM-Dateien werden nur lokal in HA abgelegt.
Der öffentliche Quellcode/Release enthält den Bootstrap-Mechanismus des Forks,
keine fertig beschafften Slicer-PEMs. Reine LAN-Verbindungen starten keinen Abruf.

## Cloud-Kamera und Steuerung

Für die Kamera die neue Entität **Cloud camera** am Bambu-Lab-Druckergerät nutzen.
Die bisherige **Camera**-Entität ist weiterhin eine lokale Kamera.
Die Cloud-Kamera benötigt keine Drucker-IP und keinen LAN-Access-Code.

Sie liefert JPEG/MJPEG mit bis zu vier decodierten Bildern pro Sekunde.
Die erste Verbindung kann einige Sekunden dauern. Nach einem anfänglichen
Thumbnail-Timeout die Kamera erneut öffnen. TUTK wird unterstützt, Agora nicht.

Pause/Fortsetzen/Stopp, Licht und weitere unterstützte Funktionen befinden sich
auf der normalen Bambu-Lab-Geräteseite. Die automatisch beschafften Zugangsdaten
werden für signierte Befehle verwendet; der Drucker muss sie bestätigen.

## Fehlerstatus

Die Kameraattribute camera_status und last_error zeigen den Zustand.
missing_signing_credentials: Automatische Einrichtung noch nicht abgeschlossen
oder fehlgeschlagen; Integration neu laden und Internetverbindung prüfen.
cloud_camera_rejected: Cloud verweigert die TUTK-Sitzung.
camera_timeout: Kein verwertbarer Stream angekommen.

Ein echter HA-/Drucker-/Cloud-Kameratest steht noch aus; experimentelle Version.
