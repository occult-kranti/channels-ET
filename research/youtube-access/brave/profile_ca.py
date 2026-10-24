#!/usr/bin/env python3
"""Provision one configured public proxy CA in Brave 1.98.60 / Chromium 156's private profile.

The browser must have created its ServerCertificate database and be closed.
This deliberately does not change system trust, NSS, HOME, proxy or TLS flags.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import ssl
import subprocess

VERSION = "156.1.98.60"
FINGERPRINT = "c71b4d1e9d7775c538c688ab10cea9ce417d7312e89838f9d15ff73256cd7fc3"
TRUST_METADATA = bytes.fromhex("0a020803")
PROFILE = Path("/workspace/channels-et-brave-profile")


# Exact Chromium 156.0.8078.48 source and protobuf verified separately.
# DB schema v1; CertificateMetadata.trust.field1 / trust_type.field1 / TRUSTED=3.
# https://chromium.googlesource.com/chromium/src/+/156.0.8078.48/components/server_certificate_database/server_certificate_database.cc
# https://chromium.googlesource.com/chromium/src/+/156.0.8078.48/components/server_certificate_database/server_certificate_database.proto

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only verification")
    args = parser.parse_args()
    engine = json.loads((Path(__file__).parent / "initialize-receipt.json").read_text())["engine"]["product"]
    if engine != "Chrome/156.0.8078.48":
        raise SystemExit("Unexpected initialized Brave engine; no trust-store changes")
    version = subprocess.check_output(["/workspace/channels-et-brave-runtime/extracted/opt/brave.com/brave/brave", "--version"], text=True).strip()
    if not re.search(r"\b" + re.escape(VERSION) + r"\b", version):
        raise SystemExit("Unsupported Chromium version: inspect its official DB/protobuf schema first")
    if (PROFILE / "SingletonLock").exists() or (PROFILE / "SingletonLock").is_symlink():
        raise SystemExit("Close this private browser profile before checking or changing its trust DB")
    cert_path = Path(os.environ.get("NODE_EXTRA_CA_CERTS", ""))
    if cert_path != Path("/usr/local/share/ca-certificates/environment-proxy-ca.crt"):
        raise SystemExit("Configured CA path changed: review the new public certificate first")
    pem = cert_path.read_text()
    if pem.count("-----BEGIN CERTIFICATE-----") != 1:
        raise SystemExit("Expected exactly one configured public CA certificate")
    der = ssl.PEM_cert_to_DER_cert(pem)
    cert_hash = hashlib.sha256(der).hexdigest()
    if cert_hash != FINGERPRINT:
        raise SystemExit("Configured CA fingerprint changed: inspect it before updating this pin")
    details = subprocess.check_output(
        ["openssl", "x509", "-in", str(cert_path), "-noout", "-subject", "-issuer", "-dates", "-ext", "basicConstraints", "-checkend", "0"],
        text=True,
    )
    if "CA:TRUE" not in details:
        raise SystemExit("Configured certificate is not a CA")
    db = PROFILE / "Default/ServerCertificate"
    if not db.is_file():
        raise SystemExit("Initialize the private profile's built-in Certificate Manager first")
    c = sqlite3.connect(f"file:{db}?mode={'ro' if args.check else 'rw'}", uri=True, timeout=1)
    meta_before = c.execute("SELECT key,value FROM meta ORDER BY key").fetchall()
    if dict(meta_before).get("version") != "1" or dict(meta_before).get("last_compatible_version") != "1":
        raise SystemExit("Unexpected ServerCertificate database version")
    columns = c.execute("PRAGMA table_info(certificates)").fetchall()
    if [(r[1], r[2], r[3], r[5]) for r in columns] != [
        ("sha256hash_hex", "TEXT", 0, 1), ("der_cert", "BLOB", 1, 0), ("trust_settings", "BLOB", 1, 0)
    ]:
        raise SystemExit("Unexpected certificate database schema")
    rows = c.execute("SELECT sha256hash_hex,der_cert,trust_settings FROM certificates").fetchall()
    expected = [(cert_hash, der, TRUST_METADATA)]
    if rows and rows != expected:
        raise SystemExit("Private certificate DB contains unexpected rows; no change made")
    changed = False
    if not rows and not args.check:
        # The browser is closed; keep the original empty store privately for rollback.
        backup = db.with_name("ServerCertificate.before-configured-ca")
        if backup.exists():
            raise SystemExit("Existing private rollback copy requires review; no overwrite")
        shutil.copy2(db, backup)
        c.execute("BEGIN EXCLUSIVE")
        c.execute("INSERT INTO certificates VALUES (?,?,?)", expected[0])
        c.commit()
        changed = True
    actual = c.execute("SELECT sha256hash_hex,der_cert,trust_settings FROM certificates").fetchall()
    assert actual == expected, "Configured CA is not installed exactly as pinned"
    assert c.execute("SELECT key,value FROM meta ORDER BY key").fetchall() == meta_before
    assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    c.close()
    print(json.dumps({"status": "verified", "changed": changed, "browserVersion": version,
        "mechanism": "Brave per-profile ServerCertificate trusted CA", "profileOutsideRepository": True,
        "caSha256": cert_hash, "trustMetadataHex": TRUST_METADATA.hex(), "certificateRows": 1,
        "databaseSchemaVersion": 1, "systemTrustModified": False, "certificateDetails": details.strip()}, indent=2))


if __name__ == "__main__":
    main()
