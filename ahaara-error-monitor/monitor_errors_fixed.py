#!/usr/bin/env python3
import json
import hashlib
import datetime
from datetime import datetime, timezone
import requests
import os

def generate_error_fingerprint(error_type, context, stack_trace):
    """Generate a unique fingerprint for an error"""
    stack_excerpt = stack_trace[:100] if stack_trace else ""
    fingerprint_data = f"{error_type}::{context}::{stack_excerpt}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()

def classify_error_complexity(error_type, context, stack_trace):
    """Classify error as simple or complex"""
    # Simple errors patterns
    simple_patterns = [
        "null check", "NullPointerException", "Assertion failed", 
        "HTTP request failed", "network timeout", "invalid argument",
        "index out of bounds", "Array index", "String index",
        "missing parameter", "required field missing", "FormatException",
        "ParseException", "JSONException", "XMLException"
    ]
    
    # Check if stack trace points to Ahaara source code (not libraries)
    ahaara_patterns = ["lib/", "package:", "dart:"] if stack_trace else []
    
    # Simple if: single identifiable issue, clear RCA, existing test patterns
    if any(pattern in (error_type + " " + (context or "") + " " + (stack_trace or "")).lower() 
           for pattern in simple_patterns):
        return "simple"
    
    # Check if stack trace points to app code rather than libraries
    if any(pattern in (stack_trace or "") for pattern in ahaara_patterns):
        return "simple"
        
    return "complex"

def create_error_message(error_data):
    """Create formatted error message for WhatsApp"""
    return f"""
🐛 *New error detected* in Ahaara

*Error:* {error_data['error_type']}
*Where:* {error_data['context'] or 'Unknown context'}
*Occurrences:* {error_data['occurrences']} (first seen {error_data['first_seen']})
*Stack:* {error_data['stack_trace_lines'][:200]}...

*RCA:* {error_data['rca']}

*Options:*

*Option A — Immediate Fix*
  What: Quick patch with validation/safety check
  Effort: Small (S)
  Risk: Low
  Tradeoff: Fast solution but may not address root cause

*Option B — Root Cause Analysis*
  What: Deep investigation + proper fix
  Effort: Medium (M) 
  Risk: Low
  Tradeoff: More thorough but takes longer

*Option C — Defensive Programming*
  What: Add error boundaries + fallback behavior
  Effort: Medium (M)
  Risk: Low
  Tradeoff: App stays stable but root cause remains

Which option should I implement? (or reply with your own approach)
"""

def main():
    # Load config
    config_path = '/Users/deeksharastogi/clawd/skills/ahaara-error-monitor/config.json'
    state_path = '/Users/deeksharastogi/clawd/skills/ahaara-error-monitor/state.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found")
        return
    
    # Load state
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"lastChecked": datetime.now(timezone.utc).isoformat(), "seenErrors": {}}
    
    print("Starting error monitoring...")
    
    # Query PostHog for new app_error events
    try:
        new_errors = query_posthog(config)
        print(f"Found {len(new_errors)} new app_error events in PostHog (last 2 hours)")
        if len(new_errors) == 0:
            print("Using sample data for testing purposes")
            # Sample test data for development
            new_errors = [
            {
                'error_type': 'FlutterError',
                'error_message': 'RenderBox was not laid out: RenderFlex needs to have an exact height',
                'context': 'cooking_mode_screen',
                'stack_trace': 'package:flutter/src/widgets/framework.dart:1234:45\\nat _RenderLayout.performLayout\\nat _RenderFlex.layout\\nat RenderBox.paint\\nat RenderObject paintWithContext\\nat PaintingContext.paintChild\\nat RenderRepaintBoundary paint',
                'is_flutter_error': True,
                'occurrences': 5,
                'first_seen': '2026-04-20T08:15:00Z',
                'last_seen': '2026-04-20T08:20:00Z'
            },
            {
                'error_type': 'FormatException',
                'error_message': 'Invalid int format',
                'context': 'recipe_ingredient_parser',
                'stack_trace': 'package:flutter/src/integers/integers.dart:456:12\\nat int.parse\\nat RecipeParser.parseIngredients\\nat RecipeScreen.loadRecipe',
                'is_flutter_error': False,
                'occurrences': 2,
                'first_seen': '2026-04-20T08:10:00Z',
                'last_seen': '2026-04-20T08:18:00Z'
            }
        ]
        print(f"Using {len(new_errors)} sample errors for testing")
    
    # Process any new errors
    for error in new_errors:
        fingerprint = generate_error_fingerprint(
            error['error_type'], 
            error.get('context', ''), 
            error.get('stack_trace', '')
        )
        
        if fingerprint not in state['seenErrors']:
            # Classify error
            complexity = classify_error_complexity(
                error['error_type'], 
                error.get('context', ''), 
                error.get('stack_trace', '')
            )
            
            error_data = {
                'error_type': error['error_type'],
                'context': error.get('context', 'Unknown'),
                'occurrences': error['occurrences'],
                'first_seen': error['first_seen'],
                'last_seen': error['last_seen'],
                'stack_trace_lines': error.get('stack_trace', 'No stack trace'),
                'rca': f"Root cause analysis for {error['error_type']} in {error.get('context', 'unknown context')}"
            }
            
            print(f"New error detected: {error['error_type']} ({complexity})")
            
            if complexity == "simple":
                print("Would auto-fix this simple error")
                # Here we would implement auto-fix logic
            else:
                message = create_error_message(error_data)
                print("Would message Divyam with RCA and options")
                print(message)
                
                # Send WhatsApp message
                try:
                    message_result = message.send(
                        action="send",
                        target=config['group_chat_id'],
                        message=message.strip()
                    )
                    print(f"WhatsApp message sent: {message_result}")
                except Exception as e:
                    print(f"Failed to send WhatsApp message: {e}")
            
            # Mark as seen
            state['seenErrors'][fingerprint] = {
                "firstSeen": error['first_seen'],
                "lastSeen": error['last_seen'],
                "occurrences": error['occurrences'],
                "status": "reported",
                "fixCommit": None
            }
    
    # Update state
    state['lastChecked'] = datetime.now(timezone.utc).isoformat()
    state['lastRunStatus'] = f"{len(new_errors)} new errors found"
    state['lastRunTime'] = datetime.now(timezone.utc).isoformat()
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
    
    print(f"Monitoring complete. Last checked: {state['lastChecked']}")


def query_posthog(config):
    """Query PostHog for app_error events in the last 2 hours"""
    url = f"{config['posthog_base_url']}/api/projects/{config['posthog_project_id']}/query/"
    
    query = "SELECT properties.error_type, properties.error_message, properties.context, properties.stack_trace, properties.is_flutter_error, count() as occurrences, max(timestamp) as last_seen, min(timestamp) as first_seen FROM events WHERE event = \"app_error\" AND timestamp > now() - INTERVAL 2 HOUR GROUP BY properties.error_type, properties.error_message, properties.context, properties.stack_trace, properties.is_flutter_error ORDER BY occurrences DESC"
    
    payload = {"query": query}
    
    headers = {
        "Authorization": f"Bearer {config['posthog_personal_api_key']}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'results' in result and result['results']:
            errors = result['results']
            print(f"Found {len(errors)} error groups from PostHog")
            return errors
        else:
            print("No results returned from PostHog query")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"Error querying PostHog: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

if __name__ == "__main__":
    main()