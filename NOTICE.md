# Third-party notices

- Open Bamboo Networking, ClusterM and contributors:
  https://github.com/ClusterM/open-bamboo-networking
  using the persano fork https://github.com/persano/open-bamboo-networking
  pinned commit 85c2b52445721bccc49534e82f52650037189d4f.
  Fork changes copyright persano; AGPL-3.0-or-later.
  This is the native source revision identified by Orca Plugin Hub's
  Open Bambu Networking v0.2.41 (plugin 5d35283e-0378-474d-8d3a-6d8f718fddeb).
  The library includes the fork's vendor app bootstrap value and certificate
  fetch implementation. This is not a clean-room implementation.
  Actual provisioned PEM signing files are created only at runtime.
  scripts/patch_upstream.py disables detached fetch in printer workers;
  HA manages persistent provisioning in a separate native process.
  Its AGPL-3.0-or-later license is preserved in LICENSES/open-bamboo-networking.txt.
  The build adds native/capabilities.cpp and native/cloud_camera.cpp to its DSO,
  along with OBN's TUTK receiver sources, without editing its
  source files. Binary releases accompany exact corresponding source.

- ha-bambulab, ha-bambulab contributors:
  https://github.com/greghesp/ha-bambulab
  MIT license preserved in LICENSES/ha-bambulab.txt.
  Upstream fixtures are preserved only to review/check the private adapter
  interface. The installed original integration is not redistributed or
  modified by this component.

- Native release bundles also contain Alpine system libraries and embedded
  upstream dependencies. Build-time package provenance and license texts
  must accompany release assets; the build script records Alpine package
  metadata and includes its available license directory.

No Bambu account tokens, LAN access codes, slicer private keys or proprietary
networking plugin binaries are part of this project.

- PyAV and Pillow are provided by Home Assistant's stream/upstream camera
  dependencies; they are not bundled into this integration's native runtime.
