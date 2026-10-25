// SPDX-License-Identifier: AGPL-3.0-or-later
// Line-delimited JSON adapter around the real Open Bamboo Networking ABI.
#include "obn/bambu_networking.hpp"
#include <nlohmann/json.hpp>
#include <openssl/evp.h>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

extern "C" {
void* bambu_network_create_agent(std::string);
int bambu_network_destroy_agent(void*);
int bambu_network_set_config_dir(void*, std::string);
int bambu_network_set_cert_file(void*, std::string, std::string);
int bambu_network_set_country_code(void*, std::string);
int bambu_network_set_queue_on_main_fn(void*, BBL::QueueOnMainFn);
int bambu_network_set_on_local_connect_fn(void*, BBL::OnLocalConnectedFn);
int bambu_network_set_on_local_message_fn(void*, BBL::OnMessageFn);
int bambu_network_set_on_message_fn(void*, BBL::OnMessageFn);
int bambu_network_set_on_server_connected_fn(void*, BBL::OnServerConnectedFn);
int bambu_network_connect_printer(void*, std::string, std::string, std::string, std::string, bool);
int bambu_network_connect_server(void*);
int bambu_network_add_subscribe(void*, std::vector<std::string>);
int bambu_network_change_user(void*, std::string);
int bambu_network_send_message_to_printer(void*, std::string, std::string, int, int);
int bambu_network_send_message(void*, std::string, std::string, int, int);
void bambu_network_install_device_cert(void*, std::string, bool);
bool obn_ha_signing_material();
bool obn_ha_camera_self_test();
void obn_ha_camera_run(void*, const char*, void*, bool (*)(void*),
    void (*)(void*, const char*, const uint8_t*, size_t, int));
bool obn_ha_signed_ready(void*, const char*);
}

using json = nlohmann::json;
static std::mutex output_mutex;
static std::atomic<bool> quitting{false};
static std::atomic<bool> connected{false};
static void emit(const json& value)
{
    std::lock_guard<std::mutex> lock(output_mutex);
    std::cout << value.dump(-1, ' ', false, json::error_handler_t::replace) << '\n' << std::flush;
}
static int64_t clock_ms()
{
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
struct CameraContext {
    std::atomic<bool> requested{false};
    std::atomic<bool> working{false};
    std::atomic<int64_t> last_request{0};
    std::string serial;
};
static bool camera_running(void* value)
{
    auto* c = static_cast<CameraContext*>(value);
    return !quitting && connected && c->requested && clock_ms() - c->last_request.load() < 60000;
}
static void camera_event(void* value, const char* status, const uint8_t* data, size_t size, int codec)
{
    auto* c = static_cast<CameraContext*>(value);
    if (quitting) return;
    if (data && size) {
        std::string encoded(4 * ((size + 2) / 3), '\0');
        EVP_EncodeBlock(reinterpret_cast<unsigned char*>(encoded.data()), data, static_cast<int>(size));
        emit({{"event", "camera_frame"}, {"serial", c->serial},
              {"codec", codec == 1 ? "mjpeg" : "h264"}, {"data", encoded}});
    } else emit({{"event", "camera_state"}, {"serial", c->serial}, {"state", status}});
}
static void check(int rc)
{
    if (rc != 0) throw std::runtime_error("Open Bamboo initialization failed");
}
static bool read_line(std::string& line)
{
    line.clear();
    char c;
    while (std::cin.get(c)) {
        if (c == '\n') return true;
        if (line.size() >= 4 * 1024 * 1024) throw std::runtime_error("Oversized input");
        line.push_back(c);
    }
    if (!line.empty()) throw std::runtime_error("Truncated input");
    return false;
}

int main(int argc, char** argv)
{
    if (argc == 2 && std::string(argv[1]) == "--self-test") {
        if (!obn_ha_camera_self_test()) return 2;
        emit({{"protocol", 2}, {"obn_commit", OBN_PINNED_COMMIT}});
        return 0;
    }
    void* agent = nullptr;
    std::thread maintenance, camera;
    CameraContext camera_context;
    std::string serial;
    bool local = true;
    std::atomic<bool> signed_ready{false};
    std::atomic<bool> signature_rejected{false};
    auto cleanup = [&] {
        quitting = true;
        camera_context.requested = false;
        if (camera.joinable()) camera.join();
        if (maintenance.joinable()) maintenance.join();
        if (agent) {
            bambu_network_destroy_agent(agent);
            agent = nullptr;
        }
    };
    try {
        std::string line;
        while (read_line(line)) {
            json request = json::parse(line);
            const auto id = request.at("id");
            const std::string method = request.at("method");
            const json params = request.value("params", json::object());
            int rc = -1;
            if (method == "init" && !agent) {
                serial = params.at("serial").get<std::string>();
                if (serial.empty() || serial.find_first_not_of(
                        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos)
                    throw std::runtime_error("Invalid serial");
                camera_context.serial = serial;
                local = params.at("local").get<bool>();
                const std::string state = params.at("state_directory");
                agent = bambu_network_create_agent(state);
                if (!agent) throw std::runtime_error("Cannot create Open Bamboo agent");
                check(bambu_network_set_config_dir(agent, state));
                check(bambu_network_set_country_code(agent, params.value("country", "US")));
                const std::string ca_file = params.value("ca_file", "");
                if (!ca_file.empty()) {
                    const auto pos = ca_file.find_last_of("/\\");
                    if (pos == std::string::npos) throw std::runtime_error("Invalid CA path");
                    check(bambu_network_set_cert_file(agent,
                        ca_file.substr(0, pos), ca_file.substr(pos + 1)));
                }
                check(bambu_network_set_queue_on_main_fn(agent,
                    [](std::function<void()> fn) { fn(); }));
                auto message = [&](std::string device, std::string payload) {
                    if (!quitting && device == serial) {
                        const auto report = json::parse(payload, nullptr, false);
                        if (report.is_object()) for (const auto& item : report.items()) {
                            if (item.value().is_object()) {
                                const auto code = item.value().value("err_code", json());
                                if (code == 84033543 || code == 84033545) signature_rejected = true;
                            }
                        }
                        emit({{"event", "message"}, {"serial", device}, {"payload", payload}});
                    }
                };
                check(bambu_network_set_on_local_message_fn(agent, message));
                check(bambu_network_set_on_message_fn(agent, message));
                check(bambu_network_set_on_local_connect_fn(agent,
                    [&](int status, std::string device, std::string detail) {
                        if (quitting || !local || device != serial) return;
                        connected = status == 0 && detail.find("disconnect") == std::string::npos;
                        signed_ready = false;
                        signature_rejected = false;
                        const bool denied = detail.find("not authorised") != std::string::npos
                            || detail.find("not authorized") != std::string::npos;
                        emit({{"event", connected ? "connected" : "disconnected"},
                              {"rc", connected ? 0 : (denied ? 5 : 7)}});
                    }));
                check(bambu_network_set_on_server_connected_fn(agent,
                    [&](int result, int reason) {
                        if (quitting || local) return;
                        connected = result == 0 && reason == 0;
                        signed_ready = false;
                        signature_rejected = false;
                        if (connected && bambu_network_add_subscribe(agent, {serial}) != 0) connected = false;
                        emit({{"event", connected ? "connected" : "disconnected"},
                              {"rc", connected ? 0 : 7}});
                    }));
                const std::string username = params.value("username", "");
                const std::string password = params.value("password", "");
                if (local) {
                    rc = bambu_network_connect_printer(agent, serial, params.at("host"),
                                                       username, password, true);
                } else {
                    std::string uid = username;
                    if (uid.rfind("u_", 0) == 0) uid.erase(0, 2);
                    if (uid.empty() || password.empty())
                        throw std::runtime_error("Cloud authentication missing");
                    const json user = {{"data", {{"token", password}, {"user", {
                        {"uid", uid}, {"name", "Home Assistant"}}}}}};
                    check(bambu_network_change_user(agent, user.dump()));
                    // Subscribe in the cloud CONNACK callback before notifying Python.
                    rc = bambu_network_connect_server(agent);
                }
                if (rc == 0) {
                    maintenance = std::thread([&] {
                        while (!quitting) {
                            bool ready = false;
                            if (connected) {
                                bambu_network_install_device_cert(agent, serial, local);
                                ready = !signature_rejected && obn_ha_signed_ready(agent, serial.c_str());
                            }
                            signed_ready = ready;
                            emit({{"event", "capabilities"}, {"signed_ready", ready}});
                            for (int i = 0; i < 10 && !quitting; ++i)
                                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                        }
                    });
                }
            } else if (method == "camera_start" && agent) {
                if (local) rc = -19;
                else if (!connected) rc = -4;
                else {
                    camera_context.last_request = clock_ms();
                    camera_context.requested = true;
                    if (!camera_context.working.exchange(true)) {
                        if (camera.joinable()) camera.join();
                        camera = std::thread([&] {
                            obn_ha_camera_run(agent, serial.c_str(), &camera_context,
                                              camera_running, camera_event);
                            camera_context.working = false;
                        });
                    }
                    rc = 0;
                }
            } else if (method == "camera_stop" && agent) {
                camera_context.requested = false;
                rc = 0;
            } else if (method == "publish" && agent) {
                const std::string payload = params.at("payload");
                const int qos = params.value("qos", 0);
                const auto body = json::parse(payload);
                if (!body.is_object() || (qos != 0 && qos != 1))
                    throw std::runtime_error("Invalid publish");
                // OBN may report device_cert_installed as an internal event;
                // only this worker controls readiness, never filenames alone.
                if (!connected) rc = -4;
                else if (local)
                    rc = bambu_network_send_message_to_printer(agent, serial, payload, qos, 0);
                else
                    rc = bambu_network_send_message(agent, serial, payload, qos, 0);
            } else {
                rc = -19;
            }
            emit({{"id", id}, {"rc", rc}});
        }
        cleanup();
        return 0;
    } catch (const std::exception&) {
        // Exception text from parsers can embed access codes and tokens.
        emit({{"event", "error"}, {"rc", -19}});
        cleanup();
        return 1;
    }
}
