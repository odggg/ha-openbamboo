# Using Google sign-in? Set a Bambu account password

Bambu Open Network's current login form accepts a **Bambu account email and password**.
It does not provide a **Sign in with Google** button. Use a password for your
Bambu account here, not your Google password.

The ha-bambulab project documents the following setup for accounts created
through Google or another OAuth provider.

## 1. Set the password in Bambu Handy

1. Open **Bambu Handy** and sign in with Google as usual.
2. Check that your existing printers are visible, so you know you are in the right account.
3. Tap the **profile/person icon** at the bottom right.
4. Open **Account Security → Change Password**.
5. Follow the verification steps offered by Bambu and set a Bambu account password.

Use the email address associated with that existing Bambu account for the
integration. If the address is unclear, check your Bambu account details before
continuing. You do not need to change your email address for this setup.

## 2. Sign in to Bambu Open Network

- **First setup:** open **Settings → Devices & services → Add integration → Bambu Open Network**.
- **Already configured:** open **Settings → Devices & services → Bambu Open Network → Configure**.

Choose **Bambu Cloud login**, select your account region and enter your Bambu
account email and the Bambu password you just set. Complete any requested
verification, then select your existing printers.

If no printers appear, check that the account and region match Bambu Handy.
Existing printer entries do not need to be deleted or rebound.

## If Change Password is not available

Menu labels and account options may differ by app version or account.
The published ha-bambulab instructions describe the route above; they do not
establish a universal email-linking or password-reset fallback for every Google account.

If your app does not offer this route or Bambu rejects it, use
[Bambu support](https://bambulab.com/en/support) to clarify the login options
for your existing account. Creating another account is not part of this setup.

## Sources and verification

- [ha-bambulab: Setup using Bambu Cloud w/ OAuth](https://docs.page/greghesp/ha-bambulab/setup#setup-using-bambu-cloud-w-oauth)
- [Current Bambu Open Network login implementation](../custom_components/bambu_open_network/cloud.py)

Documentation and integration code reviewed **26 October 2026**.
The account-password setup has not been manually tested here on a Google-linked account.

[German guide](GOOGLE_LOGIN_DE.md) · [Installation](../README.md).
