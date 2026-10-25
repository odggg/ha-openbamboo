# Google sign-in: enable email/password login for Bambu Open Network

Bambu Open Network signs in with your Bambu account email and a Bambu password.
If you normally use **Sign in with Google**, add this login method to your
existing Bambu account.

## 1. Check the account email

1. Open **Bambu Handy** and sign in with Google as usual.
2. Confirm that your existing printers are visible.
3. Open your profile at the bottom right (**Me**, person icon) and check the
   account details / **Account Security** for the associated email address.
4. Use that exact Bambu account email for the integration.

If Bambu asks you to link an email address, use its offered add/link-email
function and confirm the code sent to that address. An already linked,
accessible address does not need to change.

Menu labels vary by app version. If no email or linking option is shown,
resolve the account association through Bambu account management/support.
Keep your existing account and printer bindings.

## 2. Set a Bambu password

In Bambu Handy, open **Account Security → Change Password**.
Complete any requested email verification and set a Bambu account password.
This is the OAuth-account setup route documented by ha-bambulab.

If the app does not offer it, use [Bambu's password-reset page](https://bambulab.com/en/account/forgot-password):
enter the account email you checked above, request the code and set the password.
If the account is not found, recheck the email while still signed in with Google.

## 3. Test and connect

Test email/password sign-in on [Bambu's account page](https://bambulab.com/en/sign-in).

Then open **Settings → Devices & services → Bambu Open Network → Configure →
Bambu Cloud login**. Enter your account region, the checked email and the new
Bambu password, complete verification and select the existing printers.

A password change may require signing in again for an existing HA installation.
Selected printer entries are updated in place. If the printer list is empty,
compare the account and region with Bambu Handy.

## Sources

- [ha-bambulab OAuth account setup](https://docs.page/greghesp/ha-bambulab/setup#setup-using-bambu-cloud-w-oauth)
- [Bambu Handy Quick Start](https://wiki.bambulab.com/en/studio-handy/handy/bambu-handy-quick-start)
- [Bambu password reset](https://bambulab.com/en/account/forgot-password)

Checked 25 October 2026. [German guide](GOOGLE_LOGIN_DE.md) · [Installation](../README.md).
