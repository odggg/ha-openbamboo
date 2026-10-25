// SPDX-License-Identifier: AGPL-3.0-or-later
// Cloud URL minting + the same open TUTK receiver used by OBN's BambuSource.
#include "obn/abi_export.hpp"
#include "obn/agent.hpp"
#include "camera/tutk/TutkSession.hpp"
#include <atomic>
#include <chrono>
#include <cstdint>
#include <string>
#include <thread>

extern "C" bool obn_ha_signing_material();
using CameraEvent = void (*)(void*, const char*, const uint8_t*, size_t, int);
using CameraRunning = bool (*)(void*);

static std::string parameter(const std::string& url, const std::string& key)
{
    auto pos = url.find('?');
    while (pos != std::string::npos) {
        const auto end = url.find('&', ++pos);
        const auto part = url.substr(pos, end == std::string::npos ? end : end - pos);
        if (part.rfind(key + "=", 0) == 0) {
            std::string out;
            const auto raw = part.substr(key.size() + 1);
            auto hex = [](char c) -> int {
                if (c >= '0' && c <= '9') return c - '0';
                if (c >= 'a' && c <= 'f') return c - 'a' + 10;
                if (c >= 'A' && c <= 'F') return c - 'A' + 10;
                return -1;
            };
            for (size_t i = 0; i < raw.size(); ++i) {
                if (raw[i] == '%') {
                    if (i + 2 >= raw.size()) return {};
                    const int hi = hex(raw[i + 1]), lo = hex(raw[i + 2]);
                    if (hi < 0 || lo < 0 || (hi == 0 && lo == 0)) return {};
                    out += static_cast<char>((hi << 4) | lo);
                    i += 2;
                } else out += raw[i];
            }
            return out;
        }
        pos = end;
    }
    return {};
}

OBN_ABI bool obn_ha_camera_self_test()
{
    const std::string url = "bambu:///tutk?uid=UID&authkey=A%26B&passwd=P%2B%3D&region=eu";
    return parameter(url, "uid") == "UID" && parameter(url, "authkey") == "A&B"
        && parameter(url, "passwd") == "P+=" && parameter(url, "region") == "eu"
        && parameter(url, "key").empty()
        && parameter("bambu:///tutk?passwd=%GG", "passwd").empty();
}

OBN_ABI void obn_ha_camera_run(void* handle, const char* serial, void* context,
                              CameraRunning running, CameraEvent event)
{
    try {
        auto* agent = obn::as_agent(handle);
        if (!agent || !serial || !running(context)) return;
        if (!obn_ha_signing_material()) {
            event(context, "missing_signing_credentials", nullptr, 0, 0);
            return;
        }
        event(context, "connecting", nullptr, 0, 0);
        // Force cloud TUTK; never silently fall back to a LAN address.
        const auto url = agent->remote_camera_url(std::string(serial) + "||tutk");
        if (!running(context)) return;
        if (url.rfind("bambu:///tutk?", 0) != 0) {
            event(context, "cloud_camera_rejected", nullptr, 0, 0);
            return;
        }
        obn::camera::tutk::TutkSessionParams params;
        params.uid = parameter(url, "uid");
        params.passwd = parameter(url, "passwd");
        params.authkey = parameter(url, "authkey");
        params.region = parameter(url, "region");
        params.relay_id = params.uid;
        if (params.uid.empty() || params.passwd.empty() || params.authkey.empty()) {
            event(context, "invalid_camera_session", nullptr, 0, 0);
            return;
        }
        for (char& c : params.uid) if (c >= 'a' && c <= 'z') c -= 32;
        params.relay_id = params.uid;
        std::atomic<int64_t> last_frame{0};
        auto now = [] { return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count(); };
        const auto start = now();
        obn::camera::tutk::TutkSession session;
        session.join(params, [&](const uint8_t* data, int len, int64_t, bool) {
            if (!running(context) || len <= 0 || len > 2 * 1024 * 1024) return;
            last_frame = now();
            const int codec = len >= 2 && data[0] == 0xff && data[1] == 0xd8 ? 1 : 0;
            event(context, "frame", data, static_cast<size_t>(len), codec);
        });
        while (running(context) && session.is_joined()) {
            const auto last = last_frame.load();
            if (now() - (last ? last : start) > 45000) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        session.leave();
        if (running(context)) event(context, "camera_timeout", nullptr, 0, 0);
        else event(context, "idle", nullptr, 0, 0);
    } catch (...) {
        // Native exception text/URLs can contain account and TUTK credentials.
        event(context, "camera_failed", nullptr, 0, 0);
    }
}