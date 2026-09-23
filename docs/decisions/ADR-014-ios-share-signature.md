# ADR-014: iOS Share envelope authenticity

- Status: Accepted
- Date: 2026-09-23
- Scope: R4 Mac-side verification and paired-device key registry

## Decision

- Use Ed25519 signatures over the existing canonical JSON envelope bytes.
- Exchange/store public keys as PEM-encoded SubjectPublicKeyInfo (`PUBLIC KEY`); the key id is `ed25519:` plus the lowercase SHA-256 digest of the DER SPKI bytes.
- Encode the detached 64-byte signature as 128 lowercase hexadecimal characters. Mac verifies through a fixed-argument, five-second-bounded local OpenSSL `pkeyutl -verify -rawin` invocation; no shell is used and private keys never enter Core.
- Store active and revoked public-key records under `Vault/system/paired-device-keys/registry.json`; R5 protects and restores both key state and event receipts.
- `mobile_capture_id` is the signed event identifier. A body-free envelope digest receipt is atomically reserved under `Vault/system/ios-share-event-receipts/` before Capture; exact retries are allowed and conflicting reuse is rejected. The existing Capture idempotency receipt prevents a deleted source from being resurrected. Envelopes older than 30 days or more than five minutes in the future are rejected before Capture.

## Consequences

- Pairing requires importing a public key from a trusted, user-confirmed pairing flow; this R4 desktop implementation does not claim an iOS Keychain/Secure Enclave app exists.
- Revocation is irreversible through this registry API. Restoring an older backup can restore the trust state represented by that backup; after disaster recovery, users must reapply any later revocations.
- The local OpenSSL executable must support Ed25519. Missing/unavailable OpenSSL fails closed.
