# Bambu Open Network v0.2.0 veröffentlichen

Dieses ZIP enthält Quellcode. Die nativen Linux-Binaries sind noch nicht
gebaut. Es ist daher noch kein direkt installierbares HACS-Release.

## Repository und Build

1. Ein neues GitHub-Repository anlegen, z. B. ha-bambu-open-network.
2. Alle Projektdateien einschließlich .github und .gitignore übernehmen.
3. Im Projektordner die tatsächliche Repository-Adresse setzen:

```powershell
python scripts/configure_repository.py DEIN_GITHUB_NAME/ha-bambu-open-network
```

4. Dateien in das Repository pushen.
5. Unter Actions > Build HACS release > Run workflow den Build starten.

Der Workflow baut die echte Open-Bamboo-Bibliothek und den Adapter für amd64
und aarch64. Er muss vor einem Release vollständig durchlaufen. Linux-Build
und Gerätetest konnten in der Entwicklungsumgebung noch nicht ausgeführt werden.

Das Actions-Artefakt hacs-release enthält nach einem erfolgreichen Build:

- bambu_open_network.zip: Inhalt des HA-Integrationsordners.
- bambu_open_network-source.zip: zugehörige Quellen und Buildskripte.

Für einen manuellen Vorabtest das Integrations-ZIP nach
/config/custom_components/bambu_open_network/ entpacken, HA neu starten
und Bambu Open Network hinzufügen. Mit einem unbeschäftigten Drucker zuerst
Sensoren und eine harmlose Funktion wie das Kammerlicht prüfen.

## Bambu-Cloud-Anmeldung

Im Einrichtungsdialog „Mit Bambu Cloud anmelden“ auswählen:

1. Kontoregion (z. B. Europe), Bambu-E-Mail und Passwort eingeben.
2. Bei Bedarf E-Mail-/SMS-Code oder Authenticator-Code eingeben.
3. Drucker aus dem Konto auswählen und bestätigen.

Eine manuelle Eingabe des LAN-Access-Codes oder der Drucker-IP entfällt.
Ein bereits vorhandener Drucker wird aktualisiert, ohne ihn zu löschen oder
seine Entity-IDs zu ändern. Neue Drucker werden als ha-bambulab-Einträge angelegt.

Passwort und Bestätigungscode werden nicht gespeichert. Der Kontotoken
wird für Wiederverbindungen in HA gespeichert. Bei abgelaufener Sitzung unter
„Konfigurieren > Mit Bambu Cloud anmelden“ erneut anmelden.
Ein automatischer Token-Refresh wurde nicht ergänzt.

Neue reine Cloud-Einträge haben zunächst keine lokale Kamera-/FTP-Verbindung,
weil keine lokale IP eingetragen wird. Vorhandene lokale Einstellungen
bleiben beim Wechsel auf Cloud-MQTT erhalten.

Firmware mit Signaturpflicht benötigt weiterhin eigene slicer_key.pem,
slicer_cert.pem und slicer_crl.pem oder einen unterstützten Developer Mode.
Der Cloud-Login ersetzt diese Firmware-Anforderung nicht.

## HACS-Release veröffentlichen

Nach erfolgreichem Build und Gerätetest:

```powershell
git tag v0.2.0
git push origin v0.2.0
```

Der Workflow veröffentlicht ein experimentelles Prerelease mit beiden
ZIP-Dateien. Das Repository in HACS als benutzerdefinierte Integration
hinzufügen und Prereleases aktivieren. HACS nutzt bambu_open_network.zip.

Nach dem Download HA neu starten und die Integration einmal aktivieren.
Kein YAML erforderlich. Alternativ kann der Adapter die bestehenden
Druckerverbindungen unverändert als LAN-/Cloud-Konfiguration weiterverwenden.

Zum Rückbau die zusätzliche Integration zuerst deaktivieren/entfernen,
danach das HACS-Paket entfernen und HA neu starten. Die ursprünglichen
Transportmethoden werden wiederhergestellt. Bereits gespeicherte
Cloud-Kontoeinstellungen bleiben reguläre ha-bambulab-Einstellungen.
