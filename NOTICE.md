# Third-party notices

- Open Bamboo Networking, ClusterM and contributors:
  https://github.com/ClusterM/open-bamboo-networking
  pinned commit 7822614fc7d24b4e41b2f394ae067aa88ef4b05a.
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
