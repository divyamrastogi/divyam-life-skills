---
name: whatsapp-group-allowlist
description: Add a new WhatsApp group to OpenClaw's allowlist so the agent can receive and respond to messages in it. Use when: (1) user asks to respond to messages in a WhatsApp group, (2) a group is mentioned that isn't already in the allowlist, (3) the agent is not receiving messages from a known group. Workflow: find the group ID from logs, add it to config, update memory docs.
---

# WhatsApp Group Allowlist

## When This Is Needed

When the user says "respond to messages on [Group Name]" or messages aren't reaching from a known group, the group likely isn't in the allowlist yet.

## Step 1 — Find the Group ID

WhatsApp group IDs look like `120363XXXXXXXXX@g.us` or `XXXXXXXXXXX-XXXXXXXXXX@g.us`. The config only stores these IDs, not group names — so you need to discover the ID from the logs.

### Method A: Search logs by group name

Gateway logs contain the group subject (name) alongside the group ID. Search for the group name:

```bash
grep -i "<GROUP_NAME>" ~/.openclaw/logs/gateway.log | grep "@g.us" | tail -10
```

Look for patterns like `group=120363XXXXXXXXX@g.us` or `subject: <Group Name>` near a group ID. Extract the `@g.us` ID.

### Method B: Search for rejected/blocked group messages

If the group has already tried to message but was blocked by the allowlist, it may appear in logs as rejected:

```bash
grep -i "group" ~/.openclaw/logs/gateway.log | grep -i "not allowed\|blocked\|policy\|reject" | tail -20
```

### Method C: List all group IDs seen in logs

To see every group ID that has appeared in logs (including ones not in the allowlist):

```bash
grep -oE '[0-9]+@g\.us' ~/.openclaw/logs/gateway.log | sort -u
```

Cross-reference with the current config to find which ones are missing:

```bash
python3 -c "
import json
cfg = json.load(open('$HOME/.openclaw/openclaw.json'))
groups = set(cfg.get('channels',{}).get('whatsapp',{}).get('groups',{}).keys())
print('Currently allowlisted:')
for g in sorted(groups): print(f'  {g}')
"
```

### Method D: Check crypto credentials (best for new groups that haven't messaged yet)

When a device is added to a WhatsApp group, WhatsApp immediately syncs the group's encryption keys to all linked devices — **even before any messages are sent**. This means the group ID is discoverable from the credentials folder without needing a message to arrive first.

```bash
ls ~/.openclaw/credentials/whatsapp/default/ | grep "sender-key-" | grep "@g.us" | grep -oE '[0-9]+@g\.us' | sort -u
```

Cross-reference with currently allowlisted groups to find the new one:

```bash
python3 -c "
import json, os, re, glob
cfg = json.load(open(os.path.expanduser('~/.openclaw/openclaw.json')))
known = set(cfg.get('channels',{}).get('whatsapp',{}).get('groups',{}).keys())
cred_dir = os.path.expanduser('~/.openclaw/credentials/whatsapp/default/')
found = set(re.findall(r'[0-9]+@g\.us', ' '.join(os.listdir(cred_dir))))
new = found - known
print('New groups (in creds but not allowlisted):')
for g in sorted(new): print(f'  {g}')
"
```

This is the most reliable method for newly created groups. Try this **before** Method E (open policy).

### Method E: Temporarily open group policy

If the group has never messaged before and isn't in the credentials yet, ask the user to send a message in the group, then temporarily open the policy to catch it:

```bash
# Use gateway config.patch to temporarily open
```
```json
{
  "channels": {
    "whatsapp": {
      "groupPolicy": "open"
    }
  }
}
```

Wait for the message to arrive, then search logs:
```bash
grep "@g.us" ~/.openclaw/logs/gateway.log | tail -10
```

**⚠️ Important:** Always restore the policy to `"allowlist"` immediately after finding the ID (done automatically in Step 2).

## Step 2 — Add to Config

Use `gateway config.patch` to add the group. If the policy was temporarily opened, include the restore in the same patch:

```json
{
  "channels": {
    "whatsapp": {
      "groupPolicy": "allowlist",
      "groups": {
        "<GROUP_ID>": { "requireMention": false }
      }
    }
  }
}
```

- `requireMention: false` — respond to ALL messages in the group (active participant)
- `requireMention: true` — only respond when @mentioned (passive/noisy groups)

The gateway auto-restarts on config.patch.

## Step 3 — Update Memory & User Docs

After adding a group to the config, update workspace files so future sessions know the context:

1. **MEMORY.md** — Note the group name, ID, and response behavior (e.g. "respond actively to all members").
2. **USER.md** — If specific members are authorized or the group has special rules, note it there too.

The config controls *whether* messages arrive. Memory/user docs control *how* the agent behaves in the group.

## Notes

- Never leave `groupPolicy: "open"` permanently — always restore to `"allowlist"`
- The gateway auto-restarts on config.patch; wait for reconnect before testing
- Log files may rotate daily; check `~/.openclaw/logs/` for older files if needed
- When `requireMention: false`, pair with MEMORY.md instructions about response behavior
