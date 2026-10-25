# Mit Google registriert: E-Mail und Passwort für Bambu Open Network

Bambu Open Network meldet sich mit der E-Mail-Adresse und einem eigenen Passwort
deines Bambu-Kontos an. Wenn du bisher „Mit Google anmelden“ verwendest, richte
diesen zusätzlichen Anmeldeweg im bestehenden Bambu-Konto ein.

## 1. Das richtige Konto und die E-Mail-Adresse prüfen

1. Öffne **Bambu Handy** und melde dich wie gewohnt mit Google an.
2. Prüfe, dass deine vorhandenen Drucker in diesem Konto angezeigt werden.
3. Öffne unten rechts dein Profil (**Ich / Me**, Personensymbol) und die
   Kontodaten beziehungsweise **Kontosicherheit / Account Security**.
4. Prüfe die dort hinterlegte E-Mail-Adresse. Verwende später genau die Adresse,
   die zu diesem Bambu-Konto gehört.

Falls Bambu noch eine E-Mail-Verknüpfung verlangt, hinterlege dort über die
angebotene Funktion zum Hinzufügen/Verknüpfen deine erreichbare Adresse und
bestätige den zugesandten Code. Eine bereits hinterlegte, erreichbare Adresse
musst du dafür nicht ändern.

Die Bezeichnungen für die Kontodaten können je nach App-Version abweichen.
Falls keine E-Mail-Adresse angezeigt und keine Verknüpfung angeboten wird,
kläre die Kontozuordnung über die Bambu-Kontoverwaltung oder den Bambu-Support.
Erstelle dafür kein zweites Konto: Die Drucker sollen an deinem bisherigen
Konto gebunden bleiben.

## 2. Ein Bambu-Passwort setzen

1. Öffne **Kontosicherheit / Account Security**.
2. Wähle **Passwort ändern / Change Password**.
3. Fordere den Bestätigungscode an, wenn Bambu danach fragt.
4. Gib den Code aus der E-Mail ein und lege ein eigenes Bambu-Passwort fest.

Diesen Weg empfiehlt auch die ha-bambulab-Dokumentation für OAuth-Konten.

Falls die App das Setzen nicht anbietet, nutze
[Bambus „Passwort vergessen“-Seite](https://bambulab.com/en/account/forgot-password).
Gib die E-Mail-Adresse aus Schritt 1 ein, fordere den Code an und setze damit
ein neues Passwort. Wenn das Konto nicht gefunden wird, prüfe die Adresse
wieder im noch mit Google angemeldeten Bambu-Konto.

## 3. Den E-Mail-Login testen

Öffne [Bambus Anmeldeseite](https://bambulab.com/en/sign-in) und melde dich über
die E-Mail-Anmeldung mit deiner Bambu-Adresse und dem neu gesetzten
Bambu-Passwort an. Prüfe anschließend, dass du im richtigen Konto bist.

## 4. In Home Assistant anmelden

1. **Einstellungen → Geräte & Dienste → Bambu Open Network** öffnen.
2. Bei bestehender Einrichtung **Konfigurieren → Bambu Cloud login** wählen.
3. Deine Kontoregion, die geprüfte E-Mail-Adresse und das Bambu-Passwort eingeben.
4. Den angeforderten E-Mail-/SMS- oder 2FA-Code eingeben.
5. Deine vorhandenen Drucker auswählen und bestätigen.

Wenn das Passwort nach einer früheren HA-Einrichtung geändert wurde, kann eine
erneute Anmeldung nötig sein. Die Integration aktualisiert ausgewählte Drucker
in bestehenden Einträgen; du musst sie nicht löschen oder neu binden.

Wenn nach der Anmeldung keine Drucker auftauchen, vergleiche das verwendete
Konto und die Region mit Bambu Handy.

## Quellen

- [ha-bambulab: Einrichtung eines OAuth-Kontos](https://docs.page/greghesp/ha-bambulab/setup#setup-using-bambu-cloud-w-oauth)
- [Bambu Handy Quick Start](https://wiki.bambulab.com/en/studio-handy/handy/bambu-handy-quick-start)
- [Bambu: Passwort zurücksetzen](https://bambulab.com/en/account/forgot-password)

Geprüft am 25.10.2026. [Zur Installationsanleitung](../PUBLISH_DE.md).
