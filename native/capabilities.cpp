// SPDX-License-Identifier: AGPL-3.0-or-later
// Added to the pinned Open Bamboo DSO. No changes to upstream source files.
#include "obn/abi_export.hpp"
#include "obn/agent.hpp"
#include "obn/appcert.hpp"
#include "obn/config.hpp"
#include "obn/signing.hpp"
#include "obn/mqtt_seq.hpp"
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <chrono>
#include <cstdio>
#include <string>

static bool matching_key()
{
    const auto& cfg = obn::config::current();
    const auto path = cfg.slicer_key_pem.empty()
        ? obn::config::path_in_dir("slicer_key.pem") : cfg.slicer_key_pem;
    FILE* fp = std::fopen(path.c_str(), "rb");
    if (!fp) return false;
    EVP_PKEY* key = PEM_read_PrivateKey(fp, nullptr, [](char*, int, int, void*) { return 0; }, nullptr);
    std::fclose(fp);
    const auto pem = obn::signing::slicer_cert_pem();
    BIO* bio = BIO_new_mem_buf(pem.data(), static_cast<int>(pem.size()));
    X509* cert = bio ? PEM_read_bio_X509(bio, nullptr, nullptr, nullptr) : nullptr;
    const bool ok = key && cert && X509_check_private_key(cert, key) == 1;
    X509_free(cert);
    BIO_free(bio);
    EVP_PKEY_free(key);
    return ok;
}

OBN_ABI bool obn_ha_signing_material()
{
    const bool ok = obn::signing::slicer_signing_key_present()
        && obn::signing::slicer_app_cert_usable() && matching_key();
    return ok;
}

OBN_ABI bool obn_ha_signed_ready(void* handle, const char* serial)
{
    auto* agent = obn::as_agent(handle);
    return agent && serial && obn_ha_signing_material()
        && agent->wait_for_app_cert(serial, std::chrono::milliseconds(0));
}

// Only called in the isolated --provision-credentials process. Running
// printer workers are restarted after a refresh, preserving signer isolation.
OBN_ABI bool obn_ha_fetch_credentials()
{
    std::string error;
    return obn::appcert::fetch_and_store(&error);
}

// Use exactly the counter shared with OBN's app-cert/liveview command builders.
// It is seeded once per native process and stays in Studio's 20000..29999 window.
OBN_ABI int obn_ha_next_sequence_id()
{
    return std::stoi(obn::next_mqtt_seq_id());
}
