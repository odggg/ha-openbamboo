# Bambu Open Network v0.3.0

Repository: https://github.com/odggg/ha-openbamboo

## Installation über HACS

1. ha-bambulab v2.2.26 installiert lassen.
2. Bambu Open Network in HACS öffnen.
3. Download / Erneut herunterladen > „Need a different version?“ > Release > v0.3.0.
4. Herunterladen und Home Assistant neu starten.
5. Einstellungen > Geräte & Dienste > Integration hinzufügen > Bambu Open Network.
6. Mit Bambu Cloud anmelden und Drucker auswählen.

Die Version ist ein experimentelles Prerelease. Bei älterem HACS ggf. Beta-Versionen anzeigen.
Keine Drucker löschen oder neu anlegen: Vorhandene Bambu-Lab-Einträge werden aktualisiert.

## Cloud-Kamera und Steuerung

Am Bambu-Lab-Druckergerät erscheint eine eigene Entität **Cloud camera**.
Diese für die Dashboard-Karte auswählen. Die bisherige Kamera-Entität bleibt eine lokale Kamera und kann ohne lokale Verbindung weiter „unavailable“ anzeigen.

Die neue Kamera holt eine Cloud-Sitzung und empfängt das Bild über Open Bamboos TUTK-Empfänger. Eine lokale Drucker-IP oder ein LAN-Access-Code ist dafür nicht erforderlich.

Bambu verlangt am Cloud-Kamera-Endpunkt zusätzlich Slicer-Zertifikate. Eigene zusammenpassende Dateien unter folgendem Pfad ablegen:

```text
/config/bambu_open_network/credentials/slicer_key.pem
/config/bambu_open_network/credentials/slicer_cert.pem
/config/bambu_open_network/credentials/slicer_crl.pem
```

Danach Bambu Open Network neu laden. Bei geändertem Zertifikatsordner den dort konfigurierten Pfad verwenden.
Ein Cloud-Login oder Developer Mode allein ersetzt diese Cloud-Anforderung nicht.
Zertifikate/Schlüssel sind nicht im Release enthalten.

Die Kamera liefert JPEG-Bilder/MJPEG mit bis zu vier decodierten Bildern pro Sekunde.
TUTK wird unterstützt; Agora nicht. Die erste Verbindung kann mehrere Sekunden dauern.

Pause/Fortsetzen/Stopp, Licht und weitere unterstützte Funktionen befinden sich weiterhin auf der normalen Bambu-Lab-Geräteseite.
Bei Firmware mit Signaturpflicht werden passende Slicer-Zugangsdaten und eine vom Drucker bestätigte App-Zertifizierung benötigt.

## Status und Fehler

Die Attribute der Cloud-Kamera zeigen `camera_status` und `last_error`.
`missing_signing_credentials`: Zertifikate fehlen, passen nicht oder sind nicht nutzbar.
`cloud_camera_rejected`: Cloud verweigert die TUTK-Sitzung.
`camera_timeout`: Kein verwertbarer Stream angekommen.
Die Diagnosedatei enthält weder Token noch Kamera-Sitzungsdaten oder Bilder.

Native amd64-/aarch64-Builds und Offline-Tests laufen vor Veröffentlichung.
Ein echter Home-Assistant-/Drucker-/Cloud-Kameratest ist noch erforderlich.
