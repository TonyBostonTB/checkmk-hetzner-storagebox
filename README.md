# checkmk-hetzner-storagebox

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Checkmk](https://img.shields.io/badge/Compatible%20with-Checkmk%202.4%20%7C%202.5-green)
![Release](https://img.shields.io/github/v/release/TonyBostonTB/checkmk-hetzner-storagebox)
![Status](https://img.shields.io/badge/status-beta-orange)

Checkmk 2.x MKP plugin for monitoring Hetzner Storage Boxes through the Hetzner Console API.

> **Fork notice:** this is a fork of [47k/checkmk-hetzner-storagebox](https://github.com/47k/checkmk-hetzner-storagebox).
> Everything through v0.1.3 is the original author's work; v0.2.0 fixes Checkmk 2.5
> compatibility (see [CHANGELOG](CHANGELOG.md)) and is maintained here going forward.

## Overview

The package adds a Checkmk special agent, discovery, check plugin, WATO rulesets, and metrics for Hetzner Storage Boxes. It discovers one service per Storage Box and monitors:

- API/storage box status
- Storage usage percentage and bytes
- Data and snapshot byte usage
- Snapshot count
- Subaccount count
- Optional thresholds for snapshot size, snapshot count, and subaccount count
- Optional access setting drift checks
- Optional delete protection and snapshot plan checks
- Optional snapshot and subaccount limit usage thresholds

All monitoring is performed server-side using a Checkmk Special Agent.

## API Requirements

Create a Hetzner Console API token with permission to read Storage Boxes. This plugin uses the Hetzner Console API, not the legacy Robot API and not the Cloud-only API.

Default API endpoint:

```text
https://api.hetzner.com/v1
```

Primary endpoint used by the agent:

```text
GET /storage_boxes
Authorization: Bearer <api_token>
```

Additional endpoint used by default to count subaccounts:

```text
GET /storage_boxes/{id}/subaccounts
Authorization: Bearer <api_token>
```

The agent follows `meta.pagination` / `pagination` information when the API returns paginated responses for Storage Boxes and subaccounts.

## Installation (MKP - Recommended)

Build or download the `.mkp` package, then install it as the Checkmk site user:

```bash
mkp add hetzner_storagebox-0.2.0.mkp
mkp enable hetzner_storagebox
cmk -R
```

## Manual Installation

For manual development installs, copy the `cmk_addons/plugins/hetzner_storagebox` tree into:

```text
~/local/lib/python3/cmk_addons/plugins/
```

Then reload Checkmk:

```bash
cmk -R
```

## Rule Configuration

### Special Agent Rule

Rule name: `Hetzner Storage Box`

1. Go to Setup > Agents > Other integrations > Applications.
2. Create a rule for `Hetzner Storage Box`.
3. Enter the Hetzner Console API token in the password field.
4. Keep the API URL as `https://api.hetzner.com/v1` unless you have a compatible override.
5. Set the timeout if needed.
6. Optionally restrict monitoring to selected Storage Box IDs.
7. Adjust the result cache settings if needed.
8. Run service discovery on the target Checkmk host.
9. Optionally tune `Hetzner Storage Box` service parameters.

### Result Cache

The special agent has a built-in result cache for Hetzner API responses. The cache is maintained on the agent side and reduces API load when Checkmk executes the special agent frequently. This is important because a longer service check interval does not necessarily reduce how often the Checkmk data source runs the special agent.

Result cache settings are configured in the `Hetzner Storage Box` special agent rule.

Default result cache behavior:

- Result cache is enabled by default.
- Result cache TTL is 3600 seconds (1 hour).
- Stale cache fallback on collection errors is enabled by default.
- Expired cache and lock files older than 30 days are cleaned up automatically by the special agent.

When the cache is fresh, the agent returns the cached API response and skips a new Hetzner API collection. When the cache has expired, the agent tries to refresh it from the Hetzner API.

If the Hetzner API is unavailable during refresh and stale cache fallback is enabled, the agent returns the last usable cached dataset instead of returning only the collection error. Stale data is never hidden: every Storage Box service reports the cache age and whether the returned dataset is fresh or stale.

Storage usage thresholds are still evaluated against the returned dataset, including stale cached data. For example, a stale cached dataset with usage above the CRIT threshold still produces a CRIT storage usage result.

### Check Parameters Rule

Rule name: `Hetzner Storage Box`

Default service parameter behavior:

- Storage usage WARN at 80%, CRIT at 90%.
- Snapshot size, snapshot count, and subaccount count thresholds are disabled unless configured.
- Access setting drift, delete protection, snapshot plan, and limit usage checks are ignored unless configured.
- Subaccount counts are fetched automatically from the Storage Box subaccounts API.
- Non-active statuses are WARN.
- API collection errors are UNKNOWN by default. This avoids turning API, authentication, or network reachability issues into CRIT unless you choose that policy explicitly.
- API collection error severity is configurable as UNKNOWN, WARN, or CRIT.
- Cache freshness is reported by every discovered Storage Box service. Stale cached data is never hidden, and storage usage thresholds are evaluated against whichever dataset the agent returned, fresh or cached.

The service parameter ruleset keeps these tuning options checkbox-enabled: leave an option unchecked to use the default behavior, or enable it to edit that specific threshold, expectation, or severity.

## Metrics

Each Storage Box service can emit the following perfdata when the API provides the corresponding fields:

- `used_bytes`
- `total_bytes`
- `used_percent`
- `data_bytes`
- `snapshots_bytes`
- `snapshots_count`
- `subaccounts_count`
- `snapshot_limit`
- `subaccounts_limit`
- `snapshot_limit_usage_percent`
- `subaccount_limit_usage_percent`

Byte values are rendered in human-readable binary units such as GiB and TiB in the service summary.
When thresholds for snapshot size, snapshot count, subaccount count, snapshot limit usage, or subaccount limit usage are configured, the corresponding metric includes WARN/CRIT levels.

## Example Special Agent Output

Special agent output uses one JSON payload inside a Checkmk section:

```text
<<<hetzner_storagebox:sep(0)>>>
{"cache":{"age_seconds":0,"enabled":true,"message":"fresh collection stored in result cache (age 0s, ttl 3600s)","stale":false,"status":"refresh","ttl_seconds":3600},"storage_boxes":[{"id":12345,"username":"u12345","server":"fsn1-box1","status":"active","access_settings":{"samba_enabled":true,"ssh_enabled":false,"webdav_enabled":false,"zfs_enabled":false,"reachable_externally":true},"protection":{"delete":false},"snapshot_plan":null,"storage_box_type":{"name":"BX41","size":5497558138880,"snapshot_limit":20,"automatic_snapshot_limit":10,"subaccounts_limit":100},"stats":{"size":3485338895155,"size_data":3350074496614,"size_snapshots":135264398541},"subaccounts_count":6}],"errors":[]}
```

## Example Service Output

Fresh cache:

```text
OK - Used 63.4% (3.17 TiB / 5.00 TiB), Cache age 0s (fresh, ttl 1h 0m), Status: Active, Snapshot size 126.00 GiB, Snapshot count n/a, Subaccounts 6
```

The service details view uses multiline output and includes additional informational fields when available:

```text
Used 63.4% (3.17 TiB / 5.00 TiB)
Cache age 0s (fresh, ttl 1h 0m)
Status: Active
Snapshot size 126.00 GiB
Snapshot count n/a
Subaccounts 6
Access: Samba enabled, SSH disabled, WebDAV disabled, ZFS disabled, External enabled
Delete protection: disabled
Snapshot plan: none
Snapshot limit usage: n/a
Subaccount limit usage: 6 / 100 (6.0%)
```

Stale cache:

```text
WARN - Used 63.4% (3.17 TiB / 5.00 TiB), Cache age 1h 15m (stale, ttl 1h 0m), Status: Active, Snapshot size 126.00 GiB, Snapshot count n/a, Subaccounts 6
```

Details include the cache source and refresh error:

```text
Cache age 1h 15m (stale, ttl 1h 0m)
Cache source: Stale On Error
stale result cache used after refresh failure (age 4500s, ttl 3600s)
Fresh collection error: auth_error: HTTP 401 Unauthorized while fetching https://api.hetzner.com/v1/storage_boxes
```

Stale cache with CRIT storage usage:

```text
CRIT - Used 91.0% (4.55 TiB / 5.00 TiB), Cache age 1h 15m (stale, ttl 1h 0m), Status: Active, Snapshot size 126.00 GiB, Snapshot count n/a, Subaccounts 6
```

The CRIT state comes from the storage usage threshold evaluation. The dataset is stale, but the usage thresholds are still checked against the cached values returned by the agent.

With optional thresholds or expectation checks configured, exceeded or mismatching values produce separate WARN/CRIT/UNKNOWN results so Checkmk can render native state markers:

```text
WARN - Used 63.4% (3.17 TiB / 5.00 TiB), Status: Active, Snapshot size 120.00 GiB, Snapshot count 4, Subaccounts 95, Access settings mismatch, Delete protection mismatch, Snapshot plan mismatch, Subaccount limit usage: 95 / 100 (95.0%)
```

Details:

```text
Used 63.4% (3.17 TiB / 5.00 TiB)
Status: Active
Snapshot size 120.00 GiB
Snapshot count 4
Subaccounts 95
Access: Samba enabled, SSH enabled, WebDAV disabled, ZFS disabled, External enabled
Expected SSH: disabled
Delete protection: disabled
Expected delete protection: enabled
Snapshot plan: none
Expected snapshot plan: configured
Snapshot limit usage: 4 / 20 (20.0%)
Subaccount limit usage: 95 / 100 (95.0%)
```

Discovery creates one service per returned Storage Box. It does not create a standalone API service:

```text
Hetzner Storage Box u12345
```

## Example API Test

You can test the token outside Checkmk with:

```bash
curl -sS \
  -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  -H "Accept: application/json" \
  https://api.hetzner.com/v1/storage_boxes
```

Subaccount counting can be tested for one Storage Box ID with:

```bash
curl -sS \
  -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  -H "Accept: application/json" \
  https://api.hetzner.com/v1/storage_boxes/12345/subaccounts
```

---

## Screenshot(s) ##
<img width="916" height="218" alt="1" src="https://github.com/user-attachments/assets/23df19a4-755c-4855-a2fa-f0ff277a1e02" />
<img width="1091" height="353" alt="2" src="https://github.com/user-attachments/assets/8eab6d70-24b1-4711-a16a-083dec386e8b" />
<img width="1369" height="2421" alt="3" src="https://github.com/user-attachments/assets/3903f988-fc9a-487d-bb37-2d53c6853b4b" />

---

## Error Handling

On API or network errors, the agent still emits a valid section:

```text
<<<hetzner_storagebox:sep(0)>>>
{"storage_boxes":[],"errors":[{"code":"auth_error","message":"HTTP 401 Unauthorized while fetching https://api.hetzner.com/v1/storage_boxes"}]}
```

When the API returns partial data plus errors, each returned Storage Box service includes the API error at the configured severity. When no boxes can be returned because of an API error, discovery returns no new services. Already discovered Storage Box services remain stable and report the collection problem during check execution:

```text
Hetzner Storage Box u12345
UNKNOWN - API error (auth_error): HTTP 401 Unauthorized while fetching https://api.hetzner.com/v1/storage_boxes
```

If the API collection error severity is changed to CRIT, the same already discovered Storage Box service reports:

```text
Hetzner Storage Box u12345
CRIT - API error (auth_error): HTTP 401 Unauthorized while fetching https://api.hetzner.com/v1/storage_boxes
```

## Security

- The token is stored through the Checkmk password field.
- Server-side calls pass the token as a Checkmk `Secret`, so the command line receives a password-store reference rather than the token value.
- The special agent resolves the password-store reference at runtime.
- The token is never printed in normal output or structured error messages.

## Limitations

- The plugin depends on fields returned by `GET /storage_boxes`. Missing fields are handled gracefully. Missing storage size fields make usage evaluation UNKNOWN; optional metadata fields are shown as `n/a` and do not alert.
- `subaccounts_count` is not inferred from `GET /storage_boxes` or from `subaccounts_limit`. It is counted from `GET /storage_boxes/{id}/subaccounts` when subaccount fetching is enabled and the endpoint is available.
- Snapshot limit usage is only calculated when `snapshots_count` and `storage_box_type.snapshot_limit` are available and the limit is greater than zero.
- Subaccount limit usage is only calculated when `subaccounts_count` and `storage_box_type.subaccounts_limit` are available and the limit is greater than zero.
- Size metrics are interpreted as bytes, matching the Checkmk metric names and output units.
- The plugin monitors Storage Box metadata and capacity usage only. It does not test protocol-level access such as SSH, SFTP, SMB, Borg, or WebDAV.
- Filtering is by Storage Box ID, not username.

These limitations describe the intended scope of the 0.2.0 release.

## Authors

- Manuel "Overlord" Michalski <www.47k.de> — original author (through v0.1.3)
- Tony Boston <tboston@csitlab.org> — maintainer (v0.2.0+)
