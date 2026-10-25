# Google-Login: Ein Bambu-Passwort für die Integration setzen

Das aktuelle Anmeldeformular von Bambu Open Network verwendet die
**E-Mail-Adresse und ein Passwort deines Bambu-Kontos**.
Einen Button **„Mit Google anmelden“** gibt es dort nicht.
Verwende hier ein Bambu-Passwort, nicht dein Google-Passwort.

Für Konten, die über Google oder einen anderen OAuth-Anbieter angelegt wurden,
beschreibt die ha-bambulab-Dokumentation den folgenden Weg.

## 1. Das Passwort in Bambu Handy setzen

1. **Bambu Handy** öffnen und wie gewohnt mit Google anmelden.
2. Prüfen, dass deine bisherigen Drucker angezeigt werden. So weißt du, dass du im richtigen Konto bist.
3. Unten rechts auf das **Profil-/Personensymbol** tippen.
4. **Kontosicherheit / Account Security → Passwort ändern / Change Password** öffnen.
5. Die von Bambu angebotenen Bestätigungsschritte durchgehen und ein Bambu-Passwort setzen.

Für die Integration brauchst du die E-Mail-Adresse, die zu diesem bestehenden
Bambu-Konto gehört. Falls sie unklar ist, prüfe zuerst deine Bambu-Kontodaten.
Du musst für diese Einrichtung keine E-Mail-Adresse ändern.

## 2. Bei Bambu Open Network anmelden

- **Neue Einrichtung:** **Einstellungen → Geräte & Dienste → Integration hinzufügen → Bambu Open Network** öffnen.
- **Bereits eingerichtet:** **Einstellungen → Geräte & Dienste → Bambu Open Network → Konfigurieren** öffnen.

**Mit Bambu Cloud anmelden** wählen. Deine Kontoregion, die E-Mail-Adresse des
Bambu-Kontos und das gerade gesetzte Bambu-Passwort eingeben.
Einen eventuell angeforderten Bestätigungscode eingeben und die bisherigen Drucker auswählen.

Falls keine Drucker auftauchen, Konto und Region mit Bambu Handy vergleichen.
Vorhandene Druckereinträge müssen nicht gelöscht oder neu gebunden werden.

## Wenn „Passwort ändern“ fehlt

Menübezeichnungen und verfügbare Kontofunktionen können je nach App-Version
oder Konto abweichen. Die veröffentlichte ha-bambulab-Anleitung beschreibt
den Weg oben. Einen allgemein gültigen Ersatzweg über E-Mail-Verknüpfung
oder „Passwort vergessen“ belegt sie für Google-Konten nicht.

Falls die App diesen Weg nicht anbietet oder Bambu ihn ablehnt, kläre die
Anmeldemöglichkeiten für dein bestehendes Konto über den
[Bambu-Support](https://bambulab.com/en/support).
Ein zweites Konto anzulegen gehört nicht zu dieser Einrichtung.

## Quellen und Prüfstand

- [ha-bambulab: Einrichtung über Bambu Cloud mit OAuth-Konto](https://docs.page/greghesp/ha-bambulab/setup#setup-using-bambu-cloud-w-oauth)
- [Aktuelle Anmeldeimplementierung von Bambu Open Network](../custom_components/bambu_open_network/cloud.py)

Dokumentation und Integrationscode geprüft am **26.10.2026**.
Das Setzen des Passworts wurde hier nicht selbst an einem Google-verknüpften Konto getestet.

[Zur Installationsanleitung](../PUBLISH_DE.md).
