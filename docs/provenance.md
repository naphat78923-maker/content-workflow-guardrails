# Provenance

This repository is a clean extraction of deterministic controls from an AI-assisted editorial workflow, not a copied agent profile or a collection of private prompts.

The core existed before this public packaging. Its baseline regression suite was exercised before extraction. During packaging, the person-specific reply-field name was replaced by `last_response_at`, with the migrated reply test observed failing before the implementation change. A boolean-count regression was also observed failing before its fix. These changes are local to this shareable extraction; no running content assistant or private business system is modified by this repository.

Only generic program logic and synthetic fixtures are included. No customer records, private chat exports, research article captures, account cookies, API credentials, brand handoffs or internal file paths belong in this package.

Development used AI assistance. Tests show the local behaviour exercised by the suite; they do not establish autonomous-agent reliability, marketing performance or any commercial outcome.

This utility is not an official Hermes Agent integration and does not require Hermes. The MIT license applies to this repository's code; it does not grant rights to any third-party platform, brand, dataset or content a user might supply.
