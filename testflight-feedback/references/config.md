# TestFlight Feedback — Project Config

## Ahaara App
- **App Name**: Ahaara
- **Bundle ID**: com.divyam.ahaara
- **Repo Path**: /Users/deeksharastogi/projects/souschef
- **App Store Connect URL**: https://appstoreconnect.apple.com
- **App ID**: 6759486622
- **Feedback URL**: https://appstoreconnect.apple.com/apps/6759486622/testflight/feedback
- **TestFlight URL**: https://appstoreconnect.apple.com/apps/6759486622/testflight

## Notification
- **Target**: WhatsApp group "Ahaara Dev Bot" (120363425113122951@g.us)
- **Digest Frequency**: Every 24 hours (or on-demand)
- **Fix Notifications**: Immediate after auto-fix deployed

## Git
- **Branch**: main
- **CI Trigger**: Push to main triggers Fastlane beta → TestFlight
- **Commit Prefix**: `fix: [feedback]` for auto-fixes

## Testing
- **Command**: `flutter test`
- **Pre-push check**: Always run tests before pushing
