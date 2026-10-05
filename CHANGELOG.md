# Changelog

## 0.2.0

- Sticky percentage rollouts and audiences: `targetingKey` and audience attributes are documented, and `UserContext` / `ContextValue` are exported for type hints.
- `env` values containing hyphens or underscores (for example `prod-portals`, `staging_v2`) were rejected before the request was made, although RocketFlag allows them in environment names. An `env` with a trailing newline, or a non-string `env` such as `True`, is now rejected.
- The cache holds at most 10,000 entries by default (`max_entries` on `Client` and `create_client`) and evicts the least recently used entry when full. Cache access is now thread-safe.

## 0.1.0

- Initial release. `create_client` / `Client.get_flag` matching the Node and Go SDKs.
- Optional in-memory TTL cache, cohort/env user context, typed errors.
