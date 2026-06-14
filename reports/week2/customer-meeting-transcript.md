# Customer meeting transcript (sanitized English)

Date: 13 June 2026

Speaker 1:
00:00:00
Fix the lag. Should I repeat? I think your recording started a bit later.

Speaker 2:
00:00:08
Ah, no-no, I just left it running.

Speaker 1:
00:00:11
So, is Roma going to join or not? Does anyone know?

Speaker 2:
00:00:20
First one. If anything, I think we can basically start.

Speaker 1:
00:00:28
Yeah, let's slowly get started.

Speaker 2:
00:00:33
There I sent the first five user stories — that's the main goal for MVP v1. We take candle data from historical candles, implement main metrics and patterns, load exchange data for the coins you sent, and provide a minimal UI with chart, metrics, and recognized patterns.

Speaker 1:
00:01:54
How do you plan to build the chart? Which mockup is which? Dashboard Main Screen — the third one? How is the second different from the third? Asset Detail Screen. Can you explain the second and third screens?

Speaker 3:
00:02:41
Sorry, fire alarm in my building. The second screen is the Dashboard — main screen. Above the chart there is a watchlist block with a star to choose which chart to open. Below are Active Alerts. The third screen has a Back to Dashboard button.

Speaker 4:
00:03:33
How is the second screen different from the third? On the third I see Back to Dashboard. How do you get to the third screen? Wouldn't Detected Patterns be more convenient on the second screen?

Speaker 2:
00:04:21
The first screen is the general menu. The second shows the most important information; you can open a more detailed mode with coin selection.

Speaker 1:
00:05:00
I choose a coin, see chart, candles, alerts, metrics — great. Pattern Detection is on the right. Why go to a third screen if I only see patterns again? Maybe move the pattern block from the third screen onto the second.

Speaker 2:
00:05:42
Possibly yes. We could try to fit everything.

Speaker 1:
00:06:03
The third screen seems redundant; its functionality could move to the second.

Speaker 3:
00:06:24
Then we'll put all this data on the second screen.

Speaker 1:
00:06:54
Do you have a defined list of alerts, or is this just a mockup?

Speaker 3:
00:07:04
This shows how the implementation will look.

Speaker 1:
00:07:07
By the next meeting let's define lists for alerts, metrics, and patterns. Andrey, do you have anything?

Speaker 4:
00:08:00
Add simple price-break alerts — not only complex patterns. For example, price reaching a historical maximum.

Speaker 1:
00:08:51
For MVP: web website, not a mobile app. Desktop only first.

Speaker 2:
00:09:27
The coin list you sent stays the same, right?

Speaker 1:
00:11:09
Yes, same coins. For MVP focus on the list we sent.

Speaker 2:
00:11:24
Should we implement only accurately calculable metrics first?

Speaker 1:
00:12:00
Focus on metrics that can be calculated accurately first. Prepare a pool of metrics, alerts, and patterns for the next meeting.

Speaker 2:
00:12:59
We selected the first five user stories for MVP: candle data, pattern recognition, signal display, metrics analysis, pattern visualization.

Speaker 1:
00:13:49
In US-01, fix 50+ trading pairs — use the list we sent.

Speaker 1:
00:14:34
Replace Crypto Trader — we build for analysts, not traders.

Speaker 2:
00:15:08
Yes, okay.

Speaker 4:
00:16:01
Add a simpler story — chart viewing, filters, sorting — not only complex signals.

Speaker 1:
00:17:15
About US-08 system administrator — are you adding an admin panel?

Speaker 2:
00:17:31
That's Could Have — not sure we'll reach it.

Speaker 1:
00:18:26
Replace US-11 Crypto Trader and automatic trading. We are not building a trading platform.

Speaker 2:
00:19:08
Understood.

Speaker 1:
00:19:55
For the next meeting: lists of alerts, metrics, patterns; Figma mockups; repository with MIT public setup.

Speaker 2:
00:21:42
We need MVP v0 — basic interface, start of development.

Speaker 1:
00:22:15
Let's meet on Thursday around 19:00.

Speaker 3:
00:23:37
Yes, Thursday at 19:00.

Speaker 1:
00:23:56
Team Lead, please send this recording to the chat. Bye.

Speaker 2:
00:24:10
Before we finish — do you approve the user stories, MoSCoW priorities, and initial MVP v1 scope we presented today, with the changes we discussed?

Speaker 1:
00:24:15
Yes. We discussed everything during this call and we agree. We approve the user stories, MoSCoW priorities, and initial MVP v1 scope with the changes discussed today.

Speaker 4:
00:24:18
Yes, agreed.

Speaker 2:
00:24:20
Thank you. We will update the documents accordingly.
