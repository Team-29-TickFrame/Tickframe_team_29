# Customer meeting summary — Week 2

## Date
13 June 2026

## Participants
- Customer representatives
- Team Lead (IvanGuzhov822)
- Developers (Team 29)

## Artifacts demonstrated
- [User stories](./user-stories.md) and MoSCoW priorities
- Initial proposed MVP v1 scope (first five Must Have stories)
- Figma prototype (Dashboard, Asset Detail, Pattern/Alerts screens)
- MVP v0 plan

## Discussion points
- Replace "Crypto Trader" with "market analyst" — product is for analytics, not trading
- Fix US-01: use customer coin list, not "50+ trading pairs"
- Consider merging pattern detail into the main asset screen (third screen may be redundant)
- Add simple alerts (e.g. price breaks, historical maximum)
- Desktop web only for MVP; mobile later if time allows
- Focus on accurately calculable metrics first
- US-08 (admin monitoring) — Could Have, not core MVP

## Customer feedback
- Prototype looks good; simplify navigation between screens
- Prepare defined lists of alerts, metrics, and patterns for next meeting
- Review user stories manually; do not rely blindly on AI wording

## Decisions
- MVP: desktop web application
- MVP coins: customer-provided list
- Next meeting: Thursday, 19:00
- Recording shared with instructors via Google Drive (not in public repository)

## Customer approvals
During the call the team presented user stories, MoSCoW priorities, and initial MVP v1 scope. The customers discussed all items and gave verbal approval with the changes noted above:
- **User stories:** approved with changes (personas, US-01, US-11)
- **MoSCoW priorities:** approved
- **Initial MVP v1 scope:** approved with changes (desktop web, customer coin list, accurate metrics first)
- **Prototype:** feedback received (approval not required)

## MIT-licensed public repository
Written consent was obtained via Telegram **before** repository creation. Evidence is included in the Moodle PDF submission.

## Recording and transcript
- Recording: instructors only — https://drive.google.com/drive/folders/1jT2cU4qXRnMtETrT1zOa5YaIwojFPqNk?usp=drive_link
- Transcript: [customer-meeting-transcript.md](./customer-meeting-transcript.md)
- Customer permitted private sharing with instructors. Transcript publication in repository: approved by customer.

## Action points
- Update user-stories.md (trader → analyst, US-01, US-11)
- Update Figma prototype (pattern screen merge)
- Prepare lists of alerts, metrics, patterns
- Complete MVP v0 deployment and smoke check

## Risks
- Some metrics may be less accurate if based only on candles
- Redundant third prototype screen may confuse users

## Resulting changes
- [user-stories.md](./user-stories.md)
- Figma prototype
- [mvp-v0-report.md](./mvp-v0-report.md)
